"""Building the shuffled request plan for a stage (test, pilot, main)."""

from __future__ import annotations

import random
from pathlib import Path

from .config import Config, STAGES
from .util import KkaiError, read_csv, write_csv_once

PLAN_FIELDS = ["run_order", "request_uid", "stage", "condition_code", "frame", "scale",
               "language", "generator", "rep", "prompt_exact", "shuffle_seed"]
FRAMES = ("B", "W", "T", "WT")
SCALES = ("K", "Z")
LANGUAGES = ("PL", "EN")


def load_prompts(path: Path) -> dict[tuple[str, str, str], str]:
    rows = read_csv(path)
    prompts = {}
    for r in rows:
        key = (r["frame"].strip(), r["scale"].strip(), r["language"].strip().upper())
        if key in prompts:
            raise KkaiError(f"Powtórzony prompt w {path}: {key}")
        prompts[key] = r["prompt_exact"]
    expected = {(f, s, l) for f in FRAMES for s in SCALES for l in LANGUAGES}
    if set(prompts) != expected:
        missing = sorted(expected - set(prompts))
        extra = sorted(set(prompts) - expected)
        raise KkaiError(f"prompts.csv nie zgadza się z macierzą 4×2×2. Brakuje: {missing}; nadmiarowe: {extra}")
    return prompts


def stage_cells(cfg: Config, stage: str) -> list[tuple[str, str, str]]:
    """(frame, scale, language) cells that a stage covers."""
    if stage == "test":
        cells = []
        for code in cfg.raw.get("test_conditions", []):
            parts = code.split("-")
            if len(parts) != 3:
                raise KkaiError(f"test_conditions: zły kod {code!r}, oczekuję np. W-Z-EN")
            cells.append((parts[0], parts[1], parts[2].upper()))
        if not cells:
            raise KkaiError("Brak test_conditions w config.yaml")
        return cells
    languages = [l.upper() for l in cfg.raw.get("pilot_languages", LANGUAGES)] if stage == "pilot" else list(LANGUAGES)
    return [(f, s, l) for f in FRAMES for s in SCALES for l in languages]


def build_plan(cfg: Config, stage: str) -> list[dict]:
    if stage not in STAGES:
        raise KkaiError(f"Nieznany etap {stage!r}; dozwolone: {', '.join(STAGES)}")
    prompts = load_prompts(cfg.path(cfg.raw["prompts"]))
    reps = int(cfg.raw["reps"][stage])
    gens = list(cfg.generators)
    # Seeding with a string is deterministic across runs and platforms.
    rng = random.Random(f"{cfg.seed}:{stage}")

    per_gen = {}
    for g in gens:
        items = [(f, s, l, rep) for (f, s, l) in stage_cells(cfg, stage) for rep in range(1, reps + 1)]
        rng.shuffle(items)
        per_gen[g] = items
    # Alternate generators: OA, GG, OA, GG, ... (the starting generator is drawn too).
    order = gens[:]
    rng.shuffle(order)
    rows = []
    for i in range(len(per_gen[gens[0]])):
        for g in order:
            f, s, l, rep = per_gen[g][i]
            run_order = len(rows) + 1
            rows.append({
                "run_order": run_order,
                "request_uid": f"{stage}_{run_order:04d}",
                "stage": stage,
                "condition_code": f"{f}-{s}-{l}-{g}",
                "frame": f, "scale": s, "language": l, "generator": g, "rep": rep,
                "prompt_exact": prompts[(f, s, l)],
                "shuffle_seed": cfg.seed,
            })
    return rows


def plan_path(cfg: Config, stage: str) -> Path:
    return cfg.dir("plan") / f"{stage}.csv"


def write_plan(cfg: Config, stage: str) -> tuple[Path, list[dict], bool]:
    rows = build_plan(cfg, stage)
    path = plan_path(cfg, stage)
    created = write_csv_once(path, rows, PLAN_FIELDS)
    return path, rows, created


def read_plan(cfg: Config, stage: str) -> list[dict]:
    path = plan_path(cfg, stage)
    if not path.exists():
        raise KkaiError(f"Brak planu {path}. Najpierw uruchom: kkai plan --stage {stage}")
    rows = read_csv(path)
    expected = build_plan(cfg, stage)
    if [r["request_uid"] for r in rows] != [r["request_uid"] for r in expected] or \
            [r["condition_code"] for r in rows] != [r["condition_code"] for r in expected]:
        raise KkaiError(f"Plan {path} nie zgadza się z config.yaml i prompts.csv (inne ziarno, prompty albo powtórzenia?).")
    return rows
