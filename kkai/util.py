"""Small shared helpers: time, hashing, append-only files, git version."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


class KkaiError(Exception):
    """Error with a message meant for the user (in Polish)."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def script_version(repo_dir: Path | None = None) -> str:
    """Short hash of the current git commit, with '-dirty' if the tree has changes."""
    cwd = repo_dir or Path(__file__).resolve().parent.parent
    try:
        rev = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=cwd,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=cwd,
                               capture_output=True, text=True, check=True).stdout.strip()
        return f"{rev}-dirty" if dirty else rev
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_new(path: Path, data: bytes) -> None:
    """Write bytes to a file that must not exist yet (data is never overwritten)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def write_new_text(path: Path, text: str) -> None:
    write_new(path, text.encode("utf-8"))


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise KkaiError(f"Uszkodzona linia {n} w {path}: {e}") from e


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_text(rows: Iterable[dict], fieldnames: list[str]) -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def write_csv_once(path: Path, rows: list[dict], fieldnames: list[str]) -> bool:
    """Write a CSV that must not change once written.

    Returns True if the file was created, False if an identical file already
    exists. Raises KkaiError if a different file exists.
    """
    text = csv_text(rows, fieldnames)
    if path.exists():
        if path.read_text(encoding="utf-8") == text:
            return False
        raise KkaiError(f"Plik {path} już istnieje i ma inną treść. Nic nie nadpisuję. "
                        "Jeśli to zamierzone, przenieś stary plik ręcznie i zapisz decyzję w dzienniku.")
    write_new_text(path, text)
    return True


def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        answer = input(f"{question} [t/N] ").strip().lower()
    except EOFError:
        return False
    return answer in {"t", "tak", "y", "yes"}
