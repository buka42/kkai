"""Command line interface: kkai <command> [options]."""

from __future__ import annotations

import argparse
import sys

from .config import STAGES, load_config
from .util import KkaiError


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", default="config.yaml", help="ścieżka do config.yaml")
    p.add_argument("--dry-run", action="store_true",
                   help="generator zastępczy i model zastępczy, zapis do data_dryrun/")


def cmd_plan(args) -> None:
    from .plan import write_plan
    cfg = load_config(args.config, dry_run=args.dry_run)
    path, rows, created = write_plan(cfg, args.stage)
    per_cond = {}
    for r in rows:
        per_cond[r["condition_code"]] = per_cond.get(r["condition_code"], 0) + 1
    sizes = sorted(set(per_cond.values()))
    print(f"{'Zapisano' if created else 'Plan już istnieje i jest identyczny'}: {path}")
    print(f"Żądań: {len(rows)}; warunków: {len(per_cond)}; żądań na warunek: {sizes}")


def cmd_generate(args) -> None:
    from .generate import run_generate
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_generate(cfg, args.stage, assume_yes=args.yes, limit=args.limit, retry_errors=args.retry_errors)


def cmd_prepare(args) -> None:
    from .prepare import run_prepare
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_prepare(cfg, args.stage)


def cmd_sample(args) -> None:
    from .sample import run_sample
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_sample(cfg)


def cmd_code(args) -> None:
    from .code_ai import run_code
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_code(cfg, args.set, assume_yes=args.yes, limit=args.limit, new_run=args.new_run, mode=args.mode)


def cmd_sheet(args) -> None:
    from .sheets import run_sheet
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_sheet(cfg, args.set)


def cmd_annotate(args) -> None:
    from .annotate import run_annotate
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_annotate(cfg, args.set, args.coder_id, port=args.port)


def cmd_ingest(args) -> None:
    from .ingest import run_ingest
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_ingest(cfg, args.sheet, args.set, args.coder_id, args.round)


def cmd_validate(args) -> None:
    from .validate import run_validate
    cfg = load_config(args.config, dry_run=args.dry_run)
    run_validate(cfg)


def cmd_review(args) -> None:
    from .review import run_ingest_review, run_review
    cfg = load_config(args.config, dry_run=args.dry_run)
    if args.ingest:
        run_ingest_review(cfg, args.ingest)
    else:
        run_review(cfg)


def cmd_analyze(args) -> None:
    from .analyze import run_analyze
    run_analyze(load_config(args.config, dry_run=args.dry_run))


def cmd_walls(args) -> None:
    from .walls import run_walls
    run_walls(load_config(args.config, dry_run=args.dry_run))


def cmd_figure(args) -> None:
    from .figure import run_figure
    run_figure(load_config(args.config, dry_run=args.dry_run))


def cmd_export(args) -> None:
    from .export import run_export
    run_export(load_config(args.config, dry_run=args.dry_run), with_images=args.with_images)


def cmd_simulate_human(args) -> None:
    from .simulate import simulate_sheet
    cfg = load_config(args.config, dry_run=True)
    simulate_sheet(cfg, args.sheet)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="kkai", description="Kraków–Kazimierz AI: program badania")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="buduje plan żądań dla etapu")
    _common(p)
    p.add_argument("--stage", required=True, choices=STAGES)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("generate", help="wykonuje plan (wznawia po przerwaniu)")
    _common(p)
    p.add_argument("--stage", required=True, choices=STAGES)
    p.add_argument("--yes", action="store_true", help="bez pytania o potwierdzenie kosztu")
    p.add_argument("--limit", type=int, default=None, help="wykonaj najwyżej N żądań (np. 10 na próbę)")
    p.add_argument("--retry-errors", action="store_true",
                   help="ponów żądania zakończone błędem technicznym po wyczerpaniu ponowień")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("prepare", help="zaślepienie: losowe image_id, PNG bez metadanych, klucz")
    _common(p)
    p.add_argument("--stage", required=True, choices=STAGES)
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("sample", help="losuje zbiór walidacyjny i podzbiory")
    _common(p)
    p.set_defaults(func=cmd_sample)

    p = sub.add_parser("code", help="kodowanie obrazów modelem (Batch albo pojedyncze wywołania)")
    _common(p)
    p.add_argument("--set", required=True, choices=["test", "pilot", "pilot2", "main", "validation-repeat"])
    p.add_argument("--yes", action="store_true", help="bez pytania o potwierdzenie kosztu")
    p.add_argument("--limit", type=int, default=None, help="koduj najwyżej N obrazów (np. 10 na próbę)")
    p.add_argument("--new-run", action="store_true", help="nowe przejście dla zbioru już zakodowanego")
    p.add_argument("--mode", choices=["batch", "sync"], default=None,
                   help="nadpisuje coder.mode z config.yaml (sync = od razu, np. na próbę)")
    p.set_defaults(func=cmd_code)

    p = sub.add_parser("sheet", help="arkusz XLSX i strona HTML do kodowania ręcznego")
    _common(p)
    p.add_argument("--set", required=True, choices=["pilot", "pilot2", "validation", "retest", "second"])
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("annotate", help="kodowanie ręczne w przeglądarce: obraz i przyciski, zapis do arkusza")
    _common(p)
    p.add_argument("--set", required=True, choices=["pilot", "pilot2", "validation", "retest", "second"])
    p.add_argument("--coder-id", required=True, help="identyfikator kodera, np. PB")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_annotate)

    p = sub.add_parser("ingest", help="wczytuje wypełniony arkusz do human_codes.csv")
    _common(p)
    p.add_argument("--sheet", required=True, help="ścieżka do wypełnionego arkusza XLSX")
    p.add_argument("--set", required=True, choices=["pilot", "pilot2", "validation", "retest", "second"])
    p.add_argument("--coder-id", required=True, help="identyfikator kodera, np. PB")
    p.add_argument("--round", type=int, default=1, help="runda kodowania (test–retest: 2)")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("validate", help="zgodność model–człowiek i tabela decyzji (bramka 3)")
    _common(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("review", help="arkusz przeglądu po bramce 3; z --ingest wczytuje poprawki i tworzy kody końcowe")
    _common(p)
    p.add_argument("--ingest", default=None, help="ścieżka do wypełnionego review_sheet.xlsx")
    p.set_defaults(func=cmd_review)

    for name, func, text in [("analyze", cmd_analyze, "testy H1–H4, odsetki z przedziałami, odporność"),
                             ("walls", cmd_walls, "ściany obrazów według reguły doboru"),
                             ("figure", cmd_figure, "wykres ramy czasowej w 8 warunkach")]:
        p = sub.add_parser(name, help=text)
        _common(p)
        p.set_defaults(func=func)

    p = sub.add_parser("export", help="pakiet replikacyjny bez kluczy")
    _common(p)
    p.add_argument("--with-images", action="store_true", help="dołącz obrazy z blinded/")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("simulate-human", help="tylko --dry-run: wypełnia arkusz losowo, by przetestować dalsze kroki")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--sheet", required=True, help="arkusz do wypełnienia (validation_sheet.xlsx, review_sheet.xlsx …)")
    p.set_defaults(func=cmd_simulate_human)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except KkaiError as e:
        print(f"BŁĄD: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nPrzerwano. Uruchom to samo polecenie ponownie, aby wznowić.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
