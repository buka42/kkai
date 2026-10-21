# kkai

Code for the study *Multiculturalism in the past tense? Heritage, religion and generative images of Kraków and Kazimierz*.
It generates images with 2 image generators through their APIs, blinds them, codes them with an AI model and with a human coder, and (later) runs the validation and the analysis.

The study protocol, codebook and coder instruction are the reference documents; this program implements them. Results describe these prompts, these model versions and this period only.

## Principles

- **Additive data.** Logs and raw API responses are append-only (JSONL). No file is overwritten; each attempt gets its own file names. Derived tables (CSV) can be rebuilt from the logs.
- **Blinding by design.** `data/blinded/` holds PNG files named `img_xxxxxx.png` with pixel data only (no EXIF, text chunks or ICC profile), identical timestamps and random write order. The condition key is in `data/key/key.csv`.
- **No selection.** Refusals and blocks are results (`refused`), never regenerated. Only technical errors (timeout, 5xx, 429) are retried, up to 3 times with 5/20/60 s pauses; a corrupt file is retried once. Every attempt is logged.
- **Keys** come only from environment variables (`OPENAI_API_KEY`, `GEMINI_API_KEY`), loaded from `.env`, which is outside git. Keys are never logged.
- **`--dry-run`** on every command: a stand-in generator draws grey images, a stand-in coder returns random schema-valid codes, and everything is written to `data_dryrun/`.
- Every command that spends money shows an estimate and asks for confirmation (`--yes` skips it); `max_cost_usd` in `config.yaml` stops a run whose estimate is higher.
- `script_version` (git commit hash, `-dirty` if there are uncommitted changes) is stored in every record.

## Install

Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env             # then put your API keys in .env
```

## Commands

| Command | What it does |
|---|---|
| `kkai plan --stage test\|pilot\|main` | Builds the shuffled request plan (`data/plan/<stage>.csv`); same seed, same plan |
| `kkai generate --stage …` | Runs the plan, resumes after interruption, logs each attempt (`data/logs/generation_log.jsonl`, `data/raw/`) |
| `kkai prepare --stage …` | Blinds the images (`data/blinded/<stage>/`) and writes the key |
| `kkai sample` | Draws the validation set (5 per condition) and the retest and second-coder subsets (`data/human/*_ids.csv`) |
| `kkai sheet --set pilot\|validation\|retest\|second` | Coding sheet (XLSX with drop-down lists) and an HTML page with the images, showing only `image_id` |
| `kkai ingest --sheet FILE --set … --coder-id PB [--round 2]` | Checks a filled sheet and appends it to `data/human/human_codes.csv` |
| `kkai code --set test\|pilot\|main\|validation-repeat` | Codes blinded images with the AI model (Batch API or one call per image); run it again to collect batch results |

Useful options: `--dry-run`, `--yes`, `--limit N` (e.g. 10 images as a first test), `--retry-errors`, `--new-run`.

Still to be written: `validate`, `review`, `analyze`, `walls`, `figure`, `export`.

## Full dry run

```bash
kkai plan --stage pilot --dry-run
kkai generate --stage pilot --dry-run
kkai prepare --stage pilot --dry-run
kkai code --set pilot --dry-run
kkai sheet --set pilot --dry-run
```

## Data layout

```
data/
  plan/      request plans
  raw/       images and raw responses from the APIs, named by request_uid; never shown during coding
  logs/      generation_log.jsonl, coding_log.jsonl
  blinded/   images for coding: img_xxxxxx.png, metadata removed
  key/       key.csv: image_id -> condition (not opened before gate 3)
  ai/        ai_raw.jsonl, ai_codes.csv, batch files
  human/     sheets and human codes
  results/   reports, tables, figures
```

`data/` is not in git. The export package with codes and logs (without keys) will be produced by `kkai export`.

## API notes (checked 21.10.2026)

- OpenAI Images API, `gpt-image-2.5-flare-2026-09-08`: `size`, `quality`, `moderation`, `n` are passed as set in `config.yaml`; the response is base64 (`data[].b64_json`). The base64 string is replaced in the stored JSON by a reference (length and SHA-256) to the image file, which holds the decoded bytes unchanged.
- Gemini API, `gemini-nano-banana-2.1`, through `google-genai` `models.generate_content` with `ImageConfig(image_size="1K", aspect_ratio="1:1")`. Thinking is on by default and cannot be switched off. `prompt_feedback.block_reason` and safety `finish_reason` values are logged as `refused`; other image-less answers as `no_image`.
- Coder: `gpt-6.1-sol` through the Responses API (`/v1/responses`), strict JSON schema output, 1 image per request, Batch API with a 24 h window.

## Licence

MIT, see `LICENSE`.
