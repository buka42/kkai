"""Blinded coding by the AI model (OpenAI Responses API, Batch or one call per image).

The model receives only the instruction, one fixed sentence and the blinded
PNG. No file name, condition, prompt or generator is sent. Every raw response
is appended unchanged to ai_raw.jsonl; ai_codes.csv is derived from it.
"""

from __future__ import annotations

import base64
import csv
import json
import random
import time
from pathlib import Path

from .codebook import check_flags, flatten, load_schema, random_output, validate_output
from .config import Config, api_key, load_env
from .prepare import read_key
from .util import (KkaiError, append_jsonl, confirm, read_csv, read_jsonl, script_version, sha256_bytes,
                   sha256_file, utc_now, write_new_text)

SETS = ("test", "pilot", "main", "validation-repeat")
ENDPOINT = "/v1/responses"


# --- paths and logs -----------------------------------------------------------

def ai_dir(cfg: Config) -> Path:
    return cfg.dir("ai")


def raw_path(cfg: Config) -> Path:
    return ai_dir(cfg) / "ai_raw.jsonl"


def coding_log_path(cfg: Config) -> Path:
    return cfg.dir("logs") / "coding_log.jsonl"


def coder_materials(cfg: Config) -> dict:
    c = cfg.raw["coder"]
    instr_path, schema_path = cfg.path(c["instruction"]), cfg.path(c["schema"])
    for p in (instr_path, schema_path):
        if not p.exists():
            raise KkaiError(f"Brak pliku {p}")
    instruction = instr_path.read_text(encoding="utf-8")
    return {
        "instruction": instruction,
        "instruction_file": instr_path.name,
        "instruction_sha256": sha256_file(instr_path),
        "schema_doc": load_schema(str(schema_path)),
        "schema_file": schema_path.name,
        "schema_sha256": sha256_file(schema_path),
    }


def image_ids_for_set(cfg: Config, set_name: str) -> list[str]:
    if set_name == "validation-repeat":
        p = cfg.dir("human") / "validation_ids.csv"
        if not p.exists():
            raise KkaiError("Brak human/validation_ids.csv. Najpierw: kkai sample")
        return [r["image_id"] for r in read_csv(p)]
    ids = sorted(r["image_id"] for r in read_key(cfg) if r["stage"] == set_name)
    if not ids:
        raise KkaiError(f"Brak obrazów etapu {set_name}. Najpierw: kkai prepare --stage {set_name}")
    return ids


def blinded_file(cfg: Config, image_id: str) -> Path:
    hits = list((cfg.data_dir / "blinded").glob(f"*/{image_id}.png"))
    if len(hits) != 1:
        raise KkaiError(f"Nie znajduję jednoznacznie pliku {image_id}.png w blinded/")
    return hits[0]


# --- request and response -----------------------------------------------------

def request_body(cfg: Config, mats: dict, png: bytes) -> dict:
    c = cfg.raw["coder"]
    schema_doc = mats["schema_doc"]
    body = {
        "model": c["model"],
        "input": [
            {"role": "developer", "content": [{"type": "input_text", "text": mats["instruction"]}]},
            {"role": "user", "content": [
                {"type": "input_text", "text": c.get("user_message", "Code this image according to the instruction.")},
                {"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(png).decode(),
                 "detail": c.get("image_detail", "high")},
            ]},
        ],
        "text": {"format": {"type": "json_schema", "name": schema_doc["name"],
                            "strict": bool(schema_doc.get("strict", True)), "schema": schema_doc["schema"]}},
        "store": False,
    }
    if c.get("reasoning_effort"):
        body["reasoning"] = {"effort": c["reasoning_effort"]}
    return body


def parse_response_body(body: dict) -> tuple[dict | None, str | None]:
    """(parsed JSON output, problem) from a Responses API body."""
    if not isinstance(body, dict):
        return None, "no body"
    if body.get("status") not in (None, "completed"):
        detail = body.get("incomplete_details") or body.get("error")
        return None, f"status {body.get('status')}: {detail}"
    for item in body.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") == "refusal":
                return None, f"refusal: {part.get('refusal')}"
            if part.get("type") == "output_text":
                try:
                    return json.loads(part["text"]), None
                except (ValueError, KeyError) as e:
                    return None, f"invalid JSON: {e}"
    return None, "no output_text"


def _raw_record(cfg, mats, run, image_id, body, status_code=None, error=None, request_id=None, batch_id=None):
    price = cfg.raw["coder"].get("cost_per_image_usd")
    return {
        "image_id": image_id, "run_id": run["run_id"], "set": run["set"], "mode": run["mode"],
        "custom_id": f"{image_id}__{run['run_id']}",
        "model_requested": cfg.raw["coder"]["model"],
        "model_returned": body.get("model") if isinstance(body, dict) else None,
        "ts": utc_now(), "batch_id": batch_id, "request_id": request_id, "status_code": status_code,
        "instruction_file": mats["instruction_file"], "instruction_sha256": mats["instruction_sha256"],
        "schema_file": mats["schema_file"], "schema_sha256": mats["schema_sha256"],
        "usage": body.get("usage") if isinstance(body, dict) else None,
        "cost_usd": float(price) if price is not None and body else None,
        "response": body, "error": error,
        "script_version": script_version(), "dry_run": cfg.dry_run,
    }


# --- runs ---------------------------------------------------------------------

def _runs(cfg: Config) -> dict[str, dict]:
    runs: dict[str, dict] = {}
    for e in read_jsonl(coding_log_path(cfg)):
        r = runs.setdefault(e["run_id"], {"run_id": e["run_id"], "batches": {}, "done": False})
        if e["event"] == "run_created":
            r.update(set=e["set"], mode=e["mode"], image_ids=e["image_ids"])
        elif e["event"] == "batch_submitted":
            r["batches"][e["batch_id"]] = {"image_ids": e["image_ids"], "status": "submitted"}
        elif e["event"] == "batch_status":
            r["batches"][e["batch_id"]]["status"] = e["status"]
        elif e["event"] == "batch_downloaded":
            r["batches"][e["batch_id"]]["status"] = "downloaded"
        elif e["event"] == "run_finished":
            r["done"] = True
    return runs


def _coded(cfg: Config, run_id: str) -> set[str]:
    return {r["image_id"] for r in read_jsonl(raw_path(cfg)) if r["run_id"] == run_id}


def run_code(cfg: Config, set_name: str, assume_yes: bool = False, limit: int | None = None,
             new_run: bool = False, client=None, sleep=time.sleep) -> dict:
    if set_name not in SETS:
        raise KkaiError(f"Nieznany zbiór {set_name!r}; dozwolone: {', '.join(SETS)}")
    load_env(cfg.root)
    mats = coder_materials(cfg)
    runs = [r for r in _runs(cfg).values() if r.get("set") == set_name]
    open_runs = [r for r in runs if not r["done"]]
    if open_runs:
        return _continue_run(cfg, mats, open_runs[-1], client, sleep)
    if runs and not new_run:
        print(f"Zbiór {set_name} ma już zakończone kodowanie ({', '.join(r['run_id'] for r in runs)}). "
              "Nowe przejście tylko z --new-run.")
        _rebuild_codes(cfg)
        return {"run_id": runs[-1]["run_id"], "status": "done"}

    ids = image_ids_for_set(cfg, set_name)
    if limit is not None:
        ids = ids[:limit]
    mode = "fake" if cfg.dry_run else cfg.raw["coder"].get("mode", "batch")
    run_id = f"{set_name}-r{len(runs) + 1}"
    price = cfg.raw["coder"].get("cost_per_image_usd")
    print(f"Kodowanie {set_name}: {len(ids)} obrazów, model {cfg.raw['coder']['model']}, tryb {mode}, "
          f"instrukcja {mats['instruction_file']} (sha256 {mats['instruction_sha256'][:12]}).")
    if not cfg.dry_run:
        print("Szacowany koszt: " + (f"{float(price) * len(ids):.2f} USD" if price is not None
                                    else "nieznany (brak coder.cost_per_image_usd)"))
        if not confirm("Wysłać obrazy do kodowania?", assume_yes):
            print("Przerwano bez wywołań API.")
            return {"run_id": None, "status": "cancelled"}
    run = {"run_id": run_id, "set": set_name, "mode": mode, "image_ids": ids, "batches": {}, "done": False}
    append_jsonl(coding_log_path(cfg), {"event": "run_created", "run_id": run_id, "set": set_name, "mode": mode,
                                        "image_ids": ids, "model": cfg.raw["coder"]["model"],
                                        "instruction_sha256": mats["instruction_sha256"],
                                        "schema_sha256": mats["schema_sha256"], "ts": utc_now(),
                                        "script_version": script_version(), "dry_run": cfg.dry_run})
    if mode == "batch":
        _submit_batches(cfg, mats, run, client or _client(cfg))
        print("Zadania wysłane. Uruchom to samo polecenie później, aby sprawdzić stan i pobrać wyniki.")
        return {"run_id": run_id, "status": "submitted"}
    return _continue_run(cfg, mats, run, client, sleep)


def _client(cfg: Config):
    from openai import OpenAI
    return OpenAI(api_key=api_key("openai"), timeout=float(cfg.raw.get("timeout_seconds", 180)), max_retries=2)


def _continue_run(cfg, mats, run, client, sleep) -> dict:
    if run["mode"] == "batch":
        return _poll_batches(cfg, mats, run, client or _client(cfg))
    done = _coded(cfg, run["run_id"])
    todo = [i for i in run["image_ids"] if i not in done]
    rng = random.Random(f"{cfg.seed}:fake-coder:{run['run_id']}")
    cl = None if run["mode"] == "fake" else (client or _client(cfg))
    for n, image_id in enumerate(todo, 1):
        if run["mode"] == "fake":
            out = random_output(mats["schema_doc"], rng)
            body = {"model": f"fake/{cfg.raw['coder']['model']}", "status": "completed",
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(out)}]}],
                    "usage": {"fake": True}}
            append_jsonl(raw_path(cfg), _raw_record(cfg, mats, run, image_id, body, status_code=200))
        else:
            png = blinded_file(cfg, image_id).read_bytes()
            body = request_body(cfg, mats, png)
            rec = _call_sync(cl, body)
            append_jsonl(raw_path(cfg), _raw_record(cfg, mats, run, image_id, **rec))
        if n % 25 == 0 or n == len(todo):
            print(f"  zakodowano {n}/{len(todo)}")
    append_jsonl(coding_log_path(cfg), {"event": "run_finished", "run_id": run["run_id"], "ts": utc_now()})
    stats = _rebuild_codes(cfg)
    return {"run_id": run["run_id"], "status": "done", **stats}


def _call_sync(client, body: dict) -> dict:
    import openai
    for attempt in range(3):
        try:
            resp = client.responses.with_raw_response.create(**body)
            return {"body": json.loads(resp.text), "status_code": resp.status_code,
                    "request_id": resp.headers.get("x-request-id")}
        except (openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError, openai.RateLimitError) as e:
            last = e
            time.sleep([5, 20, 60][attempt])
        except openai.APIStatusError as e:
            return {"body": None, "status_code": e.status_code, "request_id": getattr(e, "request_id", None),
                    "error": {"message": str(e), "body": e.body}}
    return {"body": None, "error": {"message": str(last)}}


def _submit_batches(cfg, mats, run, client) -> None:
    max_bytes = int(float(cfg.raw["coder"].get("max_batch_mb", 180)) * 1024 * 1024)
    bdir = ai_dir(cfg) / "batches"
    chunks, cur, cur_size = [], [], 0
    for image_id in run["image_ids"]:
        line = json.dumps({"custom_id": f"{image_id}__{run['run_id']}", "method": "POST", "url": ENDPOINT,
                           "body": request_body(cfg, mats, blinded_file(cfg, image_id).read_bytes())},
                          ensure_ascii=False) + "\n"
        size = len(line.encode("utf-8"))
        if cur and cur_size + size > max_bytes:
            chunks.append(cur)
            cur, cur_size = [], 0
        cur.append((image_id, line))
        cur_size += size
    if cur:
        chunks.append(cur)
    for k, chunk in enumerate(chunks, 1):
        path = bdir / f"{run['run_id']}_part{k}.jsonl"
        write_new_text(path, "".join(line for _, line in chunk))
        with open(path, "rb") as f:
            up = client.files.create(file=f, purpose="batch")
        batch = client.batches.create(input_file_id=up.id, endpoint=ENDPOINT, completion_window="24h",
                                      metadata={"run_id": run["run_id"], "part": str(k)})
        append_jsonl(coding_log_path(cfg), {"event": "batch_submitted", "run_id": run["run_id"], "batch_id": batch.id,
                                            "input_file_id": up.id, "input_file": path.name,
                                            "image_ids": [i for i, _ in chunk], "ts": utc_now()})
        print(f"  część {k}/{len(chunks)}: batch {batch.id}, {len(chunk)} obrazów")


def _poll_batches(cfg, mats, run, client) -> dict:
    pending = {b: info for b, info in run["batches"].items() if info["status"] != "downloaded"}
    for batch_id in pending:
        b = client.batches.retrieve(batch_id)
        append_jsonl(coding_log_path(cfg), {"event": "batch_status", "run_id": run["run_id"], "batch_id": batch_id,
                                            "status": b.status, "request_counts": _dump(b.request_counts),
                                            "ts": utc_now()})
        print(f"  batch {batch_id}: {b.status}")
        if b.status not in ("completed", "expired", "cancelled", "failed"):
            continue
        seen = set()
        for fid in (b.output_file_id, b.error_file_id):
            if not fid:
                continue
            text = client.files.content(fid).text
            write_new_text(ai_dir(cfg) / "batches" / f"{run['run_id']}_{batch_id}_{fid}.jsonl", text)
            for line in text.splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                image_id = item["custom_id"].split("__")[0]
                seen.add(image_id)
                resp = item.get("response") or {}
                append_jsonl(raw_path(cfg), _raw_record(cfg, mats, run, image_id, resp.get("body"),
                                                        status_code=resp.get("status_code"), error=item.get("error"),
                                                        request_id=resp.get("request_id"), batch_id=batch_id))
        for image_id in run["batches"][batch_id]["image_ids"]:
            if image_id not in seen:
                append_jsonl(raw_path(cfg), _raw_record(cfg, mats, run, image_id, None, batch_id=batch_id,
                                                        error={"message": f"no result, batch status {b.status}"}))
        append_jsonl(coding_log_path(cfg), {"event": "batch_downloaded", "run_id": run["run_id"],
                                            "batch_id": batch_id, "ts": utc_now()})
        run["batches"][batch_id]["status"] = "downloaded"
    if all(i["status"] == "downloaded" for i in run["batches"].values()):
        append_jsonl(coding_log_path(cfg), {"event": "run_finished", "run_id": run["run_id"], "ts": utc_now()})
        stats = _rebuild_codes(cfg)
        print(f"Przejście {run['run_id']} zakończone.")
        return {"run_id": run["run_id"], "status": "done", **stats}
    print("Nie wszystkie części są gotowe. Uruchom polecenie ponownie później.")
    return {"run_id": run["run_id"], "status": "pending"}


def _dump(obj):
    return obj.model_dump() if hasattr(obj, "model_dump") else obj


# --- derived table ------------------------------------------------------------

CODE_META = ["image_id", "run_id", "set", "model_returned", "instruction_sha256", "valid", "problem",
             "flags_missing", "needs_review_mismatch", "temporal_rule_mismatch", "identity_terms",
             "needs_review_program"]


def _rebuild_codes(cfg: Config) -> dict:
    """Recreate ai_codes.csv from ai_raw.jsonl (derived table, safe to regenerate)."""
    schema_cache = {}
    rows, fields = [], list(CODE_META)
    for rec in read_jsonl(raw_path(cfg)):
        key = rec["schema_file"]
        if key not in schema_cache:
            schema_cache[key] = load_schema(str(cfg.path(cfg.raw["coder"]["schema"])))
        out, problem = parse_response_body(rec["response"]) if rec["response"] else (None, rec.get("error") and "error")
        row = {"image_id": rec["image_id"], "run_id": rec["run_id"], "set": rec["set"],
               "model_returned": rec.get("model_returned"), "instruction_sha256": rec["instruction_sha256"]}
        if out is not None:
            errors = validate_output(schema_cache[key], out)
            if errors:
                problem = " | ".join(errors[:5])
            else:
                row.update(check_flags(out))
                flat = flatten(out)
                row.update(flat)
                for k in flat:
                    if k not in fields:
                        fields.append(k)
        row["valid"] = problem is None
        row["problem"] = problem or (json.dumps(rec.get("error"))[:300] if rec.get("error") else None)
        if out is None and not row["problem"]:
            row["problem"] = "no response"
            row["valid"] = False
        rows.append(row)
    path = ai_dir(cfg) / "ai_codes.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    n_bad = sum(1 for r in rows if not r["valid"])
    print(f"ai_codes.csv: {len(rows)} wierszy, niezgodnych ze schematem lub bez wyniku: {n_bad}")
    return {"rows": len(rows), "invalid": n_bad}
