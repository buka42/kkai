import json
import threading
import urllib.request

from kkai.annotate import Session, serve
from kkai.generate import run_generate
from kkai.ingest import run_ingest
from kkai.plan import write_plan
from kkai.prepare import run_prepare
from kkai.util import read_csv


def _pilot(cfg):
    write_plan(cfg, "pilot")
    run_generate(cfg, "pilot", assume_yes=True)
    run_prepare(cfg, "pilot")


def _answer(session, iid):
    rec = {"image_id": iid, "notes": "", "seconds": 5}
    for v in session.variables():
        rec[v["name"]] = [] if v["multi"] else v["values"][0]["code"]
    rec["people_count"] = "crowd"
    rec["place"] = "generic_historic_townscape"
    return rec


def test_annotate_save_export_ingest(cfg):
    _pilot(cfg)
    s = Session(cfg, "pilot", "PB")
    first = s.ids[0]
    bad = s.save({"image_id": first, "people_count": "none", "roles": ["sightseeing"]})
    assert not bad["ok"] and any("Liczba osób" in e for e in bad["errors"])
    for iid in s.ids:
        assert s.save(_answer(s, iid))["ok"]
    # A later save of the same image wins; the log keeps both.
    again = _answer(s, first)
    again["notes"] = "second thoughts"
    assert s.save(again)["ok"]
    assert s.answers()[first]["notes"] == "second thoughts"
    assert sum(1 for _ in open(s.log, encoding="utf-8")) == len(s.ids) + 1
    path = s.export()
    run_ingest(cfg, path, "pilot", "PB")
    rows = read_csv(cfg.dir("human") / "human_codes.csv")
    assert len(rows) == len(s.ids) and {r["image_id"] for r in rows} == set(s.ids)


def test_annotate_page_is_blind(cfg):
    _pilot(cfg)
    s = Session(cfg, "pilot", "PB")
    server = serve(s, port=18765, open_browser=False)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        state = json.loads(urllib.request.urlopen(base + "/api/state").read())
        text = json.dumps(state)
        for word in ("condition", "generator", "prompt", "request_uid", "OA", "GG"):
            assert word not in text
        img = urllib.request.urlopen(base + f"/img/{s.ids[0]}.png").read()
        assert img[:4] == b"\x89PNG"
        req = urllib.request.Request(base + "/api/hint", data=json.dumps(
            {"contemporary_cue_types": ["mobile_device", "modern_clothing"], "historical_cue_types": []}).encode(),
            headers={"Content-Type": "application/json"})
        assert json.loads(urllib.request.urlopen(req).read())["frame"] == "contemporary"
    finally:
        server.shutdown()
        server.server_close()
