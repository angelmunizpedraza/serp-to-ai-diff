import json

from serp_ai_diff import cli


def test_dry_run_end_to_end(tmp_path):
    kws = tmp_path / "k.txt"
    kws.write_text("# demo\nbest vet los angeles\nbulldog boas surgery\n\ncheap vet santa monica\n")
    md, js, csvf = tmp_path / "r.md", tmp_path / "r.json", tmp_path / "r.csv"
    code = cli.main(["run", "--keywords", str(kws), "--ai", "perplexity,chatgpt", "--dry-run", "--my-domain", "example.com",
                     "--md", str(md), "--json", str(js), "--csv", str(csvf)])
    assert code == 0
    text = md.read_text()
    assert "# Google vs perplexity" in text and "# Google vs chatgpt" in text
    assert "Your domain: example.com" in text
    data = json.loads(js.read_text())
    assert set(data) == {"perplexity", "chatgpt"} and data["perplexity"]["aggregate"]["keywords"] == 3
    assert csvf.read_text().startswith("keyword,ai_engine,google_rank,url,domain,cited_by_ai")


def test_empty_keywords_file_errors(tmp_path, capsys):
    kws = tmp_path / "k.txt"
    kws.write_text("# only comments\n")
    assert cli.main(["run", "--keywords", str(kws), "--dry-run"]) == 2
    assert "empty" in capsys.readouterr().err


def test_unknown_ai_engine(tmp_path, capsys):
    kws = tmp_path / "k.txt"
    kws.write_text("x\n")
    assert cli.main(["run", "--keywords", str(kws), "--ai", "bing"]) == 2
    assert "Unknown AI engine" in capsys.readouterr().err
