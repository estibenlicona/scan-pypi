"""
Unified entry point for the PyInstaller executable.

Exposes the ``run`` and ``report`` subcommands using argparse subparsers,
reusing the same argument definitions and command logic as the source CLI.
Usage:
    pyscan run requests flask
    pyscan run -f requirements.scan.txt
    pyscan report
"""

from __future__ import annotations
import argparse
import os
import sys


def _set_working_directory() -> None:
    """Ensure CWD is the directory containing the executable (frozen mode)."""
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))


def _report_command(args: argparse.Namespace) -> None:
    """Generate the friendly HTML viewer from the consolidated JSON report."""
    from src.interface.cli.html_report import main as html_main
    html_main(report_path=args.report, output_path=args.output)


def _approve_command(args: argparse.Namespace) -> None:
    """Grant manual approval to one or more packages in the master report."""
    from src.interface.cli.approve import main as approve_main
    approve_main(
        specs=args.packages,
        report_path=args.report,
        motivo=args.motivo,
        por=args.por,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with ``run``, ``approve`` and ``report``."""
    from src.interface.cli.main import add_scan_arguments, run_command

    parser = argparse.ArgumentParser(
        prog="pyscan",
        description="PyPI Scanner — analiza dependencias, vulnerabilidades y licencias.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  pyscan run requests==2.28.0\n"
            "  pyscan run -f requirements.scan.txt\n"
            "  pyscan approve requests==2.28.0 --motivo \"Revisado\" --por ana\n"
            "  pyscan report\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Escanear paquetes PyPI")
    add_scan_arguments(run_parser)
    run_parser.set_defaults(func=run_command)

    approve_parser = subparsers.add_parser(
        "approve", help="Aprobar manualmente paquetes en el reporte maestro"
    )
    approve_parser.add_argument(
        "packages", nargs="+", metavar="paquete",
        help="Paquetes a aprobar (ej: requests==2.28.0)",
    )
    approve_parser.add_argument(
        "--motivo", type=str, default=None,
        help="Motivo de la aprobación manual",
    )
    approve_parser.add_argument(
        "--por", type=str, default=None,
        help="Responsable de la aprobación",
    )
    approve_parser.add_argument(
        "--report", type=str, default="consolidated_report.json",
        help="Ruta al JSON maestro",
    )
    approve_parser.set_defaults(func=_approve_command)

    report_parser = subparsers.add_parser(
        "report", help="Generar visor HTML del reporte consolidado"
    )
    report_parser.add_argument(
        "--report", type=str, default="consolidated_report.json",
        help="Ruta al JSON maestro",
    )
    report_parser.add_argument(
        "--output", type=str, default="report.html",
        help="Ruta del HTML a generar",
    )
    report_parser.set_defaults(func=_report_command)

    return parser


def main() -> None:
    """Unified CLI dispatcher for the packaged executable."""
    _set_working_directory()
    args = _build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
