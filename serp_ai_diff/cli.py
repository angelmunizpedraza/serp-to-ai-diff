"""serp-ai-diff CLI.

    serp-ai-diff run --keywords keywords.txt --serp cse --ai perplexity [--my-domain example.com] [--md report.md] [--csv out.csv] [--json out.json]
    serp-ai-diff run --keywords keywords.txt --dry-run     # no API keys, synthetic data
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import List

from . import __version__
from .compare import aggregate, compare_keyword
from .report import csv_text, markdown
from .sources import FakeSource, SourceError, build_ai, build_serp


def read_keywords(path: str) -> List[str]:
    lines = [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines()]
    kws = [l for l in lines if l and not l.startswith("#")]
    if not kws:
        raise ValueError("keywords file is empty")
    return kws


def _demo_sources(keywords: List[str], ai_names: List[str], my_domain: str | None):
    pool = ["example.com", "wikipedia.org", "healthline.com", "nytimes.com", "reddit.com", "forbes.com", "avma.org", "petmd.com", "yelp.com", "quora.com", "medium.com", "bbc.com"]
    if my_domain:
        pool.insert(0, my_domain)

    def pick(seed: str, k: int) -> List[str]:
        h = int(hashlib.sha1(seed.encode()).hexdigest(), 16)
        doms = sorted(pool, key=lambda d: int(hashlib.sha1((seed + d).encode()).hexdigest(), 16))[:k]
        return [f"https://www.{d}/{seed.split('|')[0][:12].replace(' ', '-')}/p{(h >> i) % 7}" for i, d in enumerate(doms)]

    google = FakeSource("google", {k: pick("g|" + k, 10) for k in keywords})
    ais = [FakeSource(n, {k: pick(f"{n}|{k}", 6) for k in keywords}) for n in ai_names]
    return google, ais


def _cmd_run(a: argparse.Namespace) -> int:
    keywords = read_keywords(a.keywords)
    ai_names = [x.strip().lower() for x in a.ai.split(",")]
    if a.dry_run:
        google, ais = _demo_sources(keywords, ai_names, a.my_domain)
    else:
        google, ais = build_serp(a.serp), build_ai(ai_names)

    out_md: List[str] = []
    out_json = {}
    out_csv: List[str] = []
    for ai in ais:
        diffs = []
        for kw in keywords:
            try:
                g = google.fetch(kw)
                r = ai.fetch(kw)
            except SourceError as e:
                print(f"[warn] {kw!r} via {ai.name}: {e}", file=sys.stderr)
                continue
            diffs.append(compare_keyword(g, r, a.my_domain))
            if a.verbose:
                d = diffs[-1]
                print(f"[{ai.name}] {kw[:50]!r}: url J={d.url_jaccard:.2f} dom J={d.domain_jaccard:.2f} first cited rank={d.first_cited_google_rank}")
        if not diffs:
            continue
        agg = aggregate(diffs)
        out_md.append(markdown(agg, diffs, a.my_domain))
        out_json[ai.name] = {"aggregate": agg, "keywords": [d.__dict__ for d in diffs]}
        out_csv.append(csv_text(diffs))

    if not out_md:
        print("error: no results", file=sys.stderr)
        return 1
    md = "\n\n---\n\n".join(out_md)
    if a.md:
        Path(a.md).write_text(md, encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(out_json, indent=2, default=str), encoding="utf-8")
    if a.csv:
        Path(a.csv).write_text("".join(out_csv), encoding="utf-8")
    if not (a.md or a.json or a.csv):
        print(md)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="serp-ai-diff", description="Measure overlap between Google's top-10 and the sources AI engines cite.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--keywords", required=True, help="Text file, one keyword per line (# comments allowed)")
    r.add_argument("--serp", default="cse", choices=["cse", "serpapi"])
    r.add_argument("--ai", default="perplexity", help="Comma list: perplexity,chatgpt")
    r.add_argument("--my-domain")
    r.add_argument("--md")
    r.add_argument("--csv")
    r.add_argument("--json")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("-v", "--verbose", action="store_true")
    r.set_defaults(func=_cmd_run)
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SourceError, FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
