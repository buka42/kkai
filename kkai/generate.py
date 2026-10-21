"""Executing a request plan: one API call per request, every attempt logged.

Resumable: a request with a final record in generation_log.jsonl is skipped.
Nothing is overwritten: each attempt gets its own file names.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

from . import providers as P
from .config import Config, api_key, api_params, load_env
from .plan import read_plan
from .util import KkaiError, append_jsonl, confirm, read_jsonl, script_version, sha256_bytes, utc_now, write_new, write_new_text

FINAL_STATUSES = {P.OK, P.REFUSED, P.NO_IMAGE}
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp"}


def log_path(cfg: Config) -> Path:
    return cfg.dir("logs") / "generation_log.jsonl"


def read_log(cfg: Config, stage: str | None = None) -> list[dict]:
    return [r for r in read_jsonl(log_path(cfg)) if stage is None or r.get("stage") == stage]


def request_state(records: list[dict]) -> dict[str, dict]:
    """Per request_uid: last attempt number and the final record, if any."""
    state: dict[str, dict] = {}
    for r in records:
        s = state.setdefault(r["request_uid"], {"attempts": 0, "final": None})
        s["attempts"] = max(s["attempts"], int(r["attempt"]))
        if r.get("final"):
            s["final"] = r
    return state


def _image_ok(data: bytes) -> bool:
    from PIL import Image
    import io
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        return True
    except Exception:
        return False


def _next_attempt(raw_dir: Path, uid: str, logged: int) -> int:
    """Attempt number above both the log and any file left by an interrupted run."""
    on_disk = [int(p.name.split("_a")[-1].split(".")[0]) for p in raw_dir.glob(f"{uid}_a*.*")
               if p.name.split("_a")[-1].split(".")[0].isdigit()]
    return max([logged, *on_disk]) + 1


def estimate_cost(cfg: Config, todo: list[dict]) -> tuple[float | None, dict]:
    per_gen = Counter(r["generator"] for r in todo)
    total, unknown = 0.0, []
    for g, n in per_gen.items():
        price = cfg.generators[g].get("cost_per_image_usd")
        if price is None:
            unknown.append(g)
        else:
            total += float(price) * n
    return (None if unknown else total), {"per_generator": dict(per_gen), "no_price": unknown}


def make_providers(cfg: Config) -> dict:
    timeout = float(cfg.raw.get("timeout_seconds", 180))
    out = {}
    for code, g in cfg.generators.items():
        if cfg.dry_run:
            out[code] = P.make_provider("fake", g["model"], api_params(g), None, timeout)
        else:
            out[code] = P.make_provider(g["provider"], g["model"], api_params(g), api_key(g["provider"]), timeout)
    return out


def run_generate(cfg: Config, stage: str, assume_yes: bool = False, limit: int | None = None,
                 retry_errors: bool = False, providers: dict | None = None, sleep=time.sleep) -> dict:
    load_env(cfg.root)
    plan = read_plan(cfg, stage)
    state = request_state(read_log(cfg, stage))

    def pending(row):
        f = state.get(row["request_uid"], {}).get("final")
        if f is None:
            return True
        return retry_errors and f["status"] not in FINAL_STATUSES

    todo = [r for r in plan if pending(r)]
    if limit is not None:
        todo = todo[:limit]
    done = len(plan) - len([r for r in plan if pending(r)])
    print(f"Etap {stage}: w planie {len(plan)} żądań, zakończonych {done}, do wykonania teraz {len(todo)}.")
    if not todo:
        return {"executed": 0}

    cost, detail = estimate_cost(cfg, todo)
    max_cost = cfg.raw.get("max_cost_usd")
    if not cfg.dry_run:
        if cost is None:
            print(f"Szacowany koszt: nieznany (brak cost_per_image_usd dla: {', '.join(detail['no_price'])}).")
        else:
            print(f"Szacowany koszt: {cost:.2f} USD ({detail['per_generator']}).")
            if max_cost is not None and cost > float(max_cost):
                raise KkaiError(f"Szacunek {cost:.2f} USD przekracza max_cost_usd = {max_cost}. Zatrzymuję.")
        if not confirm("Uruchomić generowanie?", assume_yes):
            print("Przerwano bez wywołań API.")
            return {"executed": 0}

    provs = providers or make_providers(cfg)
    retries = cfg.raw.get("retries", {})
    max_tech = int(retries.get("technical", 3))
    max_corrupt = int(retries.get("corrupt_file", 1))
    backoff = list(retries.get("backoff_seconds", [5, 20, 60])) or [5]
    raw_dir = cfg.dir("raw")
    version = script_version()
    seen_models = {g: {r["model_returned"] for r in read_log(cfg, stage)
                       if r.get("generator") == g and r.get("model_returned")} for g in cfg.generators}
    last_call: dict[str, float] = {}
    counts = Counter()

    for row in todo:
        uid, gen = row["request_uid"], row["generator"]
        gcfg = cfg.generators[gen]
        tech_fail = corrupt_fail = 0
        while True:
            attempt = _next_attempt(raw_dir, uid, state.get(uid, {}).get("attempts", 0))
            wait = float(gcfg.get("min_interval_seconds", 0)) - (time.monotonic() - last_call.get(gen, -1e9))
            if wait > 0 and not cfg.dry_run:
                sleep(wait)
            ts_start = utc_now()
            last_call[gen] = time.monotonic()
            try:
                res = provs[gen].generate(row["prompt_exact"], label=uid)
            except P.FatalProviderError as e:
                append_jsonl(log_path(cfg), _record(cfg, row, gcfg, attempt, ts_start, utc_now(),
                                                    P.GenResult(status="fatal", error_message=str(e)),
                                                    None, None, version, final=False))
                raise KkaiError(str(e)) from e
            ts_end = utc_now()

            raw_file = img_file = sha = None
            if res.image is not None and not _image_ok(res.image):
                res.status, res.error_code = P.CORRUPT, res.error_code or "undecodable_image"
            if res.image is not None:
                ext = EXT.get((res.image_mime or "").lower(), "bin")
                img_path = raw_dir / f"{uid}_a{attempt}.{ext}"
                write_new(img_path, res.image)
                img_file, sha = img_path.name, sha256_bytes(res.image)
            if res.raw is not None:
                raw_path = raw_dir / f"{uid}_a{attempt}.json"
                write_new_text(raw_path, json.dumps(res.raw, ensure_ascii=False, indent=1, default=str))
                raw_file = raw_path.name

            if res.status == P.TECHNICAL:
                tech_fail += 1
            if res.status == P.CORRUPT:
                corrupt_fail += 1
            retry = (res.status == P.TECHNICAL and tech_fail <= max_tech) or \
                    (res.status == P.CORRUPT and corrupt_fail <= max_corrupt)
            final = not retry
            if res.status == P.OK and res.model_returned:
                seen = seen_models[gen]
                if seen and res.model_returned not in seen:
                    append_jsonl(log_path(cfg), _record(cfg, row, gcfg, attempt, ts_start, ts_end, res,
                                                        img_file or raw_file, sha, version, final=False))
                    raise KkaiError(f"Generator {gen} zwrócił inną wersję modelu ({res.model_returned}) niż wcześniej "
                                    f"({', '.join(sorted(seen))}). Protokół: wersji nie mieszamy. Zatrzymuję.")
                seen.add(res.model_returned)
            append_jsonl(log_path(cfg), _record(cfg, row, gcfg, attempt, ts_start, ts_end, res,
                                                img_file, sha, version, final=final, raw_json=raw_file))
            state.setdefault(uid, {"attempts": 0, "final": None})["attempts"] = attempt
            if final:
                counts[res.status] += 1
                print(f"  {uid}: {res.status}" + (f" ({res.error_code})" if res.error_code else ""))
                break
            delay = backoff[min((tech_fail or corrupt_fail) - 1, len(backoff) - 1)]
            print(f"  {uid}: {res.status}, ponowienie za {delay} s")
            if not cfg.dry_run:
                sleep(delay)
    print("Podsumowanie: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return {"executed": len(todo), "status_counts": dict(counts)}


def _record(cfg, row, gcfg, attempt, ts_start, ts_end, res, raw_file, sha, version, final, raw_json=None) -> dict:
    price = gcfg.get("cost_per_image_usd")
    return {
        "request_uid": row["request_uid"], "attempt": attempt, "final": final,
        "run_order": int(row["run_order"]), "stage": row["stage"],
        "condition_code": row["condition_code"], "frame": row["frame"], "scale": row["scale"],
        "language": row["language"], "generator": row["generator"], "rep": int(row["rep"]),
        "prompt_exact": row["prompt_exact"],
        "provider": "fake" if cfg.dry_run else gcfg["provider"],
        "model_requested": gcfg["model"], "model_returned": res.model_returned,
        "params": api_params(gcfg),
        "ts_start": ts_start, "ts_end": ts_end,
        "status": res.status, "http_status": res.http_status,
        "error_code": res.error_code, "error_message": res.error_message,
        "finish_reason": res.finish_reason, "text_parts": res.text_parts,
        "n_images_returned": res.n_images_returned,
        "request_id": res.request_id, "response_id": res.response_id,
        "usage": res.usage,
        "cost_usd": (float(price) if (price is not None and res.status == P.OK) else None),
        "cost_basis": "config cost_per_image_usd (estimate)" if price is not None else None,
        "raw_file": raw_file, "raw_json": raw_json, "sha256": sha,
        "script_version": version, "shuffle_seed": cfg.seed, "dry_run": cfg.dry_run,
    }
