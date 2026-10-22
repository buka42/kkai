"""Loading config.yaml and API keys from the environment (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .util import KkaiError

API_KEY_ENV = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
STAGES = ("test", "pilot", "pilot2", "main")
# Pilot stages share pilot_languages; pilot2 is the repeat after the prompt change of 22.10.
PILOT_STAGES = ("pilot", "pilot2")
# Keys in a generator block that configure kkai and are not sent to the API.
LOCAL_GENERATOR_KEYS = {"provider", "model", "cost_per_image_usd", "min_interval_seconds"}


@dataclass
class Config:
    raw: dict
    root: Path
    dry_run: bool = False

    @property
    def data_dir(self) -> Path:
        base = self.raw.get("data_dir", "data")
        if self.dry_run:
            base = f"{base}_dryrun"
        return (self.root / base).resolve()

    @property
    def seed(self) -> int:
        return int(self.raw["shuffle_seed"])

    @property
    def generators(self) -> dict:
        return self.raw["generators"]

    def path(self, rel: str) -> Path:
        return (self.root / rel).resolve()

    def dir(self, name: str) -> Path:
        d = self.data_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d


def load_config(path: str | Path = "config.yaml", dry_run: bool = False) -> Config:
    path = Path(path)
    if not path.exists():
        raise KkaiError(f"Brak pliku konfiguracji: {path}")
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    _validate(raw)
    return Config(raw=raw, root=path.resolve().parent, dry_run=dry_run)


def _validate(raw: dict) -> None:
    missing = [k for k in ("shuffle_seed", "generators", "reps", "prompts") if k not in raw]
    if missing:
        raise KkaiError(f"W config.yaml brakuje pól: {', '.join(missing)}")
    for code, g in raw["generators"].items():
        if g.get("provider") not in API_KEY_ENV:
            raise KkaiError(f"Generator {code}: nieznany provider {g.get('provider')!r}")
        if not g.get("model"):
            raise KkaiError(f"Generator {code}: brak nazwy modelu")
    for stage in STAGES:
        if stage not in raw["reps"]:
            raise KkaiError(f"W config.yaml brakuje reps.{stage}")


def load_env(root: Path) -> None:
    """Load .env from the project root (or a parent directory) if python-dotenv is present."""
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    env = root / ".env"
    load_dotenv(env if env.exists() else find_dotenv(usecwd=True), override=False)


def api_key(provider: str) -> str:
    name = API_KEY_ENV[provider]
    key = os.environ.get(name, "").strip()
    if not key:
        raise KkaiError(f"Brak klucza {name}. Wpisz go do pliku .env (poza repozytorium).")
    return key


def api_params(generator: dict) -> dict:
    """Parameters sent to the API: the generator block minus local keys."""
    return {k: v for k, v in generator.items() if k not in LOCAL_GENERATOR_KEYS}
