from collections import Counter

import pytest

from kkai.plan import build_plan, read_plan, write_plan
from kkai.util import KkaiError


@pytest.mark.parametrize("stage,total,conds,per", [("test", 16, 16, 1), ("pilot", 32, 16, 2), ("main", 640, 32, 20)])
def test_counts(cfg, stage, total, conds, per):
    rows = build_plan(cfg, stage)
    c = Counter(r["condition_code"] for r in rows)
    assert len(rows) == total
    assert len(c) == conds
    assert set(c.values()) == {per}


def test_pilot_is_english_only(cfg):
    assert {r["language"] for r in build_plan(cfg, "pilot")} == {"EN"}


def test_same_seed_same_plan_other_seed_other_plan(cfg):
    a = build_plan(cfg, "main")
    assert a == build_plan(cfg, "main")
    cfg.raw["shuffle_seed"] = 1
    assert [r["condition_code"] for r in build_plan(cfg, "main")] != [r["condition_code"] for r in a]


def test_generators_alternate(cfg):
    gens = [r["generator"] for r in build_plan(cfg, "main")]
    assert all(gens[i] != gens[i + 1] for i in range(len(gens) - 1))


def test_order_is_shuffled(cfg):
    conds = [r["condition_code"] for r in build_plan(cfg, "main")]
    assert conds != sorted(conds)


def test_uid_carries_no_condition(cfg):
    for r in build_plan(cfg, "main"):
        assert r["frame"] not in r["request_uid"].split("_")[1]
        assert r["generator"] not in r["request_uid"]


def test_plan_file_never_overwritten(cfg):
    write_plan(cfg, "test")
    _, _, created = write_plan(cfg, "test")
    assert created is False
    cfg.raw["shuffle_seed"] = 7
    with pytest.raises(KkaiError):
        write_plan(cfg, "test")
    with pytest.raises(KkaiError):
        read_plan(cfg, "test")
