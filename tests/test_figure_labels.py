def test_figure_uses_display_labels(cfg, monkeypatch):
    monkeypatch.chdir(cfg.root)
    cfg.raw["figure"] = {"labels": {"OA": "GPT Image 2.5 Flare", "GG": "Gemini Nano Banana 2.1"}}
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    seen = []
    orig = plt.Axes.legend

    def spy(self, *a, **k):
        seen.extend(t for t in self.get_legend_handles_labels()[1])
        return orig(self, *a, **k)

    monkeypatch.setattr(plt.Axes, "legend", spy)
    from kkai.figure import run_figure
    import kkai.figure as fig
    monkeypatch.setattr(fig, "load_dataset", lambda c: [])
    run_figure(cfg)
    assert seen == ["GPT Image 2.5 Flare", "Gemini Nano Banana 2.1"]
