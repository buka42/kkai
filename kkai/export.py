"""Replication package: prompts, materials, codes and logs (no API keys, no images by default)."""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import Config
from .util import sha256_file, utc_now

FILES = [
    ("materials", None),
    ("data/plan", "plan"),
    ("data/logs/generation_log.jsonl", "logs/generation_log.jsonl"),
    ("data/logs/coding_log.jsonl", "logs/coding_log.jsonl"),
    ("data/key/key.csv", "codes/key.csv"),
    ("data/ai/ai_codes.csv", "codes/ai_codes.csv"),
    ("data/ai/ai_raw.jsonl", "codes/ai_raw.jsonl"),
    ("data/human/human_codes.csv", "codes/human_codes.csv"),
    ("data/human/review_corrections.csv", "codes/review_corrections.csv"),
    ("data/human/final_codes.csv", "codes/final_codes.csv"),
    ("data/human/decisions.csv", "codes/decisions.csv"),
    ("config.yaml", "config.yaml"),
]


def run_export(cfg: Config, with_images: bool = False) -> Path:
    out = cfg.root / ("export_dryrun" if cfg.dry_run else "export") / utc_now()[:10]
    if out.exists():
        out = out.with_name(out.name + "_" + utc_now()[11:19].replace(":", ""))
    out.mkdir(parents=True)
    data = cfg.data_dir
    for src, dst in FILES:
        p = (cfg.root / src) if not src.startswith("data/") else data / src[len("data/"):]
        if not p.exists():
            continue
        target = out / (dst or src)
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, target)
    for res in ("results/validation", "results/analysis", "results/figures"):
        p = data / res
        if p.exists():
            shutil.copytree(p, out / res)
    if with_images:
        shutil.copytree(data / "blinded", out / "images_blinded")
    manifest = ["path,sha256"] + [f"{f.relative_to(out).as_posix()},{sha256_file(f)}"
                                  for f in sorted(out.rglob("*")) if f.is_file()]
    (out / "MANIFEST.csv").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    (out / "README.md").write_text(README, encoding="utf-8")
    print(f"Pakiet: {out}")
    return out


README = """# Replication package

Study: Multiculturalism in the past tense? Heritage, religion and generative images of Kraków and Kazimierz.

- `materials/`: exact prompts (`prompts.csv`), coder instruction and output schema sent to the coding model.
- `plan/`: shuffled request plans (seed in each row).
- `logs/generation_log.jsonl`: every generation attempt (request, parameters, status, refusals, usage, file hash).
- `logs/coding_log.jsonl`: coding runs and batch jobs.
- `codes/key.csv`: blinded image_id -> condition.
- `codes/ai_raw.jsonl`: raw responses of the coding model; `ai_codes.csv` is derived from it.
- `codes/human_codes.csv`, `review_corrections.csv`, `final_codes.csv`, `decisions.csv`: human codes, review and final codes with source.
- `results/`: validation and analysis reports and tables.
- `MANIFEST.csv`: SHA-256 of every file.

Code: the kkai repository (MIT licence). API keys are never stored in any file.
"""
