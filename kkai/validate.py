"""Agreement between the AI coder and the human coder; decision table for gate 3.

Per variable: Krippendorff's alpha model–human (bootstrap CI over images),
percent agreement and Gwet's AC1 (used instead of alpha when one category
covers more than 90% of the validation images, protocol 0.9.5 sec. 6),
model stability (two model runs), confusion matrices, differential error
(W/WT vs B/T; OA vs GG), test–retest and, if present, the second coder.
"""

from __future__ import annotations

import csv
import html
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .codebook import FLAG_VARIABLES, SECOND_CODER_COLUMNS, SHEET_COLUMNS, allowed_values, load_schema
from .config import Config
from .prepare import read_key
from .util import KkaiError, read_csv, utc_now, write_new_text

SINGLE_VARS = ["medium", "temporal_frame", "mode_dominant", "religion_form", "place"]
# Multi-select variables are split into one 0/1 variable per category (02_kodeks.md).
BINARY_FROM = ["roles", "scripts", "religion_traditions"]
# Categories assessed together as one 0/1 variable (protocol 0.9.5 sec. 6); the parts are still reported.
COMBINED = {"scripts": [("hebrew", "hebrew_like")]}
SKEW_SHARE = 0.90
# (reliability level, minimum percent agreement, minimum AC1) for skewed variables.
SKEW_RULES = ((0.80, 0.95, 0.80), (0.67, 0.90, 0.67))


def alpha_nominal(data: list[list]) -> float:
    """Krippendorff's alpha (nominal) for rows = coders, columns = units; None = missing."""
    import krippendorff
    cats = sorted({v for row in data for v in row if v is not None})
    if not cats:
        return float("nan")
    pairable = [[row[j] for row in data] for j in range(len(data[0]))]
    pairable = [u for u in pairable if sum(v is not None for v in u) >= 2]
    if not pairable:
        return float("nan")
    if len(cats) == 1:
        return 1.0  # perfect agreement on a single category (alpha is formally undefined)
    idx = {c: i for i, c in enumerate(cats)}
    arr = np.array([[np.nan if v is None else idx[v] for v in row] for row in data], dtype=float)
    return float(krippendorff.alpha(reliability_data=arr, level_of_measurement="nominal"))


def alpha_with_ci(a: dict, b: dict, n_boot: int, seed: int) -> tuple[float, float, float, int]:
    units = sorted(set(a) & set(b))
    if len(units) < 2:
        return float("nan"), float("nan"), float("nan"), len(units)
    est = alpha_nominal([[a[u] for u in units], [b[u] for u in units]])
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        s = [rng.choice(units) for _ in units]
        v = alpha_nominal([[a[u] for u in s], [b[u] for u in s]])
        if not math.isnan(v):
            boots.append(v)
    if not boots:
        return est, float("nan"), float("nan"), len(units)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return est, float(lo), float(hi), len(units)


def percent_agreement(a: dict, b: dict) -> float:
    units = sorted(set(a) & set(b))
    return sum(a[u] == b[u] for u in units) / len(units) if units else float("nan")


def gwet_ac1(a: dict, b: dict, categories: list[str]) -> float:
    """Gwet's AC1 for two coders, nominal; categories = all allowed values (Q)."""
    units = sorted(set(a) & set(b))
    q = len(categories)
    if not units or q < 2:
        return float("nan")
    n = len(units)
    pa = sum(a[u] == b[u] for u in units) / n
    counts = Counter(a[u] for u in units) + Counter(b[u] for u in units)
    pe = sum((counts[c] / (2 * n)) * (1 - counts[c] / (2 * n)) for c in categories) / (q - 1)
    return 1.0 if pe == 1 else (pa - pe) / (1 - pe)


def top_share(values: dict) -> float:
    return max(Counter(values.values()).values()) / len(values) if values else float("nan")


def reliability_level(alpha: float, agreement: float, ac1: float, skewed: bool) -> float:
    """Threshold the variable reaches: 0.80, 0.67 or 0.0 (nan without data)."""
    if skewed:
        if math.isnan(agreement):
            return float("nan")
        for level, min_pa, min_ac1 in SKEW_RULES:
            if agreement >= min_pa and ac1 >= min_ac1:
                return level
        return 0.0
    if math.isnan(alpha):
        return float("nan")
    return 0.80 if alpha >= 0.80 else (0.67 if alpha >= 0.67 else 0.0)


def _pair_alpha(a: dict, b: dict) -> float:
    units = sorted(set(a) & set(b))
    return alpha_nominal([[a[u] for u in units], [b[u] for u in units]]) if units else float("nan")


def variables(allowed: dict) -> list[tuple[str, str, str | None]]:
    """(name, source column, category for binary split or None)."""
    out = [(v, v, None) for v in SINGLE_VARS]
    for col in BINARY_FROM:
        for cat in allowed[col]:
            out.append((f"{col}:{cat}", col, cat))
        for group in COMBINED.get(col, []):
            out.append((f"{col}:{'+'.join(group)}", col, "+".join(group)))
    return out


def _decisive(col: str, cat: str) -> bool:
    """False for categories that are judged only as part of a combined category."""
    return not any(cat in group for group in COMBINED.get(col, []))


def value(row: dict, col: str, cat: str | None):
    raw = row.get(col)
    if raw is None:
        return None
    if cat is None:
        return raw or None
    present = {c for c in raw.split(";") if c}
    return "1" if present & set(cat.split("+")) else "0"


def _by_image(rows: list[dict], col: str, cat: str | None) -> dict:
    return {r["image_id"]: v for r in rows if (v := value(r, col, cat)) is not None}


def load_inputs(cfg: Config) -> dict:
    ai_path = cfg.data_dir / "ai" / "ai_codes.csv"
    hum_path = cfg.data_dir / "human" / "human_codes.csv"
    if not ai_path.exists() or not hum_path.exists():
        raise KkaiError("Brak ai_codes.csv albo human_codes.csv. Najpierw: kkai code i kkai ingest.")
    ai = [r for r in read_csv(ai_path) if r["valid"] == "True"]
    human = read_csv(hum_path)
    vcfg = cfg.raw.get("validation", {})
    primary = vcfg.get("coder_id") or (human[0]["coder_id"] if human else None)

    def first_run(set_name):
        runs = sorted({r["run_id"] for r in ai if r["set"] == set_name})
        return [r for r in ai if r["run_id"] == runs[0]] if runs else []

    return {
        "model": first_run("main"),
        "model_repeat": first_run("validation-repeat"),
        "human": [r for r in human if r["set"] == "validation" and r["coder_id"] == primary and r["round"] == "1"],
        "retest": [r for r in human if r["set"] == "retest" and r["coder_id"] == primary],
        "second": [r for r in human if r["set"] == "second" and r["coder_id"] != primary],
        "key": {r["image_id"]: r for r in read_key(cfg)},
        "primary": primary,
    }


def fisher_rate(err: dict, key: dict, group_fn, alternative: str) -> tuple:
    from scipy.stats import fisher_exact
    g = defaultdict(lambda: [0, 0])  # [errors, n]
    for iid, e in err.items():
        grp = group_fn(key[iid])
        g[grp][0] += e
        g[grp][1] += 1
    a, b = g.get(True, [0, 0]), g.get(False, [0, 0])
    if not a[1] or not b[1]:
        return None, None, None
    p = fisher_exact([[a[0], a[1] - a[0]], [b[0], b[1] - b[0]]], alternative=alternative).pvalue
    return a[0] / a[1], b[0] / b[1], float(p)


FLAG_NAMES = [*FLAG_VARIABLES, "low_confidence_primary", "identity_terms"]


def flag_rates(model: list[dict], key: dict) -> list[dict]:
    """Share of images with each review flag, per condition and per frame (protocol 0.9.2 sec. 6)."""
    groups = defaultdict(list)
    for r in model:
        k = key.get(r["image_id"])
        if k is None:
            continue
        reasons = {x for x in (r.get("review_reasons", "") + ";" + r.get("flags_missing", "")).split(";") if x}
        if r.get("identity_terms"):
            reasons.add("identity_terms")
        groups[("condition", k["condition_code"])].append(reasons)
        groups[("frame", k["frame"])].append(reasons)
    out = []
    for (level, name), sets in sorted(groups.items()):
        row = {"level": level, "group": name, "n": len(sets), "any_flag": sum(bool(x) for x in sets) / len(sets)}
        row.update({f: sum(f in x for x in sets) / len(sets) for f in FLAG_NAMES})
        out.append(row)
    return out


def decide(level: float, stability: float, differential: bool) -> str:
    """Protocol section 6 decision rule; level from reliability_level()."""
    if math.isnan(level):
        return "no_data"
    if level < 0.67 or differential:
        return "manual_all"
    if level >= 0.80 and (math.isnan(stability) or stability >= 0.90):
        return "review_flagged" if not math.isnan(stability) else "review_flagged_pending_stability"
    return "review_all"


def run_validate(cfg: Config) -> Path:
    inp = load_inputs(cfg)
    allowed = allowed_values(load_schema(str(cfg.path(cfg.raw["coder"]["schema"]))))
    n_boot = int(cfg.raw.get("validation", {}).get("bootstrap", 1000))
    seed = cfg.seed
    key = inp["key"]
    rows, confusions = [], {}
    for name, col, cat in variables(allowed):
        m = _by_image(inp["model"], col, cat)
        h = _by_image(inp["human"], col, cat)
        a, lo, hi, n = alpha_with_ci(m, h, n_boot, seed)
        both = sorted(set(m) & set(h))
        pa = percent_agreement(m, h)
        ac1 = gwet_ac1(m, h, allowed[col] if cat is None else ["0", "1"])
        share = top_share({u: h[u] for u in both})
        skewed = not math.isnan(share) and share > SKEW_SHARE
        level = reliability_level(a, pa, ac1, skewed)
        rep = _by_image(inp["model_repeat"], col, cat)
        stab = _pair_alpha(m, rep)
        err = {u: int(m[u] != h[u]) for u in both if u in key}
        w_rate, b_rate, p_w = fisher_rate(err, key, lambda k: k["frame"] in ("W", "WT"), "greater")
        oa_rate, gg_rate, p_g = fisher_rate(err, key, lambda k: k["generator"] == "OA", "two-sided")
        differential = (p_w is not None and p_w < 0.05) or (p_g is not None and p_g < 0.05)
        rt = _pair_alpha(h, _by_image(inp["retest"], col, cat))
        second = _pair_alpha(h, _by_image(inp["second"], col, cat)) if col in SECOND_CODER_COLUMNS else float("nan")
        rows.append({
            "variable": name, "n": n, "alpha_model_human": a, "ci_low": lo, "ci_high": hi,
            "agreement": pa, "ac1": ac1, "top_category_share": share, "skewed": skewed, "level": level,
            "model_stability": stab, "error_rate_W_WT": w_rate, "error_rate_B_T": b_rate, "p_W_vs_B": p_w,
            "error_rate_OA": oa_rate, "error_rate_GG": gg_rate, "p_OA_vs_GG": p_g,
            "differential_error": differential, "test_retest_alpha": rt, "second_coder_alpha": second,
            "decision": decide(level, stab, differential) if cat is None else "",
        })
        if cat is None:
            confusions[name] = Counter((h[u], m[u]) for u in both)

    # Multi-select variables get one decision from the weakest category (lowest level, then lowest alpha).
    for col in BINARY_FROM:
        sub = [r for r in rows if r["variable"].startswith(col + ":") and not math.isnan(r["level"])
               and _decisive(col, r["variable"].split(":", 1)[1])]
        if sub:
            worst = min(sub, key=lambda r: (r["level"], r["alpha_model_human"]))
            rows.append({**{k: "" for k in rows[0]}, "variable": col, "n": worst["n"],
                         "alpha_model_human": worst["alpha_model_human"], "agreement": worst["agreement"],
                         "ac1": worst["ac1"], "skewed": worst["skewed"], "level": worst["level"],
                         "differential_error": any(r["differential_error"] for r in sub),
                         "decision": decide(worst["level"],
                                            min((r["model_stability"] for r in sub), default=float("nan")),
                                            any(r["differential_error"] for r in sub)),
                         "ci_low": worst["ci_low"], "ci_high": worst["ci_high"],
                         "model_stability": min((r["model_stability"] for r in sub), default=float("nan"))})

    out_dir = cfg.dir("results") / "validation" / utc_now().replace(":", "").replace(".", "_")
    out_dir.mkdir(parents=True)
    fields = list(rows[0])
    with open(out_dir / "validation_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.3f}" if isinstance(v, float) and not math.isnan(v) else ("" if isinstance(v, float) else v))
                        for k, v in r.items()})
    for name, cm in confusions.items():
        cats = sorted({c for pair in cm for c in pair})
        with open(out_dir / f"confusion_{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["human \\ model", *cats])
            for hc in cats:
                w.writerow([hc, *[cm.get((hc, mc), 0) for mc in cats]])
    proposal = [{"variable": r["variable"], "decision": r["decision"]} for r in rows
                if r["decision"] and ":" not in r["variable"]]
    for v in ("people_count", "contemporary_cue_types", "historical_cue_types", "mode_secondary", "landmarks"):
        # Not validated (02_kodeks.md): checked on flagged images only.
        proposal.append({"variable": v, "decision": "review_flagged"})
    with open(out_dir / "decisions_proposed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variable", "decision"], lineterminator="\n")
        w.writeheader()
        w.writerows(proposal)
    flags = flag_rates(inp["model"], key)
    if flags:
        with open(out_dir / "flag_rates.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(flags[0]), lineterminator="\n")
            w.writeheader()
            w.writerows({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()} for r in flags)
    write_new_text(out_dir / "validation_report.html", _report(rows, confusions, inp, n_boot, flags))
    print(f"Raport walidacji: {out_dir / 'validation_report.html'}")
    print(f"Propozycja decyzji: {out_dir / 'decisions_proposed.csv'} (po bramce 3 zapisz swoje decyzje jako data/human/decisions.csv)")
    for r in rows:
        if r["decision"]:
            a = r["alpha_model_human"]
            extra = f", zgodność {r['agreement']:.0%}, AC1 = {r['ac1']:.2f} (1 kategoria > 90%)" if r["skewed"] else ""
            print(f"  {r['variable']:<22} α = {a:.2f}{extra}  →  {r['decision']}" if isinstance(a, float) and not math.isnan(a)
                  else f"  {r['variable']:<22} brak danych")
    return out_dir


def _fmt(v):
    if isinstance(v, float):
        return "" if math.isnan(v) else f"{v:.3f}"
    return html.escape(str(v))


def _report(rows, confusions, inp, n_boot, flags=()) -> str:
    head = "".join(f"<th>{html.escape(k)}</th>" for k in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{_fmt(v)}</td>" for v in r.values()) + "</tr>" for r in rows)
    cms = []
    for name, cm in confusions.items():
        cats = sorted({c for pair in cm for c in pair})
        t = "<tr><th>human \\ model</th>" + "".join(f"<th>{c}</th>" for c in cats) + "</tr>"
        t += "".join("<tr><th>" + hc + "</th>" + "".join(f"<td>{cm.get((hc, mc), 0)}</td>" for mc in cats) + "</tr>"
                     for hc in cats)
        cms.append(f"<h3>{name}</h3><table>{t}</table>")
    ftab = ""
    if flags:
        ftab = ("<h2>Odsetek flag (kody modelu, etap main)</h2><table><tr>"
                + "".join(f"<th>{html.escape(k)}</th>" for k in flags[0]) + "</tr>"
                + "".join("<tr>" + "".join(f"<td>{_fmt(v)}</td>" for v in r.values()) + "</tr>" for r in flags)
                + "</table>")
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>Walidacja kodowania</title>
<style>body{{font-family:sans-serif;margin:16px}}table{{border-collapse:collapse;margin-bottom:16px}}
td,th{{border:1px solid #ccc;padding:3px 6px;font-size:13px}}</style></head><body>
<h1>Walidacja kodowania</h1>
<p>Koder: {html.escape(str(inp['primary']))}. Obrazów z kodami modelu: {len(inp['model'])}; z Twoimi kodami: {len(inp['human'])};
powtórne kodowanie modelu: {len(inp['model_repeat'])}; test–retest: {len(inp['retest'])}; drugi koder: {len(inp['second'])}.
Przedziały: bootstrap po obrazach, {n_boot} powtórzeń.</p>
<p>Reguła (protokół, sekcja 6): α ≥ .80, stabilność ≥ .90 i brak błędu różnicowego → <b>review_flagged</b>;
α .67–.80 → <b>review_all</b>; α &lt; .67 albo błąd różnicowy → <b>manual_all</b>.
Gdy 1 kategoria obejmuje ponad 90% Twoich kodów (kolumna skewed), zamiast α decyduje zgodność i AC1 Gweta:
próg .80 przy zgodności ≥ 95% i AC1 ≥ .80, próg .67 przy zgodności ≥ 90% i AC1 ≥ .67 (kolumna level).
Pismo hebrajskie ocenia połączona kategoria scripts:hebrew+hebrew_like; hebrew i hebrew_like osobno są tylko informacyjne. Błąd różnicowy: jednostronny test Fishera
(W/WT częściej niż B/T) albo dwustronny (OA vs GG), p &lt; .05. α ≥ .80 przy stabilności &lt; .90 protokół nie rozstrzyga; program daje review_all.</p>
<table><tr>{head}</tr>{body}</table>
{ftab}
<h2>Macierze pomyłek</h2>{''.join(cms)}
</body></html>
"""
