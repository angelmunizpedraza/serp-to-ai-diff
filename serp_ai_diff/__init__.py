"""serp-to-ai-diff — how much do Google's top results overlap with the sources AI engines cite?

For each keyword: fetch Google's top-10 (Custom Search JSON API or SerpAPI),
ask Perplexity (and optionally ChatGPT with web search) the same query, collect
the URLs they cite, and measure overlap at URL and domain level. The output tells
you which of your rankings are "AI-safe", which domains AI engines trust that
Google does not, and where you rank but are never cited.
"""

__version__ = "0.1.0"

from .compare import compare_keyword, domain_of, normalize_url  # noqa: F401
