"""
Unified entry point for PyInstaller executable.

Dispatches to run or report based on the first argument.
Usage:
    pyscan run requests flask
    pyscan report
"""

from __future__ import annotations
import sys
import os


def _set_working_directory() -> None:
    """Ensure CWD is the directory containing the executable."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        exe_dir = os.path.dirname(sys.executable)
        os.chdir(exe_dir)


def main() -> None:
    """Unified CLI dispatcher."""
    _set_working_directory()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _print_help()
        sys.exit(0)

    command = sys.argv[1]
    # Remove the subcommand from argv so each module sees its own args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "run":
        from src.interface.cli.main import main as run_main
        run_main()
    elif command == "report":
        from src.interface.cli.consolidate import main as report_main
        report_main()
    else:
        print(f"[ERROR] Comando desconocido: '{command}'", file=sys.stderr)
        _print_help()
        sys.exit(1)


def _print_help() -> None:
    """Print usage information."""
    print(
        "PyPI Scanner — Ejecutable standalone\n"
        "\n"
        "Uso:\n"
        "  pyscan <comando> [opciones]\n"
        "\n"
        "Comandos disponibles:\n"
        "  run           Escanear paquetes PyPI\n"
        "  report        Consolidar reportes históricos en XLSX\n"
        "\n"
        "Ejemplos:\n"
        "  pyscan run requests==2.28.0\n"
        "  pyscan run -f requirements.scan.txt\n"
        "  pyscan run requests --markdown\n"
        "  pyscan report\n"
        "\n"
        "Configuración:\n"
        "  Coloca un archivo .env junto al ejecutable para configurar\n"
        "  las reglas de negocio, caché, y tokens de API.\n"
        "  Ver .env.example para referencia.\n"
    )


if __name__ == "__main__":
    main()
