"""kkai export --osf: anonymised coder ids, zipped images, documentation files."""

import zipfile

from kkai.cli import main
from kkai.export import anonymise_text


def test_anonymise_whole_tokens_only():
    aliases = {"PB": "A", "DK": "X1"}
    text, n = anonymise_text("coder PB,DK;xPB PBx a7DK2 [DK]", aliases)
    assert text == "coder A,X1;xPB PBx a7DK2 [X1]" and n == 3


def test_export_osf_dry_run(cfg, monkeypatch, tmp_path):
    monkeypatch.chdir(cfg.root)
    d = ["--dry-run"]
    for s in (["plan", "--stage", "main"], ["generate", "--stage", "main"], ["prepare", "--stage", "main"]):
        assert main(s + d) == 0, s
    human = cfg.data_dir / "human"
    human.mkdir(parents=True, exist_ok=True)
    (human / "human_codes.csv").write_text("image_id,coder_id,source_file\nabc,PB,sheet_PB.xlsx\nabd,DK,second_DK.xlsx\n",
                                           encoding="utf-8")
    log = tmp_path / "dziennik_PB.md"
    log.write_text("Wykluczono DK i WD.\n", encoding="utf-8")
    cfg.raw["export"] = {"coder_aliases": {"PB": "A", "DK": "X1", "WD": "X2"}}
    import yaml
    (cfg.root / "config.yaml").write_text(yaml.safe_dump(cfg.raw, allow_unicode=True), encoding="utf-8")
    assert main(["export", "--osf", "--add", str(log)] + d) == 0
    out = next((cfg.root / "export_dryrun").glob("*_osf"))
    codes = (out / "codes" / "human_codes.csv").read_text(encoding="utf-8")
    assert ",A,sheet_A.xlsx" in codes and ",X1,second_X1.xlsx" in codes and "PB" not in codes
    assert (out / "docs" / "dziennik_A.md").read_text(encoding="utf-8") == "Wykluczono X1 i X2.\n"
    with zipfile.ZipFile(out / "images_blinded.zip") as z:
        assert any(n.endswith(".png") for n in z.namelist())
    for f in ("README.md", "DATA_DICTIONARY.md", "LICENSE-DATA.txt", "MANIFEST.csv"):
        assert (out / f).exists(), f
    assert "images_blinded.zip" in (out / "MANIFEST.csv").read_text(encoding="utf-8")


def test_anonymise_tree_keeps_raw_logs(tmp_path):
    from kkai.export import anonymise_tree
    (tmp_path / "codes").mkdir()
    (tmp_path / "codes" / "ai_raw.jsonl").write_text('{"text": "DW tram"}\n', encoding="utf-8")
    (tmp_path / "codes" / "human_codes.csv").write_text("x,DW\n", encoding="utf-8")
    counts = anonymise_tree(tmp_path, {"DW": "C1"})
    assert (tmp_path / "codes" / "ai_raw.jsonl").read_text(encoding="utf-8") == '{"text": "DW tram"}\n'
    assert counts == {"codes/human_codes.csv": 1}
