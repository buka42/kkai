import csv

import pytest

from kkai.analyze import holm, run_analyze, wilson
from kkai.prepare import KEY_FIELDS


def test_wilson_known_value():
    lo, hi = wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)


def test_holm():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def _write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def test_synthetic_effect_detected(cfg):
    """W: 80% historical, B: 20% historical (OA only); GG: no difference."""
    key, final, n = [], [], 0
    for f in ("B", "W", "T", "WT"):
        for s in ("K", "Z"):
            for lang in ("PL", "EN"):
                for g in ("OA", "GG"):
                    for rep in range(20):
                        iid = f"img_{n:06x}"
                        n += 1
                        share = {"W": 0.8, "B": 0.2}.get(f, 0.5) if g == "OA" else 0.5
                        hist = rep < share * 20
                        key.append({"image_id": iid, "stage": "main", "condition_code": f"{f}-{s}-{lang}-{g}",
                                    "frame": f, "scale": s, "language": lang, "generator": g})
                        final.append({"image_id": iid, "temporal_frame": "historical" if hist else "contemporary",
                                      "mode_dominant": "everyday", "religion_form": "none"})
    _write(cfg.data_dir / "key" / "key.csv", key, KEY_FIELDS)
    _write(cfg.data_dir / "human" / "final_codes.csv", final, ["image_id", "temporal_frame", "mode_dominant", "religion_form"])
    out = run_analyze(cfg)
    with open(out / "tables" / "hypotheses.csv", encoding="utf-8") as fh:
        rows = {(r["hypothesis"], r["generator"], r["analysis"]): r for r in csv.DictReader(fh)}
    h1 = rows[("H1", "OA", "confirmatory")]
    assert (h1["group_a_n"], h1["group_b_n"]) == ("80", "80")
    assert float(h1["group_a_p"]) == pytest.approx(0.8) and float(h1["group_b_p"]) == pytest.approx(0.2)
    assert h1["supported"] == "True"
    assert rows[("H1", "GG", "confirmatory")]["supported"] == "False"
    h4 = rows[("H4", "OA", "confirmatory")]
    assert (h4["group_a_n"], h4["group_b_n"]) == ("40", "40")
    with open(out / "tables" / "conditions.csv", encoding="utf-8") as fh:
        cond = {r["condition_code"]: r for r in csv.DictReader(fh)}
    assert len(cond) == 32
    assert float(cond["W-K-EN-OA"]["hist_or_staged_p"]) == pytest.approx(0.8)
