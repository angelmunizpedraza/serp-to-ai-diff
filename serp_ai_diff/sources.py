"""Result sources: Google SERP providers and AI answer engines.

All network access goes through plain `requests`. Keys come from the environment:

    GOOGLE_CSE_KEY + GOOGLE_CSE_CX  -> GoogleCSE       (Custom Search JSON API, 100 free queries/day)
    SERPAPI_KEY                      -> SerpApiGoogle   (paid, closer to real SERPs)
    PERPLEXITY_API_KEY               -> PerplexitySource (returns an explicit citation list)
    OPENAI_API_KEY                   -> ChatGPTSearchSource (Responses API with web_search tool)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Protocol

import requests


class SourceError(RuntimeError):
    pass


@dataclass
class Result:
    """A ranked URL. `rank` is 1-based; AI citations keep the order the engine returned."""

    url: str
    rank: int
    title: str = ""


@dataclass
class Listing:
    source: str
    keyword: str
    results: List[Result] = field(default_factory=list)
    answer_text: str = ""  # AI engines only


class Source(Protocol):
    name: str

    def fetch(self, keyword: str) -> Listing: ...


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise SourceError(f"Missing {name} in environment")
    return v


def _get(url: str, params: dict, headers: dict | None = None, timeout: int = 30) -> dict:
    r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
    if r.status_code >= 400:
        raise SourceError(f"{url} -> HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def _post(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if r.status_code >= 400:
        raise SourceError(f"{url} -> HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


class GoogleCSE:
    name = "google"

    def __init__(self, gl: str = "es", hl: str = "es", num: int = 10):
        self.gl, self.hl, self.num = gl, hl, min(num, 10)

    def fetch(self, keyword: str) -> Listing:
        data = _get(
            "https://www.googleapis.com/customsearch/v1",
            {"key": _env("GOOGLE_CSE_KEY"), "cx": _env("GOOGLE_CSE_CX"), "q": keyword, "num": self.num, "gl": self.gl, "hl": self.hl},
        )
        items = data.get("items") or []
        return Listing(self.name, keyword, [Result(i["link"], n + 1, i.get("title", "")) for n, i in enumerate(items)])


class SerpApiGoogle:
    name = "google"

    def __init__(self, gl: str = "es", hl: str = "es", num: int = 10):
        self.gl, self.hl, self.num = gl, hl, num

    def fetch(self, keyword: str) -> Listing:
        data = _get(
            "https://serpapi.com/search.json",
            {"engine": "google", "q": keyword, "gl": self.gl, "hl": self.hl, "num": self.num, "api_key": _env("SERPAPI_KEY")},
        )
        org = data.get("organic_results") or []
        return Listing(self.name, keyword, [Result(o["link"], o.get("position", n + 1), o.get("title", "")) for n, o in enumerate(org)])


class PerplexitySource:
    name = "perplexity"

    def __init__(self, model: str = "sonar"):
        self.model = model

    def fetch(self, keyword: str) -> Listing:
        data = _post(
            "https://api.perplexity.ai/chat/completions",
            {"Authorization": f"Bearer {_env('PERPLEXITY_API_KEY')}"},
            {"model": self.model, "messages": [{"role": "user", "content": keyword}]},
        )
        text = data["choices"][0]["message"]["content"]
        cites = list(data.get("citations") or [])
        return Listing(self.name, keyword, [Result(u, n + 1) for n, u in enumerate(cites)], text)


class ChatGPTSearchSource:
    """ChatGPT with the web_search tool (Responses API). Citations come as url_citation annotations."""

    name = "chatgpt"

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    def fetch(self, keyword: str) -> Listing:
        data = _post(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {_env('OPENAI_API_KEY')}"},
            {"model": self.model, "tools": [{"type": "web_search_preview"}], "input": keyword},
        )
        urls: List[str] = []
        text = ""
        for item in data.get("output", []):
            for c in item.get("content", []) or []:
                text += c.get("text", "")
                for a in c.get("annotations", []) or []:
                    u = a.get("url")
                    if u and u not in urls:
                        urls.append(u)
        return Listing(self.name, keyword, [Result(u, n + 1) for n, u in enumerate(urls)], text)


class FakeSource:
    """Canned listings for tests and --dry-run."""

    def __init__(self, name: str, table: Dict[str, List[str]]):
        self.name = name
        self._table = table

    def fetch(self, keyword: str) -> Listing:
        urls = self._table.get(keyword, [])
        return Listing(self.name, keyword, [Result(u, n + 1) for n, u in enumerate(urls)])


def build_serp(provider: str) -> Source:
    if provider == "cse":
        return GoogleCSE()
    if provider == "serpapi":
        return SerpApiGoogle()
    raise SourceError("SERP provider must be 'cse' or 'serpapi'")


def build_ai(names: List[str]) -> List[Source]:
    reg = {"perplexity": PerplexitySource, "chatgpt": ChatGPTSearchSource}
    out: List[Source] = []
    for n in names:
        n = n.strip().lower()
        if n not in reg:
            raise SourceError(f"Unknown AI engine '{n}'. Known: {', '.join(reg)}")
        out.append(reg[n]())
    return out
