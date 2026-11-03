"""Replication package: prompts, materials, codes and logs (no API keys, no images by default)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .config import Config
from .util import KkaiError, sha256_file, utc_now

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


def run_export(cfg: Config, with_images: bool = False, osf: bool = False, add: list | None = None) -> Path:
    out = cfg.root / ("export_dryrun" if cfg.dry_run else "export") / (utc_now()[:10] + ("_osf" if osf else ""))
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
    for extra in add or []:
        extra = Path(extra)
        if not extra.is_file():
            raise KkaiError(f"Brak pliku do dołączenia: {extra}")
        (out / "docs").mkdir(exist_ok=True)
        shutil.copy2(extra, out / "docs" / extra.name)
    if osf:
        aliases = _coder_aliases(cfg)
        counts = anonymise_tree(out, aliases)
        for f, n in sorted(counts.items()):
            print(f"  zanonimizowano {n}x: {f}")
        if (data / "blinded").exists():
            shutil.make_archive(str(out / "images_blinded"), "zip", data / "blinded")
        (out / "DATA_DICTIONARY.md").write_text(DATA_DICTIONARY, encoding="utf-8")
        (out / "LICENSE-DATA.txt").write_text(LICENSE_DATA, encoding="utf-8")
    elif with_images:
        shutil.copytree(data / "blinded", out / "images_blinded")
    manifest = ["path,sha256"] + [f"{f.relative_to(out).as_posix()},{sha256_file(f)}"
                                  for f in sorted(out.rglob("*")) if f.is_file()]
    (out / "MANIFEST.csv").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    (out / "README.md").write_text(README_OSF if osf else README, encoding="utf-8")
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


TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".txt", ".yaml", ".yml", ".html", ".tsv"}
# Verbatim machine records: never edited, so they still match the API responses and their hashes.
# Coder ids do not occur in them; any two-letter match there is a coincidence.
VERBATIM = {"codes/ai_raw.jsonl", "logs/generation_log.jsonl", "logs/coding_log.jsonl"}


def _coder_aliases(cfg: Config) -> dict:
    aliases = ((cfg.raw.get("export") or {}).get("coder_aliases")) or {}
    if not aliases:
        raise KkaiError("--osf wymaga export.coder_aliases w config.yaml (np. {PB: A, DW: C1, DK: X1, WD: X2})")
    return {str(k): str(v) for k, v in aliases.items()}


def anonymise_text(text: str, aliases: dict) -> tuple[str, int]:
    """Replace coder ids as whole tokens (letters/digits around them block a match)."""
    if not aliases:
        return text, 0
    pat = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, sorted(aliases, key=len, reverse=True)))
                     + r")(?![A-Za-z0-9])")
    return pat.subn(lambda m: aliases[m.group(1)], text)


def anonymise_tree(root: Path, aliases: dict) -> dict:
    """Anonymise coder ids in text files and file names under root; returns replacements per file."""
    counts = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.suffix.lower() in TEXT_SUFFIXES and f.relative_to(root).as_posix() not in VERBATIM:
            text = f.read_text(encoding="utf-8")
            new, n = anonymise_text(text, aliases)
            if n:
                f.write_text(new, encoding="utf-8")
                counts[f.relative_to(root).as_posix()] = n
    for f in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        new_name, n = anonymise_text(f.name, aliases)
        if n:
            f.rename(f.with_name(new_name))
            counts[f.with_name(new_name).relative_to(root).as_posix() + " (nazwa)"] = n
    return counts


README_OSF = """# Data and materials: multicultural Kraków and Kazimierz in two image generators

This package contains everything needed to check the article's results without contacting the author:
the exact prompts, all generated images, every API request and response record, the codebook, all model,
human and final codes, the validation data, the decision log and the analysis output.

## Contents

| Path | What it is |
|---|---|
| `materials/` | Prompts (`prompts_v2.csv` used in the main study; `prompts.csv` in the first pilot), codebook, protocol and analysis plan v1.0, coder instruction and JSON output schema, `SHA256SUMS_v1.0.txt` (hashes of the frozen files, git tag `v1.0-freeze`, 24 October 2026). |
| `plan/` | Shuffled request plans for each stage, with the seed. |
| `logs/generation_log.jsonl` | One record per generation attempt: prompt, parameters, timestamp, status, refusal or error, model name returned by the API, SHA-256 of the saved image. Base64 image data is replaced by a reference to the file. |
| `logs/coding_log.jsonl` | Coding runs and Batch jobs of the coding model. |
| `images_blinded.zip` | All generated images as PNG without metadata, named by random `image_id`. |
| `codes/key.csv` | `image_id` -> stage, condition, frame, scale, language, generator and hashes of the raw and blinded file. |
| `codes/ai_raw.jsonl`, `codes/ai_codes.csv` | Raw responses of the coding model and the table derived from them. |
| `codes/human_codes.csv` | All human codes: validation set, test-retest and second coders (see Coders). |
| `codes/decisions.csv` | Decision per variable after validation (model codes kept, reviewed or replaced by manual coding). |
| `codes/review_corrections.csv`, `codes/final_codes.csv` | Review of model codes and the final code of every variable with its source. |
| `results/` | Validation report (agreement, Krippendorff's alpha, Gwet's AC1), analysis report (confirmatory tests, sensitivity and exploratory tables), figures. |
| `docs/` | Decision log and other documents added at export. |
| `config.yaml` | Settings used for every step. API keys are never stored in any file. |
| `DATA_DICTIONARY.md` | Variables and category values. |
| `MANIFEST.csv` | SHA-256 of every file in this package. |

## Coders

Coder identifiers are anonymised: `A` is the author; `C1` is the independent second coder; `X1` and `X2` are
two earlier second-coding attempts that were excluded before analysis (X1: entries marked as AI output;
X2: codes identical to X1 in 50 of 50 images). Their codes are kept for transparency and are left out of all
agreement statistics (`validation.excluded_coders` in `config.yaml`). The decision log documents the exclusion.

## Reproducing the results

Every number in the article can be recomputed from `codes/key.csv` and `codes/final_codes.csv`
(confirmatory tests: one-sided Fisher's exact tests, Holm adjustment over 8 tests; see
`materials/analysis_plan_v1.0.md`). The study software is kkai (MIT licence; the archived version is cited in
the article); `kkai analyze` produces the reports in `results/` from the original data folder. Image generation
and model coding need API keys and are not required to check the results.

## Licence

Data, images and documents: CC BY 4.0 (`LICENSE-DATA.txt`). Images were generated with OpenAI GPT Image 2.5 Flare
and Google Gemini Nano Banana 2.1 in October 2026; neither provider's terms claim ownership of outputs.
"""

DATA_DICTIONARY = """# Data dictionary

## codes/key.csv

| Column | Meaning |
|---|---|
| `image_id` | Random identifier used for blind coding and as the file name in `images_blinded.zip`. |
| `request_uid` | Link to the record in `logs/generation_log.jsonl`. |
| `stage` | `test`, `pilot`, `pilot2` or `main` (the article analyses `main`). |
| `condition_code` | FRAME-SCALE-LANGUAGE-GENERATOR, e.g. `W-K-PL-OA`. |
| `frame` | `B` baseline, `W` multicultural, `T` today, `WT` multicultural today. |
| `scale` | `K` Kraków, `Z` Kazimierz. |
| `language` | `PL` or `EN`. |
| `generator` | `OA` OpenAI GPT Image 2.5 Flare, `GG` Google Gemini Nano Banana 2.1. |
| `raw_file`, `raw_sha256`, `blinded_sha256` | Original file name and hashes of the original and blinded image. |

## Coded variables (ai_codes.csv, human_codes.csv, final_codes.csv)

Multi-value fields are separated by `;`. In `final_codes.csv` every variable has a `<variable>__source` column:
`human_validation`, `model`, `model_confirmed`, `review` or `manual`.

| Variable | Values | Used in |
|---|---|---|
| `temporal_frame` | contemporary, historical, staged_historical, indeterminate | H1, H2, H4 |
| `contemporary_cue_types` | mobile_device, modern_motor_vehicle, modern_tram, micromobility, modern_clothing, screen_or_led, modern_signage_or_branding, other_contemporary_object | frame evidence |
| `historical_cue_types` | period_clothing_all_figures, period_motor_vehicle, aged_photographic_look, other_period_object | frame evidence |
| `mode_dominant` | everyday, heritage, spectacle, consumption, indeterminate | H3 |
| `mode_secondary` | everyday, heritage, spectacle, consumption | descriptive |
| `roles` | everyday_activity, sightseeing, performer_or_costumed, religious_practice, indeterminate | descriptive |
| `people_count` | none, 1_5, 6_20, crowd | descriptive |
| `religion_form` | none, building, symbol_or_object, practice (highest visible level) | descriptive |
| `religion_traditions` | jewish, christian, christian_orthodox, muslim, other, indeterminate (inferred from objects and buildings only) | descriptive |
| `scripts` | latin, hebrew, hebrew_like, cyrillic, other | descriptive |
| `place` | landmark, generic_historic_townscape, generic_modern_townscape, inconsistent_with_krakow, indeterminate | descriptive |
| `landmarks` | wawel, cloth_hall, st_marys, town_hall_tower, barbican_florian_gate, sts_peter_paul, old_synagogue, remuh, tempel, plac_nowy, szeroka_street, corpus_christi, skalka, bernatek_footbridge, other_krakow_landmark | descriptive |
| `medium` | photo_colour, photo_aged, illustration, indeterminate | descriptive, sensitivity |

Full definitions and decision rules: `materials/codebook_v1.0.md` and `materials/coder_instruction_v1.0.md`.

## codes/human_codes.csv (additional columns)

`coder_id` (anonymised, see README), `set` (validation, retest, second), `round`, `notes`, `coded_at`,
`source_file` and `source_sha256` (the filled coding sheet the row was read from).
"""

LICENSE_DATA = """Data, images and documents in this package are licensed under the Creative Commons Attribution 4.0
International licence (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/
Cite the article and this dataset when you reuse them.
The kkai software is licensed separately under the MIT licence (see its repository).
"""
