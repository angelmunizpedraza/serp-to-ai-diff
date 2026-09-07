from serp_ai_diff.compare import aggregate, compare_keyword, domain_of, normalize_url
from serp_ai_diff.sources import Listing, Result


def L(name, kw, urls):
    return Listing(name, kw, [Result(u, i + 1) for i, u in enumerate(urls)])


def test_normalize_url_strips_www_tracking_fragment_and_trailing_slash():
    assert normalize_url("https://www.Example.com/a/b/?utm_source=x&id=2#top") == "https://example.com/a/b?id=2"
    assert normalize_url("http://example.com/") == "http://example.com/"


def test_domain_of():
    assert domain_of("https://www.blog.example.com/x") == "blog.example.com"


def test_compare_basic_overlap_and_ranks():
    g = L("google", "k", ["https://a.com/1", "https://b.com/1", "https://c.com/1", "https://d.com/1"])
    ai = L("perplexity", "k", ["https://www.b.com/1/", "https://z.org/x", "https://c.com/other"])
    d = compare_keyword(g, ai)
    assert d.shared_urls == ["https://b.com/1"]          # exact URL match after normalization
    assert d.shared_domains == ["b.com", "c.com"]        # domain-level match
    assert d.ai_only_domains == ["z.org"] and d.google_only_domains == ["a.com", "d.com"]
    assert d.first_cited_google_rank == 2
    assert d.cited_by_rank == [False, True, True, False]
    assert d.url_jaccard == round(1 / 6, 4)
    assert d.domain_jaccard == round(2 / 5, 4)


def test_my_domain_rank_and_citation():
    g = L("google", "k", ["https://x.com/", "https://mine.com/page"])
    ai = L("perplexity", "k", ["https://docs.mine.com/faq"])
    d = compare_keyword(g, ai, my_domain="www.mine.com")
    assert d.my_domain_google_rank == 2 and d.my_domain_cited is True


def test_no_overlap_is_zero_not_error():
    d = compare_keyword(L("google", "k", ["https://a.com/"]), L("perplexity", "k", []))
    assert d.url_jaccard == 0.0 and d.first_cited_google_rank is None


def test_aggregate_rates_and_backlog():
    d1 = compare_keyword(L("google", "k1", ["https://mine.com/a", "https://b.com/"]), L("perplexity", "k1", ["https://b.com/"]), "mine.com")
    d2 = compare_keyword(L("google", "k2", ["https://c.com/", "https://mine.com/b"]), L("perplexity", "k2", ["https://mine.com/b"]), "mine.com")
    d3 = compare_keyword(L("google", "k3", ["https://c.com/"]), L("perplexity", "k3", ["https://mine.com/z"]), "mine.com")
    agg = aggregate([d1, d2, d3])
    assert agg["keywords"] == 3
    assert agg["cited_rate_by_rank"][0] == 0.0            # rank 1 never cited
    assert agg["cited_rate_by_rank"][1] == 1.0            # rank 2 cited both times it existed
    assert agg["cited_rate_by_rank"][9] is None           # no keyword had a rank 10
    assert agg["my_domain"]["ranking_but_not_cited"] == ["k1"]
    assert agg["my_domain"]["cited_but_not_ranking"] == ["k3"]
    assert ("mine.com", 1) in agg["top_ai_only_domains"]
