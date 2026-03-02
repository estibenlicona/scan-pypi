"""
Build script for creating PyPI Scanner standalone executable.

Usage:
    python build.py          # Build using .spec file (recommended)
    python build.py --clean  # Clean previous builds first
    python build.py --onefile # Single-file executable (slower startup)

Requirements:
    pip install pyinstaller
"""

from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SPEC_FILE = PROJECT_ROOT / "pypi_scanner.spec"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUT_DIR = DIST_DIR / "pypi-scanner"


def clean_build_artifacts() -> None:
    """Remove previous build and dist directories."""
    for directory in (BUILD_DIR, DIST_DIR):
        if directory.exists():
            print(f"[CLEAN] Removing {directory}")
            shutil.rmtree(directory)
    print("[CLEAN] Done")


def check_pyinstaller() -> None:
    """Verify PyInstaller is installed."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[ERROR] PyInstaller not installed. Run:")
        print("  pip install pyinstaller")
        sys.exit(1)


def build_with_spec() -> None:
    """Build using the .spec file (folder mode)."""
    print("[BUILD] Building with spec file...")
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm"]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("[ERROR] Build failed")
        sys.exit(1)
    print(f"[OK] Build complete: {OUTPUT_DIR}")


def build_onefile() -> None:
    """Build as a single executable file."""
    print("[BUILD] Building single-file executable...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--console",
        "--name", "pypi-scanner",
        "--paths", ".",
        # Hidden imports for key packages
        "--hidden-import", "src",
        "--hidden-import", "aiohttp",
        "--hidden-import", "aiofiles",
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic_core",
        "--hidden-import", "requests",
        "--hidden-import", "openpyxl",
        "--hidden-import", "dotenv",
        "--hidden-import", "certifi",
        "--hidden-import", "multidict",
        "--hidden-import", "yarl",
        "--hidden-import", "annotated_types",
        "--hidden-import", "typing_extensions",
        "--collect-submodules", "src",
        "--collect-submodules", "pydantic",
        # Exclude unnecessary packages
        "--exclude-module", "pytest",
        "--exclude-module", "mypy",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "entry_point.py",
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("[ERROR] Build failed")
        sys.exit(1)
    print(f"[OK] Build complete: {DIST_DIR / 'pypi-scanner.exe'}")


def copy_runtime_files() -> None:
    """Copy files needed at runtime alongside the executable."""
    target = OUTPUT_DIR if OUTPUT_DIR.exists() else DIST_DIR

    # Copy .env.example for user reference
    env_example = PROJECT_ROOT / ".env.example"
    if env_example.exists():
        shutil.copy2(env_example, target / ".env.example")
        print(f"[COPY] .env.example -> {target}")

    # Copy .env if it exists (user config)
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        shutil.copy2(env_file, target / ".env")
        print(f"[COPY] .env -> {target}")

    # Create empty requirements.scan.txt as template
    scan_template = target / "requirements.scan.txt.example"
    scan_template.write_text(
        "# Lista de paquetes a escanear (uno por línea)\n"
        "# Solo versiones exactas (==) o sin versión\n"
        "# Ejemplos:\n"
        "# requests==2.28.0\n"
        "# flask\n"
        "# django==4.2\n",
        encoding="utf-8",
    )
    print(f"[COPY] requirements.scan.txt.example -> {target}")


def main() -> None:
    """Main build entry point."""
    parser = argparse.ArgumentParser(description="Build PyPI Scanner executable")
    parser.add_argument(
        "--clean", action="store_true",
        help="Clean previous build artifacts before building",
    )
    parser.add_argument(
        "--onefile", action="store_true",
        help="Build as single file (slower startup, easier distribution)",
    )
    args = parser.parse_args()

    check_pyinstaller()

    if args.clean:
        clean_build_artifacts()

    if args.onefile:
        build_onefile()
    else:
        build_with_spec()

    copy_runtime_files()

    print("\n" + "=" * 60)
    print("BUILD EXITOSO")
    print("=" * 60)
    if args.onefile:
        print(f"Ejecutable: {DIST_DIR / 'pypi-scanner.exe'}")
    else:
        print(f"Carpeta:    {OUTPUT_DIR}")
        print(f"Ejecutable: {OUTPUT_DIR / 'pypi-scanner.exe'}")
    print("\nPara distribuir:")
    if args.onefile:
        print("  1. Copia pypi-scanner.exe al destino")
    else:
        print("  1. Copia toda la carpeta dist/pypi-scanner/ al destino")
    print("  2. Crea un archivo .env con la configuración (ver .env.example)")
    print("  3. Ejecuta: pypi-scanner scan <paquete>")
    print("=" * 60)


if __name__ == "__main__":
    main()
