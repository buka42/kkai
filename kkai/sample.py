"""Drawing the validation set (k per condition) and the retest / second-coder subsets."""

from __future__ import annotations

import random
from collections import defaultdict

from .config import Config
from .prepare import read_key
from .util import KkaiError, write_csv_once


def draw_samples(cfg: Config, stage: str = "main") -> dict[str, list[str]]:
    v = cfg.raw.get("validation", {})
    k = int(v.get("per_condition", 5))
    rng = random.Random(f"{cfg.seed}:validation")
    by_cond = defaultdict(list)
    for r in read_key(cfg):
        if r["stage"] == stage:
            by_cond[r["condition_code"]].append(r["image_id"])
    if not by_cond:
        raise KkaiError(f"Brak obrazów etapu {stage} w kluczu. Najpierw: kkai prepare --stage {stage}")
    validation, short = [], []
    for cond in sorted(by_cond):
        ids = sorted(by_cond[cond])
        if len(ids) < k:
            short.append(f"{cond} ({len(ids)})")
        validation += rng.sample(ids, min(k, len(ids)))
    rng.shuffle(validation)
    if short:
        print("Uwaga: za mało obrazów w warunkach: " + ", ".join(short))
    retest = rng.sample(validation, min(int(v.get("retest_n", 50)), len(validation)))
    second = rng.sample(validation, min(int(v.get("second_coder_n", 50)), len(validation)))
    return {"validation": validation, "retest": retest, "second": second}


def run_sample(cfg: Config, stage: str = "main") -> dict:
    sets = draw_samples(cfg, stage)
    human = cfg.dir("human")
    for name, ids in sets.items():
        path = human / f"{name}_ids.csv"
        created = write_csv_once(path, [{"order": i + 1, "image_id": x} for i, x in enumerate(ids)],
                                 ["order", "image_id"])
        print(f"{'Zapisano' if created else 'Bez zmian'}: {path} ({len(ids)} obrazów)")
    return sets
