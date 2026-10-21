import shutil
from pathlib import Path

import pytest

from kkai.config import load_config

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def cfg(tmp_path):
    shutil.copy(ROOT / "config.yaml", tmp_path / "config.yaml")
    shutil.copytree(ROOT / "materials", tmp_path / "materials")
    return load_config(tmp_path / "config.yaml", dry_run=True)
