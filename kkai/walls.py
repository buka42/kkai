"""Image walls: 8 conditions (frame x scale, languages pooled) x generators.

Selection rule fixed before viewing (protocol section 8): the first 8 images
of each cell by random image_id.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .plan import FRAMES, SCALES
from .prepare import read_key

PER_WALL = 8
THUMB = 384
LABEL_H = 48


def select(cfg: Config) -> dict[str, list[str]]:
    key = [r for r in read_key(cfg) if r["stage"] == "main"]
    out = {}
    for s in SCALES:
        for f in FRAMES:
            for g in cfg.generators:
                ids = sorted(r["image_id"] for r in key if r["frame"] == f and r["scale"] == s and r["generator"] == g)
                out[f"{f}-{s}-{g}"] = ids[:PER_WALL]
    return out


def run_walls(cfg: Config) -> Path:
    out_dir = cfg.dir("results") / "walls"
    out_dir.mkdir(exist_ok=True)
    blinded = cfg.data_dir / "blinded" / "main"
    font = ImageFont.load_default(size=28) if hasattr(ImageFont, "load_default") else None
    sel = select(cfg)
    lines = ["wall,position,image_id"]
    for cell, ids in sel.items():
        cols, rows = 4, 2
        wall = Image.new("RGB", (cols * THUMB, rows * THUMB + LABEL_H), "white")
        draw = ImageDraw.Draw(wall)
        draw.text((12, 8), f"{cell}  (first {PER_WALL} by random id)", fill="black", font=font)
        for i, iid in enumerate(ids):
            with Image.open(blinded / f"{iid}.png") as im:
                im = im.convert("RGB")
                im.thumbnail((THUMB, THUMB))
                wall.paste(im, ((i % cols) * THUMB, LABEL_H + (i // cols) * THUMB))
            lines.append(f"{cell},{i + 1},{iid}")
        wall.save(out_dir / f"wall_{cell}.png")
        wall.save(out_dir / f"wall_{cell}.pdf", resolution=150)
    (out_dir / "walls_selection.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Ściany obrazów: {out_dir} ({len(sel)} ścian)")
    return out_dir
