"""
Build script for creating PyPI Scanner standalone executable (pyscan.exe).

Usage:
    python build.py          # Build pyscan.exe (onefile) using pyscan.spec
    python build.py --clean  # Clean previous builds first

Requirements:
    pip install -r requirements.txt
    (PyInstaller and uv are listed there.)

Output:
    dist/pyscan.exe   — standalone single-file executable. The end user
                        only needs to place a .env file next to it.
"""

from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SPEC_FILE = PROJECT_ROOT / "pyscan.spec"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
EXE_NAME = "pyscan.exe" if sys.platform.startswith("win") else "pyscan"
EXE_PATH = DIST_DIR / EXE_NAME


def clean_build_artifacts() -> None:
    """Remove previous build and dist directories."""
    for directory in (BUILD_DIR, DIST_DIR):
        if directory.exists():
            print(f"[CLEAN] Removing {directory}")
            shutil.rmtree(directory)
    print("[CLEAN] Done")


def check_requirements() -> None:
    """Verify PyInstaller and uv are available."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[ERROR] PyInstaller not installed. Run:")
        print("  pip install pyinstaller")
        sys.exit(1)

    if shutil.which("uv") is None:
        print("[ERROR] 'uv' binary not found on PATH. Run:")
        print("  pip install uv")
        sys.exit(1)


def build_with_spec() -> None:
    """Build pyscan.exe using pyscan.spec (onefile mode)."""
    print(f"[BUILD] Building with {SPEC_FILE.name}...")
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm"]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("[ERROR] Build failed")
        sys.exit(1)
    print(f"[OK] Build complete: {EXE_PATH}")


def copy_runtime_files() -> None:
    """Copy the only file the end user must edit: .env.

    Everything else (including the uv binary) is already bundled inside
    pyscan.exe.
    """
    # Copy .env.example for reference if available
    env_example = PROJECT_ROOT / ".env.example"
    if env_example.exists():
        shutil.copy2(env_example, DIST_DIR / ".env.example")
        print(f"[COPY] .env.example -> {DIST_DIR}")

    # Copy current .env (user config) if it exists
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        shutil.copy2(env_file, DIST_DIR / ".env")
        print(f"[COPY] .env -> {DIST_DIR}")


def main() -> None:
    """Main build entry point."""
    parser = argparse.ArgumentParser(
        description="Build pyscan standalone executable",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Clean previous build artifacts before building",
    )
    args = parser.parse_args()

    check_requirements()

    if args.clean:
        clean_build_artifacts()

    build_with_spec()
    copy_runtime_files()

    print("\n" + "=" * 60)
    print("BUILD EXITOSO")
    print("=" * 60)
    print(f"Ejecutable: {EXE_PATH}")
    print("\nPara distribuir:")
    print(f"  1. Copia {EXE_NAME} al destino")
    print("  2. Crea un archivo .env junto al ejecutable "
          "(ver .env.example)")
    print(f"  3. Ejecuta: {EXE_NAME} run <paquete>")
    print("=" * 60)


if __name__ == "__main__":
    main()
