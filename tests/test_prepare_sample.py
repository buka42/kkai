import io

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from kkai.generate import run_generate
from kkai.plan import write_plan
from kkai.prepare import clean_png, read_key, run_prepare
from kkai.sample import run_sample


def test_clean_png_drops_metadata():
    buf = io.BytesIO()
    info = PngInfo()
    info.add_text("prompt", "multicultural Kazimierz W-Z-EN-GG")
    Image.new("RGB", (4, 4), (9, 9, 9)).save(buf, format="PNG", pnginfo=info)
    out = clean_png(buf.getvalue())
    assert b"Kazimierz" not in out and b"tEXt" not in out and b"eXIf" not in out
    with Image.open(io.BytesIO(out)) as im:
        assert im.info == {} or set(im.info) <= {"dpi"}
        assert im.getpixel((0, 0)) == (9, 9, 9)


def _generate(cfg, stage="main"):
    write_plan(cfg, stage)
    run_generate(cfg, stage, assume_yes=True)


def test_blinded_folder_has_no_condition_info(cfg):
    _generate(cfg, "pilot")
    run_prepare(cfg, "pilot")
    key = read_key(cfg)
    files = list((cfg.data_dir / "blinded" / "pilot").glob("*"))
    assert len(files) == len(key)
    codes = {r["condition_code"] for r in key} | {"OA", "GG", "Kazimierz", "Krak"}
    for f in files:
        assert f.name.startswith("img_") and f.suffix == ".png"
        assert not any(c in f.name for c in codes)
        data = f.read_bytes()
        # 2-letter generator codes can occur by chance in compressed pixel data, so check long strings only
        assert not any(c.encode() in data for c in codes if len(c) > 4)
    assert len({f.stat().st_mtime for f in files}) == 1


def test_prepare_is_additive(cfg):
    _generate(cfg, "pilot")
    run_prepare(cfg, "pilot")
    n = len(read_key(cfg))
    out = run_prepare(cfg, "pilot")
    assert out["prepared"] == 0 and len(read_key(cfg)) == n


def test_sample_five_per_condition(cfg):
    _generate(cfg)
    run_prepare(cfg, "main")
    sets = run_sample(cfg)
    key = {r["image_id"]: r["condition_code"] for r in read_key(cfg)}
    from collections import Counter
    c = Counter(key[i] for i in sets["validation"])
    assert len(c) == 32 and set(c.values()) == {5}
    assert len(sets["retest"]) == 50 and set(sets["retest"]) <= set(sets["validation"])
    assert run_sample(cfg) == sets  # same seed, same draw, files unchanged
