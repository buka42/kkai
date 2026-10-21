"""Full --dry-run from plan to walls, figure and export, through the command line."""

from kkai.cli import main


def test_full_dry_run(cfg, monkeypatch):
    monkeypatch.chdir(cfg.root)
    d = ["--dry-run"]
    steps = [
        ["plan", "--stage", "main"], ["generate", "--stage", "main"], ["prepare", "--stage", "main"], ["sample"],
        ["code", "--set", "main"], ["code", "--set", "validation-repeat"], ["sheet", "--set", "validation"],
    ]
    for s in steps:
        assert main(s + d) == 0, s
    assert main(["simulate-human", "--sheet", "validation_sheet.xlsx"]) == 0
    assert main(["ingest", "--sheet", "data_dryrun/human/validation_sheet_filled.xlsx", "--set", "validation",
                 "--coder-id", "PB"] + d) == 0
    assert main(["validate"] + d) == 0
    assert main(["simulate-human", "--sheet", "decisions"]) == 0
    assert main(["review"] + d) == 0
    assert main(["simulate-human", "--sheet", "review_sheet.xlsx"]) == 0
    assert main(["review", "--ingest", "data_dryrun/human/review_sheet_filled.xlsx"] + d) == 0
    for s in (["analyze"], ["walls"], ["figure"], ["export"]):
        assert main(s + d) == 0, s
    assert len(list((cfg.data_dir / "results" / "walls").glob("*.png"))) == 16
