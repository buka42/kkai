import io
import json

import pytest
from PIL import Image

from kkai import providers as P
from kkai.generate import read_log, run_generate
from kkai.plan import write_plan
from kkai.util import KkaiError


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(buf, format="PNG")
    return buf.getvalue()


class Scripted:
    """Provider returning a scripted sequence of statuses, then OK."""

    def __init__(self, script=(), model="m1"):
        self.script = list(script)
        self.calls = 0
        self.model = model

    def generate(self, prompt, label=""):
        self.calls += 1
        st = self.script.pop(0) if self.script else P.OK
        if st == P.OK:
            return P.GenResult(status=P.OK, image=png(), image_mime="image/png", raw={"x": 1},
                               model_returned=self.model, n_images_returned=1)
        if st == P.CORRUPT:
            return P.GenResult(status=P.OK, image=b"not an image", image_mime="image/png", raw={"x": 1},
                               model_returned=self.model)
        if st == "fatal":
            raise P.FatalProviderError("bad key")
        return P.GenResult(status=st, raw={"err": st}, error_code=st)


def run(cfg, provs, **kw):
    return run_generate(cfg, "test", assume_yes=True, providers=provs, sleep=lambda s: None, **kw)


def test_full_run_and_resume_without_duplicates(cfg):
    write_plan(cfg, "test")
    provs = {"OA": Scripted(), "GG": Scripted()}
    run(cfg, provs, limit=3)
    run(cfg, provs)
    run(cfg, provs)
    log = read_log(cfg, "test")
    assert len(log) == 8
    assert len({r["request_uid"] for r in log}) == 8
    assert all(r["final"] and r["status"] == "ok" for r in log)
    assert len(list((cfg.data_dir / "raw").glob("*.png"))) == 8


def test_refusal_is_final_and_not_retried(cfg):
    write_plan(cfg, "test")
    provs = {"OA": Scripted([P.REFUSED] * 4), "GG": Scripted([P.REFUSED] * 4)}
    run(cfg, provs)
    log = read_log(cfg, "test")
    assert len(log) == 8 and all(r["status"] == "refused" and r["attempt"] == 1 for r in log)


def test_technical_errors_retried_three_times(cfg):
    write_plan(cfg, "test")
    provs = {"OA": Scripted([P.TECHNICAL] * 4), "GG": Scripted([P.TECHNICAL] * 2)}
    run(cfg, provs)
    log = read_log(cfg, "test")
    oa_first = [r for r in log if r["generator"] == "OA"]
    first_uid = oa_first[0]["request_uid"]
    attempts = [r for r in log if r["request_uid"] == first_uid]
    assert [r["attempt"] for r in attempts] == [1, 2, 3, 4]
    assert attempts[-1]["final"] and attempts[-1]["status"] == P.TECHNICAL
    assert not any(r["final"] for r in attempts[:-1])
    gg_uid = [r for r in log if r["generator"] == "GG"][0]["request_uid"]
    assert [r["status"] for r in log if r["request_uid"] == gg_uid] == [P.TECHNICAL, P.TECHNICAL, P.OK]


def test_retry_errors_flag_continues_attempt_numbers(cfg):
    write_plan(cfg, "test")
    run(cfg, {"OA": Scripted([P.TECHNICAL] * 4), "GG": Scripted()})
    run(cfg, {"OA": Scripted(), "GG": Scripted()}, retry_errors=True)
    log = read_log(cfg, "test")
    uid = [r for r in log if r["generator"] == "OA"][0]["request_uid"]
    assert [r["attempt"] for r in log if r["request_uid"] == uid] == [1, 2, 3, 4, 5]


def test_corrupt_file_retried_once(cfg):
    write_plan(cfg, "test")
    run(cfg, {"OA": Scripted([P.CORRUPT, P.CORRUPT]), "GG": Scripted()})
    log = read_log(cfg, "test")
    uid = [r for r in log if r["generator"] == "OA"][0]["request_uid"]
    sts = [r["status"] for r in log if r["request_uid"] == uid]
    assert sts == [P.CORRUPT, P.CORRUPT]


def test_fatal_error_stops_run(cfg):
    write_plan(cfg, "test")
    with pytest.raises(KkaiError):
        run(cfg, {"OA": Scripted(["fatal"]), "GG": Scripted(["fatal"])})
    assert all(not r["final"] for r in read_log(cfg, "test"))


def test_model_version_change_stops_run(cfg):
    write_plan(cfg, "test")
    run(cfg, {"OA": Scripted(model="v1"), "GG": Scripted()}, limit=2)
    with pytest.raises(KkaiError, match="wersj"):
        run(cfg, {"OA": Scripted(model="v2"), "GG": Scripted()})


def test_log_fields_and_no_key_in_log(cfg, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-SECRET-should-not-appear")
    write_plan(cfg, "test")
    run(cfg, {"OA": Scripted(), "GG": Scripted()})
    text = (cfg.data_dir / "logs" / "generation_log.jsonl").read_text(encoding="utf-8")
    assert "SECRET" not in text
    rec = json.loads(text.splitlines()[0])
    for f in ("request_uid", "attempt", "stage", "condition_code", "prompt_exact", "language", "generator",
              "model_requested", "model_returned", "params", "ts_start", "ts_end", "status", "error_code",
              "error_message", "text_parts", "usage", "cost_usd", "raw_file", "sha256", "script_version",
              "shuffle_seed"):
        assert f in rec


def test_dry_run_fake_provider_end_to_end(cfg):
    write_plan(cfg, "test")
    out = run_generate(cfg, "test", assume_yes=True)
    assert out["executed"] == 8


def test_cost_limit_stops_before_calls(cfg):
    cfg.dry_run = False
    cfg.raw["data_dir"] = str(cfg.data_dir)  # keep files in tmp
    write_plan(cfg, "test")
    for g in cfg.generators.values():
        g["cost_per_image_usd"] = 100
    prov = Scripted()
    with pytest.raises(KkaiError, match="max_cost_usd"):
        run_generate(cfg, "test", assume_yes=True, providers={"OA": prov, "GG": prov}, sleep=lambda s: None)
    assert prov.calls == 0
