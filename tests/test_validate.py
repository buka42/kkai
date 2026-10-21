import csv
import math
import random

import pytest

from kkai.prepare import KEY_FIELDS
from kkai.validate import alpha_nominal, decide, run_validate


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
