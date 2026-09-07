"""Overlap metrics between a Google SERP and an AI engine's citations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .sources import Listing

TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "ref", "srsltid"}


def normalize_url(url: str) -> str:
    """Lower-case host, drop www., fragments, tracking params and trailing slash."""
    p = urlparse(url.strip())
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING]
    path = re.sub(r"/+$", "", p.path) or "/"
    return urlunparse((p.scheme.lower() or "https", host, path, "", urlencode(q), ""))


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


@dataclass
class KeywordDiff:
    keyword: str
    ai_engine: str
    google_urls: List[str]
    ai_urls: List[str]
    shared_urls: List[str]
    shared_domains: List[str]
    google_only_domains: List[str]
    ai_only_domains: List[str]
    url_jaccard: float
    domain_jaccard: float
    # position of the first Google result that the AI also cites (1-based) or None
    first_cited_google_rank: Optional[int]
    # for each Google rank 1..10: was it cited? (index 0 == rank 1)
    cited_by_rank: List[bool] = field(default_factory=list)
    my_domain_google_rank: Optional[int] = None
    my_domain_cited: Optional[bool] = None


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    return round(len(sa & sb) / len(sa | sb), 4) if (sa | sb) else 0.0


def compare_keyword(google: Listing, ai: Listing, my_domain: Optional[str] = None) -> KeywordDiff:
    g_urls = [normalize_url(r.url) for r in sorted(google.results, key=lambda r: r.rank)]
    a_urls = [normalize_url(r.url) for r in sorted(ai.results, key=lambda r: r.rank)]
    g_dom = [domain_of(u) for u in g_urls]
    a_dom = [domain_of(u) for u in a_urls]
    a_set, a_dom_set = set(a_urls), set(a_dom)

    shared_urls = [u for u in g_urls if u in a_set]
    shared_domains = sorted(set(g_dom) & a_dom_set)
    cited_by_rank = [d in a_dom_set for d in g_dom]
    first = next((i + 1 for i, hit in enumerate(cited_by_rank) if hit), None)

    my_rank = my_cited = None
    if my_domain:
        md = my_domain.lower().removeprefix("www.")
        my_rank = next((i + 1 for i, d in enumerate(g_dom) if d == md or d.endswith("." + md)), None)
        my_cited = any(d == md or d.endswith("." + md) for d in a_dom)

    return KeywordDiff(
        keyword=google.keyword,
        ai_engine=ai.source,
        google_urls=g_urls,
        ai_urls=a_urls,
        shared_urls=shared_urls,
        shared_domains=shared_domains,
        google_only_domains=sorted(set(g_dom) - a_dom_set),
        ai_only_domains=sorted(a_dom_set - set(g_dom)),
        url_jaccard=_jaccard(g_urls, a_urls),
        domain_jaccard=_jaccard(g_dom, a_dom),
        first_cited_google_rank=first,
        cited_by_rank=cited_by_rank,
        my_domain_google_rank=my_rank,
        my_domain_cited=my_cited,
    )


def aggregate(diffs: List[KeywordDiff]) -> Dict:
    """Study-level numbers across all keywords for one AI engine."""
    if not diffs:
        return {}
    n = len(diffs)
    rank_hits = [0] * 10
    rank_seen = [0] * 10
    ai_only: Dict[str, int] = {}
    g_only: Dict[str, int] = {}
    for d in diffs:
        for i, hit in enumerate(d.cited_by_rank[:10]):
            rank_seen[i] += 1
            rank_hits[i] += int(hit)
        for dom in d.ai_only_domains:
            ai_only[dom] = ai_only.get(dom, 0) + 1
        for dom in d.google_only_domains:
            g_only[dom] = g_only.get(dom, 0) + 1
    mine = [d for d in diffs if d.my_domain_google_rank is not None]
    return {
        "keywords": n,
        "ai_engine": diffs[0].ai_engine,
        "avg_url_jaccard": round(sum(d.url_jaccard for d in diffs) / n, 4),
        "avg_domain_jaccard": round(sum(d.domain_jaccard for d in diffs) / n, 4),
        "pct_keywords_with_any_overlap": round(sum(1 for d in diffs if d.shared_domains) / n, 4),
        # P(cited | Google rank k)
        "cited_rate_by_rank": [round(h / s, 4) if s else None for h, s in zip(rank_hits, rank_seen)],
        "top_ai_only_domains": sorted(ai_only.items(), key=lambda x: -x[1])[:15],
        "top_google_only_domains": sorted(g_only.items(), key=lambda x: -x[1])[:15],
        "my_domain": {
            "keywords_ranking_top10": len(mine),
            "keywords_cited": sum(1 for d in diffs if d.my_domain_cited),
            "ranking_but_not_cited": [d.keyword for d in mine if not d.my_domain_cited],
            "cited_but_not_ranking": [d.keyword for d in diffs if d.my_domain_cited and d.my_domain_google_rank is None],
        },
    }
