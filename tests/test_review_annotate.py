import json
import threading
import urllib.request

from kkai.cli import main
from kkai.review_annotate import ReviewSession
from kkai.annotate import serve
from kkai.util import read_csv


def _to_gate3(cfg, monkeypatch):
    monkeypatch.chdir(cfg.root)
    d = ["--dry-run"]
    for s in (["plan", "--stage", "main"], ["generate", "--stage", "main"], ["prepare", "--stage", "main"], ["sample"],
              ["code", "--set", "main"], ["code", "--set", "validation-repeat"], ["sheet", "--set", "validation"]):
        assert main(s + d) == 0, s
    assert main(["simulate-human", "--sheet", "validation_sheet.xlsx"]) == 0
    assert main(["ingest", "--sheet", "data_dryrun/human/validation_sheet_filled.xlsx", "--set", "validation",
                 "--coder-id", "PB"] + d) == 0
    # Gate 3 as decided on 25.10: two variables by hand, the rest reviewed.
    rows = ["variable,decision"]
    for v in ("medium", "people_count", "temporal_frame", "contemporary_cue_types", "historical_cue_types",
              "mode_dominant", "mode_secondary", "roles", "religion_form", "religion_traditions", "scripts",
              "place", "landmarks"):
        dec = "manual_all" if v in ("mode_dominant", "roles") else (
            "review_all" if v in ("temporal_frame", "place", "religion_traditions", "scripts") else "review_flagged")
        rows.append(f"{v},{dec}")
    (cfg.dir("human") / "decisions.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _accept(session, iid, **changes):
    """Answer that keeps the model codes and fills the hand-coded variables."""
    it = session.items()[iid]
    rec = {"image_id": iid, "notes": "", "seconds": 3}
    for v in it["review"]:
        rec[v] = it["model"][v]
    for v in it["manual"]:
        rec[v] = [] if v == "roles" else ("everyday" if v == "mode_dominant" else session.allowed[v][0])
    rec.update(changes)
    # The page clears codes that break the codebook rules (landmarks without place = landmark).
    if "landmarks" in rec and rec.get("place", it["model"]["place"]) != "landmark":
        rec["landmarks"] = []
    if "roles" in rec and rec.get("people_count", it["model"]["people_count"]) == "none":
        rec["roles"] = []
    return rec


def test_review_annotate_round_trip(cfg, monkeypatch):
    _to_gate3(cfg, monkeypatch)
    s = ReviewSession(cfg, "PB")
    n = len(s.ids)  # main images outside the validation set (dry run: some refusals)
    assert n > 400
    first, second = s.ids[0], s.ids[1]
    assert set(s.plan[first]["manual"]) == {"mode_dominant", "roles"}
    bad = s.save({"image_id": first, "roles": []})
    assert not bad["ok"] and any("brak wyboru" in e for e in bad["errors"])
    assert "Brakuje" in str(_raises(s.export))
    for iid in s.ids:
        r = s.save(_accept(s, iid))
        assert r["ok"], (iid, r)
    old_frame = s.items()[second]["model"]["temporal_frame"]
    new_frame = "indeterminate" if old_frame != "indeterminate" else "contemporary"
    assert s.save(_accept(s, second, temporal_frame=new_frame, notes="tło"))["ok"]
    path = s.export()
    assert main(["review", "--ingest", str(path), "--dry-run"]) == 0
    corr = read_csv(cfg.dir("human") / "review_corrections.csv")
    assert {(c["image_id"], c["variable"]) for c in corr if c["variable"] not in ("mode_dominant", "roles", "landmarks")} == \
        {(second, "temporal_frame")}
    assert sum(1 for c in corr if c["variable"] == "mode_dominant") == n
    final = {r["image_id"]: r for r in read_csv(cfg.dir("human") / "final_codes.csv")}
    assert final[second]["temporal_frame"] == new_frame and final[second]["temporal_frame__source"] == "review"
    assert final[first]["mode_dominant__source"] == "manual" and final[first]["roles"] == ""
    assert not any(r[f"{v}__source"] == "missing" for r in final.values() for v in ("mode_dominant", "roles"))


def _raises(fn):
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        return e
    raise AssertionError("no exception")


def test_review_page_is_blind(cfg, monkeypatch):
    _to_gate3(cfg, monkeypatch)
    s = ReviewSession(cfg, "PB")
    server = serve(s, port=18865, open_browser=False)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        page = urllib.request.urlopen(base + "/").read().decode("utf-8")
        assert "reviewRender" in page
        text = json.dumps(json.loads(urllib.request.urlopen(base + "/api/state").read()))
        for word in ("condition", "generator", "prompt", "request_uid", "run_id", "\"OA\"", "\"GG\""):
            assert word not in text
    finally:
        server.shutdown()
        server.server_close()
