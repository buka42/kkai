"""Figure: share of historical or staged frame in the 8 conditions, per generator, with Wilson CIs."""

from __future__ import annotations

from pathlib import Path

from .analyze import has, load_dataset, wilson
from .config import Config
from .plan import FRAMES, SCALES

MARKERS = ["o", "s", "^", "D"]


def run_figure(cfg: Config) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = load_dataset(cfg)
    gens = list(cfg.generators)
    cells = [(s, f) for s in SCALES for f in FRAMES]
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    width = 0.8 / len(gens)
    for gi, g in enumerate(gens):
        xs, ps, lo_err, hi_err = [], [], [], []
        for ci, (s, f) in enumerate(cells):
            vals = [has(r, "hist_or_staged") for r in data
                    if r["generator"] == g and r["frame"] == f and r["scale"] == s and has(r, "hist_or_staged") is not None]
            k, n = sum(vals), len(vals)
            p = k / n if n else float("nan")
            lo, hi = wilson(k, n)
            xs.append(ci + (gi - (len(gens) - 1) / 2) * width)
            ps.append(p)
            lo_err.append(p - lo)
            hi_err.append(hi - p)
        ax.errorbar(xs, ps, yerr=[lo_err, hi_err], fmt=MARKERS[gi % len(MARKERS)], color="black",
                    mfc="white" if gi % 2 else "black", capsize=3, label=g, linestyle="none")
    ax.set_xticks(range(len(cells)))
    ax.set_xticklabels([f"{f}-{s}" for s, f in cells])
    ax.axvline(len(FRAMES) - 0.5, color="grey", linewidth=0.8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Historical or staged frame (share)")
    ax.legend(frameon=False)
    fig.tight_layout()
    out_dir = cfg.dir("results") / "figures"
    out_dir.mkdir(exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"temporal_frame.{ext}", dpi=300)
    plt.close(fig)
    print(f"Wykres: {out_dir / 'temporal_frame.png'}")
    return out_dir
