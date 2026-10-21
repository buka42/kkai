"""Confirmatory tests H1–H4, condition-level proportions, sensitivity and robustness tables."""

from __future__ import annotations

import csv
import html
import math
from collections import defaultdict
from pathlib import Path

from .config import Config
from .generate import read_log, request_state
from .plan import FRAMES, LANGUAGES, SCALES
from .prepare import read_key
from .util import KkaiError, read_csv, utc_now, write_new_text

INDICATORS = {
    "hist_or_staged": ("temporal_frame", {"historical", "staged_historical"}),
    "heritage_or_spectacle": ("mode_dominant", {"heritage", "spectacle"}),
    "not_contemporary": ("temporal_frame", {"historical", "staged_historical", "indeterminate"}),
    "religion_present": ("religion_form", {"building", "symbol_or_object", "practice"}),
}

# (code, indicator, group A = expected higher, group B, filter) per protocol section 7.
HYPOTHESES = [
    ("H1", "hist_or_staged", lambda k: k["frame"] == "W", lambda k: k["frame"] == "B"),
    ("H2", "hist_or_staged", lambda k: k["frame"] == "WT", lambda k: k["frame"] == "T"),
    ("H3", "heritage_or_spectacle", lambda k: k["frame"] == "W", lambda k: k["frame"] == "B"),
    ("H4", "not_contemporary", lambda k: k["frame"] == "T" and k["scale"] == "Z",
     lambda k: k["frame"] == "T" and k["scale"] == "K"),
]
SENSITIVITY = {"H1", "H2", "H4"}


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    from statsmodels.stats.proportion import proportion_confint
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    return float(lo), float(hi)


def holm(pvals: list[float]) -> list[float]:
    from statsmodels.stats.multitest import multipletests
    return list(multipletests(pvals, alpha=0.05, method="holm")[1])


def fisher_greater(a_k, a_n, b_k, b_n) -> float:
    from scipy.stats import fisher_exact
    return float(fisher_exact([[a_k, a_n - a_k], [b_k, b_n - b_k]], alternative="greater").pvalue)


def load_dataset(cfg: Config) -> list[dict]:
    path = cfg.dir("human") / "final_codes.csv"
    if not path.exists():
        raise KkaiError("Brak final_codes.csv. Najpierw: kkai review --ingest …")
    final = {r["image_id"]: r for r in read_csv(path)}
    rows = []
    for k in read_key(cfg):
        if k["stage"] == "main" and k["image_id"] in final:
            rows.append({**k, **final[k["image_id"]]})
    return rows


def has(row: dict, indicator: str) -> bool | None:
    col, vals = INDICATORS[indicator]
    v = row.get(col, "")
    return None if not v else v in vals


def run_analyze(cfg: Config) -> Path:
    data = load_dataset(cfg)
    gens = list(cfg.generators)
    out_dir = cfg.dir("results") / "analysis" / utc_now().replace(":", "").replace(".", "_")
    tdir = out_dir / "tables"
    tdir.mkdir(parents=True)

    # Refusals and other image-less results per condition (denominator: all planned requests).
    final = [s["final"] for s in request_state(read_log(cfg, "main")).values() if s["final"]]
    req = defaultdict(lambda: defaultdict(int))
    for r in final:
        req[r["condition_code"]]["requests"] += 1
        req[r["condition_code"]][r["status"]] += 1

    # 1. Proportions with Wilson intervals in each of the 32 conditions.
    cond_rows = []
    for f in FRAMES:
        for s in SCALES:
            for lang in LANGUAGES:
                for g in gens:
                    code = f"{f}-{s}-{lang}-{g}"
                    sub = [r for r in data if r["condition_code"] == code]
                    row = {"condition_code": code, "frame": f, "scale": s, "language": lang, "generator": g,
                           "requests": req[code]["requests"], "refused": req[code]["refused"],
                           "no_image": req[code]["no_image"], "coded": len(sub)}
                    row["refusal_rate"] = row["refused"] / row["requests"] if row["requests"] else float("nan")
                    for ind in INDICATORS:
                        vals = [has(r, ind) for r in sub if has(r, ind) is not None]
                        k, n = sum(vals), len(vals)
                        lo, hi = wilson(k, n)
                        row.update({f"{ind}_k": k, f"{ind}_n": n, f"{ind}_p": k / n if n else float("nan"),
                                    f"{ind}_lo": lo, f"{ind}_hi": hi})
                    cond_rows.append(row)
    _write(tdir / "conditions.csv", cond_rows)

    # 2. Confirmatory tests: 4 hypotheses x generators, Holm over all.
    tests = []
    for code, ind, ga, gb in HYPOTHESES:
        for g in gens:
            for sensitivity in ([False, True] if code in SENSITIVITY else [False]):
                sub = [r for r in data if r["generator"] == g]
                if sensitivity:
                    sub = [r for r in sub if r.get("temporal_frame") != "indeterminate"]
                a = [has(r, ind) for r in sub if ga(r) and has(r, ind) is not None]
                b = [has(r, ind) for r in sub if gb(r) and has(r, ind) is not None]
                ak, an, bk, bn = sum(a), len(a), sum(b), len(b)
                p = fisher_greater(ak, an, bk, bn) if an and bn else float("nan")
                tests.append({"hypothesis": code, "generator": g, "indicator": ind,
                              "analysis": "sensitivity_no_indeterminate" if sensitivity else "confirmatory",
                              "group_a_k": ak, "group_a_n": an, "group_a_p": ak / an if an else float("nan"),
                              "group_b_k": bk, "group_b_n": bn, "group_b_p": bk / bn if bn else float("nan"),
                              "difference_pp": 100 * (ak / an - bk / bn) if an and bn else float("nan"),
                              "p_one_sided": p})
    conf = [t for t in tests if t["analysis"] == "confirmatory"]
    adj = holm([t["p_one_sided"] if not math.isnan(t["p_one_sided"]) else 1.0 for t in conf])
    for t, pa in zip(conf, adj):
        t["p_holm"] = pa
        t["supported"] = pa < 0.05 and t["difference_pp"] > 0
    for t in tests:
        t.setdefault("p_holm", "")
        t.setdefault("supported", "")
    _write(tdir / "hypotheses.csv", tests)

    # 3. Robustness: effect of each hypothesis by language (descriptive, no tests).
    robust = []
    for code, ind, ga, gb in HYPOTHESES:
        for g in gens:
            for lang in LANGUAGES:
                sub = [r for r in data if r["generator"] == g and r["language"] == lang]
                a = [has(r, ind) for r in sub if ga(r) and has(r, ind) is not None]
                b = [has(r, ind) for r in sub if gb(r) and has(r, ind) is not None]
                robust.append({"hypothesis": code, "generator": g, "language": lang,
                               "group_a_p": sum(a) / len(a) if a else float("nan"), "group_a_n": len(a),
                               "group_b_p": sum(b) / len(b) if b else float("nan"), "group_b_n": len(b),
                               "difference_pp": 100 * (sum(a) / len(a) - sum(b) / len(b)) if a and b else float("nan")})
            for s in SCALES:
                if code == "H4":
                    continue
                sub = [r for r in data if r["generator"] == g and r["scale"] == s]
                a = [has(r, ind) for r in sub if ga(r) and has(r, ind) is not None]
                b = [has(r, ind) for r in sub if gb(r) and has(r, ind) is not None]
                robust.append({"hypothesis": code, "generator": g, "scale": s,
                               "group_a_p": sum(a) / len(a) if a else float("nan"), "group_a_n": len(a),
                               "group_b_p": sum(b) / len(b) if b else float("nan"), "group_b_n": len(b),
                               "difference_pp": 100 * (sum(a) / len(a) - sum(b) / len(b)) if a and b else float("nan")})
    _write(tdir / "robustness.csv", robust)

    # 4. P5 (exploratory): religion form and traditions in each condition.
    p5 = []
    for c in sorted({r["condition_code"] for r in data}):
        sub = [r for r in data if r["condition_code"] == c]
        row = {"condition_code": c, "n": len(sub)}
        for form in ("none", "building", "symbol_or_object", "practice"):
            row[f"form_{form}"] = sum(r.get("religion_form") == form for r in sub)
        for trad in ("jewish", "christian", "christian_orthodox", "muslim", "other", "indeterminate"):
            row[f"trad_{trad}"] = sum(trad in r.get("religion_traditions", "").split(";") for r in sub)
        for sc in ("latin", "hebrew", "hebrew_like", "cyrillic", "other"):
            row[f"script_{sc}"] = sum(sc in r.get("scripts", "").split(";") for r in sub)
        p5.append(row)
    _write(tdir / "religion_scripts.csv", p5)

    write_new_text(out_dir / "analysis_report.html", _report(cond_rows, tests, robust, len(data)))
    print(f"Raport analizy: {out_dir / 'analysis_report.html'}")
    for t in conf:
        print(f"  {t['hypothesis']} {t['generator']}: {t['group_a_p']:.2f} vs {t['group_b_p']:.2f}, "
              f"p Holm = {t['p_holm']:.4f} → {'potwierdzona' if t['supported'] else 'niepotwierdzona'}")
    return out_dir


def _fmt(v):
    if isinstance(v, float):
        return "" if math.isnan(v) else f"{v:.3f}"
    return "" if v is None else str(v)


def _write(path: Path, rows: list[dict]) -> None:
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: _fmt(v) for k, v in r.items()})


def _table(rows: list[dict], cols: list[str]) -> str:
    head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(_fmt(r.get(c)))}</td>" for c in cols) + "</tr>" for r in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def _report(cond_rows, tests, robust, n) -> str:
    cond_cols = ["condition_code", "requests", "refused", "coded", "hist_or_staged_p", "hist_or_staged_lo",
                 "hist_or_staged_hi", "heritage_or_spectacle_p", "not_contemporary_p", "religion_present_p"]
    test_cols = ["hypothesis", "generator", "analysis", "group_a_k", "group_a_n", "group_a_p", "group_b_k",
                 "group_b_n", "group_b_p", "difference_pp", "p_one_sided", "p_holm", "supported"]
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>Analiza</title>
<style>body{{font-family:sans-serif;margin:16px}}table{{border-collapse:collapse;margin-bottom:24px}}
td,th{{border:1px solid #ccc;padding:3px 6px;font-size:13px}}</style></head><body>
<h1>Analiza</h1><p>Obrazów z kodami końcowymi: {n}. Mianownik: obrazy zakodowane; odmowy osobno.
Testy: dokładny test Fishera, jednostronny; korekta Holma dla testów konfirmacyjnych; potwierdzenie przy p po korekcie &lt; .05 i zgodnym kierunku.</p>
<h2>Hipotezy</h2>{_table(tests, test_cols)}
<h2>Warunki (przedziały Wilsona 95%)</h2>{_table(cond_rows, cond_cols)}
<h2>Odporność (opisowo)</h2>{_table(robust, ["hypothesis", "generator", "language", "scale", "group_a_p", "group_a_n", "group_b_p", "group_b_n", "difference_pp"])}
</body></html>"""
