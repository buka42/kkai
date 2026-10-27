import csv
import math
import random

import pytest

from kkai.prepare import KEY_FIELDS
from kkai.util import KkaiError
from kkai.validate import alpha_nominal, decide, gwet_ac1, percent_agreement, reliability_level, run_validate, value, variables


def test_alpha_identical_is_one():
    assert alpha_nominal([["a", "b", "a", "c"], ["a", "b", "a", "c"]]) == pytest.approx(1.0)


def test_alpha_known_value():
    # Krippendorff (2011) nominal example reduced to 2 coders: disagreement lowers alpha below 1.
    v = alpha_nominal([["a", "a", "b", "b", "c"], ["a", "b", "b", "b", "c"]])
    assert 0 < v < 1


def test_decide_rules():
    assert decide(0.85, 0.95, False) == "review_flagged"
    assert decide(0.85, 0.85, False) == "review_all"
    assert decide(0.75, 0.95, False) == "review_all"
    assert decide(0.60, 0.95, False) == "manual_all"
    assert decide(0.90, 0.95, True) == "manual_all"
    assert decide(float("nan"), 0.9, False) == "no_data"


def test_ac1_and_agreement_on_skewed_data():
    # Pilot 1 pattern: 31 of 32 one category, 2 disagreements -> low alpha, high AC1.
    a = {i: "contemporary" for i in range(32)}
    b = dict(a)
    a[0], b[1] = "indeterminate", "indeterminate"
    assert percent_agreement(a, b) == pytest.approx(30 / 32)
    assert alpha_nominal([[a[i] for i in range(32)], [b[i] for i in range(32)]]) < 0.1
    assert gwet_ac1(a, b, ["contemporary", "historical", "staged_historical", "indeterminate"]) > 0.9
    assert gwet_ac1(a, a, ["contemporary", "indeterminate"]) == pytest.approx(1.0)


def test_reliability_level_skewed_rule():
    assert reliability_level(0.30, 0.96, 0.85, skewed=True) == 0.80
    assert reliability_level(0.30, 0.94, 0.85, skewed=True) == 0.67
    assert reliability_level(0.30, 0.89, 0.85, skewed=True) == 0.0
    assert reliability_level(0.85, 0.80, 0.50, skewed=False) == 0.80
    assert reliability_level(0.70, 0.80, 0.50, skewed=False) == 0.67
    assert math.isnan(reliability_level(float("nan"), float("nan"), float("nan"), skewed=False))


def test_hebrew_combined_category():
    allowed = {"roles": ["sightseeing"], "scripts": ["latin", "hebrew", "hebrew_like"], "religion_traditions": ["jewish"]}
    names = [n for n, _, _ in variables(allowed)]
    assert "scripts:hebrew+hebrew_like" in names
    assert value({"scripts": "hebrew_like;latin"}, "scripts", "hebrew+hebrew_like") == "1"
    assert value({"scripts": "hebrew"}, "scripts", "hebrew+hebrew_like") == "1"
    assert value({"scripts": "latin"}, "scripts", "hebrew+hebrew_like") == "0"
    assert value({"scripts": "hebrew"}, "scripts", "hebrew_like") == "0"


def _write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _setup(cfg, model_fn):
    rng = random.Random(0)
    key, ai, human = [], [], []
    frames, temporal = ["B", "W", "T", "WT"], ["contemporary", "historical", "staged_historical", "indeterminate"]
    for i in range(160):
        f, g = frames[i % 4], ["OA", "GG"][i % 2]
        iid = f"img_{i:06x}"
        key.append({"image_id": iid, "stage": "main", "condition_code": f"{f}-K-EN-{g}", "frame": f, "scale": "K",
                    "language": "EN", "generator": g})
        true = {"medium": rng.choice(["photo_colour", "photo_aged"]), "temporal_frame": rng.choice(temporal),
                "mode_dominant": rng.choice(["heritage", "everyday", "spectacle"]), "religion_form": rng.choice(["none", "building"]),
                "place": rng.choice(["landmark", "generic_historic_townscape"]),
                "roles": rng.choice(["", "sightseeing", "everyday_activity;sightseeing"]),
                "scripts": rng.choice(["", "latin"]), "religion_traditions": rng.choice(["", "christian"])}
        human.append({"image_id": iid, "coder_id": "PB", "set": "validation", "round": "1", **true})
        for run in ("main-r1", "validation-repeat-r1"):
            ai.append({"image_id": iid, "run_id": run, "set": run.rsplit("-r", 1)[0], "valid": "True",
                       **model_fn(true, f, rng)})
    _write(cfg.data_dir / "key" / "key.csv", key, KEY_FIELDS)
    _write(cfg.data_dir / "ai" / "ai_codes.csv", ai, list(ai[0]))
    _write(cfg.data_dir / "human" / "human_codes.csv", human, list(human[0]))


def _table(out_dir):
    with open(out_dir / "validation_table.csv", encoding="utf-8") as f:
        return {r["variable"]: r for r in csv.DictReader(f)}


def test_perfect_model(cfg):
    cfg.raw["validation"]["bootstrap"] = 50
    _setup(cfg, lambda t, f, rng: dict(t))
    t = _table(run_validate(cfg))
    assert float(t["temporal_frame"]["alpha_model_human"]) == pytest.approx(1.0)
    assert t["temporal_frame"]["decision"] == "review_flagged"
    assert t["roles"]["decision"] == "review_flagged"


def test_model_errs_only_in_multicultural_conditions(cfg):
    cfg.raw["validation"]["bootstrap"] = 50

    def model(t, frame, rng):
        out = dict(t)
        if frame in ("W", "WT"):
            out["temporal_frame"] = "historical" if t["temporal_frame"] != "historical" else "contemporary"
        return out

    _setup(cfg, model)
    t = _table(run_validate(cfg))
    row = t["temporal_frame"]
    assert row["differential_error"] == "True"
    assert row["decision"] == "manual_all"
    assert float(row["error_rate_W_WT"]) == 1.0 and float(row["error_rate_B_T"]) == 0.0


def test_flag_rates_per_condition_and_frame():
    from kkai.validate import flag_rates
    key = {"a": {"condition_code": "W-K-EN-OA", "frame": "W"}, "b": {"condition_code": "W-K-EN-OA", "frame": "W"},
           "c": {"condition_code": "B-K-EN-OA", "frame": "B"}}
    model = [{"image_id": "a", "review_reasons": "religion_present", "flags_missing": "", "identity_terms": ""},
             {"image_id": "b", "review_reasons": "", "flags_missing": "", "identity_terms": "jews"},
             {"image_id": "c", "review_reasons": "", "flags_missing": "", "identity_terms": ""}]
    rows = {(r["level"], r["group"]): r for r in flag_rates(model, key)}
    w = rows[("condition", "W-K-EN-OA")]
    assert w["n"] == 2 and w["any_flag"] == 1.0 and w["religion_present"] == 0.5 and w["identity_terms"] == 0.5
    assert rows[("frame", "B")]["any_flag"] == 0.0


def test_excluded_second_coder_is_ignored(cfg):
    """Codes of an excluded coder stay in human_codes.csv but count in no agreement."""
    cfg.raw["validation"]["bootstrap"] = 50
    _setup(cfg, lambda t, f, rng: dict(t))
    path = cfg.data_dir / "human" / "human_codes.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    first50 = [r for r in rows if r["set"] == "validation"][:50]
    flipped = {"contemporary": "historical", "historical": "contemporary",
               "staged_historical": "indeterminate", "indeterminate": "staged_historical"}
    bad = [{**r, "coder_id": "DK", "set": "second", "temporal_frame": flipped[r["temporal_frame"]]} for r in first50]
    good = [{**r, "coder_id": "KR", "set": "second"} for r in first50]
    _write(path, rows + bad + good, list(rows[0]))
    cfg.raw["validation"]["excluded_coders"] = ["DK"]
    out = run_validate(cfg)
    assert float(_table(out)["temporal_frame"]["second_coder_alpha"]) == pytest.approx(1.0)
    assert "wykluczeni koderzy: DK" in (out / "validation_report.html").read_text(encoding="utf-8")
    assert sum(1 for r in csv.DictReader(open(path, encoding="utf-8")) if r["coder_id"] == "DK") == 50
    cfg.raw["validation"]["excluded_coders"] = ["PB"]
    with pytest.raises(KkaiError):
        run_validate(cfg)
