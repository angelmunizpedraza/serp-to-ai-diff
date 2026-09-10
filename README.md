# serp-to-ai-diff

**How much of Google's top-10 do AI engines actually cite? Measure it for your keywords, and find where you rank but never get cited.**

[![CI](https://github.com/angelmunizpedraza/serp-to-ai-diff/actions/workflows/ci.yml/badge.svg)](https://github.com/angelmunizpedraza/serp-to-ai-diff/actions)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Everyone in SEO is asking the same question in 2026: *if I rank in Google, will ChatGPT and Perplexity cite me?* Most answers are opinions. This tool gives you numbers for **your** keywords and **your** market.

For each keyword it fetches Google's top-10, asks Perplexity (and optionally ChatGPT with web search) the same query, collects every URL the engine cites, and compares the two lists at URL and domain level.

```
$ serp-ai-diff run --keywords keywords.txt --serp cse --ai perplexity --my-domain losangelesbulldogvet.com --md report.md

# Google vs perplexity — citation overlap study
25 keywords · avg URL overlap (Jaccard) 9 % · avg domain overlap 31 % · keywords with any shared domain 84 %

## Does ranking in Google get you cited?
| Google rank | Cited by AI |
|---:|---:|
| 1 | 64 % |
| 2 | 48 % |
| 3 | 40 % |
| …

## Domains the AI trusts that Google does not rank
| avma.org | 9 |   | petmd.com | 7 |   | reddit.com | 6 |

## Your domain: losangelesbulldogvet.com
- Ranking in Google top 10 for 11 keywords; cited by the AI for 4.
- Ranking but NOT cited (7) — your GEO backlog: "bulldog boas surgery cost los angeles"; …
```

## What you get

| Output | Question it answers |
|---|---|
| **URL / domain Jaccard per keyword** | How different is the AI's source list from Google's page one? |
| **Cited rate by Google rank (1–10)** | Is rank 1 enough? Does rank 6 ever get cited? |
| **AI-only domains** | Which sources does the engine trust that Google does not rank? (Often Reddit, Wikipedia, associations, PDFs.) |
| **Google-only domains** | Who ranks but is invisible to AI? (Usually thin commercial pages, aggregators, JS-heavy sites.) |
| **Your domain: ranking-but-not-cited** | The exact keywords where a GEO fix (structured data, llms.txt, quotable facts, sourcing) has the best odds. |
| **CSV** | One row per Google result with a `cited_by_ai` flag — pivot it however you like. |

## Install

```bash
pip install git+https://github.com/angelmunizpedraza/serp-to-ai-diff.git
```

Keys (only for what you use):

```bash
export GOOGLE_CSE_KEY=...   GOOGLE_CSE_CX=...   # Google Custom Search JSON API — 100 free queries/day
export SERPAPI_KEY=...                            # alternative: SerpAPI, closer to real SERPs
export PERPLEXITY_API_KEY=...                     # perplexity (sonar) — returns explicit citations
export OPENAI_API_KEY=...                         # chatgpt with the web_search tool (Responses API)
```

No keys? `--dry-run` produces deterministic synthetic data so you can see every output.

## Usage

```bash
# keywords.txt: one per line, # comments allowed
serp-ai-diff run --keywords keywords.txt --serp cse --ai perplexity,chatgpt \
  --my-domain example.com --md report.md --csv rows.csv --json full.json -v
```

## Method notes (read before quoting the numbers)

* **Google via Custom Search** is not identical to a live SERP (no local pack, slightly different ordering). For publishable studies use `--serp serpapi` with the right `gl`/`hl`.
* **URLs are normalised** before comparison: lower-case host, `www.` removed, tracking params (`utm_*`, `gclid`, `fbclid`, `srsltid`) and fragments dropped, trailing slash removed. Domain comparison ignores subdomains only for your own `--my-domain` check.
* **AI answers are non-deterministic.** Run 20+ keywords and, for trend claims, repeat weekly; do not draw conclusions from one query.
* **Perplexity** returns an explicit citation list. **ChatGPT** citations come from `url_citation` annotations of the web-search tool; if the model answers without searching, the list is empty and the keyword shows 0 % overlap, which is itself a finding.
* Cost: one keyword = 1 SERP call + 1 call per AI engine. 25 keywords × 2 engines ≈ cents.

## Project layout

```
serp_ai_diff/
  sources.py   # GoogleCSE, SerpApiGoogle, PerplexitySource, ChatGPTSearchSource, FakeSource
  compare.py   # normalisation, per-keyword diff, study-level aggregation
  report.py    # Markdown + CSV
  cli.py       # serp-ai-diff run
tests/         # 9 tests, no network
examples/      # sample keyword list
```

## Related tools

Part of a set of nine open-source tools I use on client work — all Python, MIT, deterministic, no API keys:

[geo-check](https://github.com/angelmunizpedraza/geo-check) · [render-gap](https://github.com/angelmunizpedraza/render-gap) · [llms-txt-generator](https://github.com/angelmunizpedraza/llms-txt-generator) · [citeable](https://github.com/angelmunizpedraza/citeable) · [ai-visibility-tracker](https://github.com/angelmunizpedraza/ai-visibility-tracker) · [linkjuice](https://github.com/angelmunizpedraza/linkjuice) · [seo-audit](https://github.com/angelmunizpedraza/seo-audit) · [ga4-report](https://github.com/angelmunizpedraza/ga4-report)

`geo-check` asks whether the AI crawlers are allowed in. `render-gap` asks whether anything was there when they arrived. `citeable` asks whether it was worth quoting.


* [ai-visibility-tracker](https://github.com/angelmunizpedraza/ai-visibility-tracker) — are you mentioned/cited by ChatGPT, Perplexity and Claude for a prompt set? Share of voice over time + AI-crawler log analysis.
* [geo-check](https://github.com/angelmunizpedraza/geo-check) — is your site technically ready for AI search?
* [seo-audit](https://github.com/angelmunizpedraza/seo-audit) — severity-ranked technical SEO issues.
* [ga4-report](https://github.com/angelmunizpedraza/ga4-report) — organic traffic report from the GA4 Data API.

## License

MIT © Ángel Muñiz Pedraza — [LinkedIn](https://www.linkedin.com/in/angel-muniz-seo)
