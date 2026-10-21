"""Blinding: random image_id, PNG without metadata, condition key kept apart.

blinded/<stage>/img_xxxxxx.png carries no condition information: random name,
pixel data only (no EXIF, PNG text chunks or ICC profile), identical
modification time, and files written in random order.
"""

from __future__ import annotations

import csv
import io
import os
import secrets
from pathlib import Path

from PIL import Image

from . import providers as P
from .config import Config
from .generate import read_log, request_state
from .util import KkaiError, read_csv, sha256_bytes, sha256_file, utc_now, write_new

KEY_FIELDS = ["image_id", "request_uid", "stage", "condition_code", "frame", "scale", "language",
              "generator", "raw_file", "raw_sha256", "blinded_sha256", "prepared_at"]
FIXED_MTIME = 1_700_000_000  # all blinded files get the same timestamp


def key_path(cfg: Config) -> Path:
    return cfg.dir("key") / "key.csv"


def read_key(cfg: Config) -> list[dict]:
    p = key_path(cfg)
    return read_csv(p) if p.exists() else []


def clean_png(data: bytes) -> bytes:
    """Re-encode pixels only, dropping every metadata chunk."""
    with Image.open(io.BytesIO(data)) as im:
        alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        im = im.convert("RGBA" if alpha else "RGB")
        # frombytes builds a new image with an empty info dict: no EXIF, ICC or text chunks.
        clean = Image.frombytes(im.mode, im.size, im.tobytes())
    buf = io.BytesIO()
    clean.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def new_image_id(taken: set[str]) -> str:
    while True:
        iid = f"img_{secrets.token_hex(3)}"
        if iid not in taken:
            taken.add(iid)
            return iid


def run_prepare(cfg: Config, stage: str) -> dict:
    final = [s["final"] for s in request_state(read_log(cfg, stage)).values() if s["final"]]
    ok = [r for r in final if r["status"] == P.OK]
    key = read_key(cfg)
    done = {r["request_uid"] for r in key}
    todo = [r for r in ok if r["request_uid"] not in done]
    secrets.SystemRandom().shuffle(todo)  # write order must not follow plan order or generator
    raw_dir, out_dir = cfg.dir("raw"), cfg.dir("blinded") / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    taken = {r["image_id"] for r in key}
    new_rows = []
    for r in todo:
        raw_path = raw_dir / r["raw_file"]
        raw_sha = sha256_file(raw_path)
        if raw_sha != r["sha256"]:
            raise KkaiError(f"Skrót pliku {raw_path.name} różni się od zapisanego w logu. Zatrzymuję.")
        png = clean_png(raw_path.read_bytes())
        iid = new_image_id(taken)
        out = out_dir / f"{iid}.png"
        write_new(out, png)
        os.utime(out, (FIXED_MTIME, FIXED_MTIME))
        new_rows.append({"image_id": iid, "request_uid": r["request_uid"], "stage": stage,
                         "condition_code": r["condition_code"], "frame": r["frame"], "scale": r["scale"],
                         "language": r["language"], "generator": r["generator"], "raw_file": r["raw_file"],
                         "raw_sha256": raw_sha, "blinded_sha256": sha256_bytes(png), "prepared_at": utc_now()})
    if new_rows:
        p = key_path(cfg)
        new_file = not p.exists()
        with open(p, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=KEY_FIELDS, lineterminator="\n")
            if new_file:
                w.writeheader()
            w.writerows(sorted(new_rows, key=lambda x: x["image_id"]))
    refused = sum(1 for r in final if r["status"] != P.OK)
    print(f"Etap {stage}: przygotowano {len(new_rows)} nowych obrazów w {out_dir}; "
          f"wcześniej {len(ok) - len(todo)}; bez obrazu (odmowa, brak obrazu, błąd): {refused}.")
    print(f"Klucz: {key_path(cfg)} (nie otwierać przed bramką 3).")
    return {"prepared": len(new_rows), "without_image": refused}
