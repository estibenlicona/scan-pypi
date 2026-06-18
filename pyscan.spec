# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import shutil

# Bundle the uv binary so the executable is self-contained and does not
# require uv to be installed on the target machine (e.g. a clean sandbox).
# Prefer the binary shipped by the pip `uv` package (reproducible in CI);
# fall back to a standalone `uv` on PATH for local/offline builds.
try:
    from uv import find_uv_bin
    uv_bin = find_uv_bin()
except Exception:
    uv_bin = shutil.which("uv")

if not uv_bin:
    raise SystemExit(
        "ERROR: no se encontro el binario 'uv' para empaquetar. "
        "Instala el paquete pip 'uv' o asegurate de que 'uv' este en el PATH."
    )

hiddenimports =['aiohttp', 'pydantic', 'pydantic_core', 'requests', 'openpyxl', 'et_xmlfile', 'dotenv', 'certifi', 'multidict', 'yarl', 'aiofiles', 'annotated_types', 'typing_extensions', 'click', 'charset_normalizer', 'idna', 'urllib3']
hiddenimports += collect_submodules('src')
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('aiohttp')


a = Analysis(
    ['entry_point.py'],
    pathex=['.'],
    binaries=[(uv_bin, '.')],
    datas=[('viewer/report_template.html', 'viewer')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'mypy', 'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL', 'IPython', 'notebook', 'nbformat', 'nbconvert', 'jupyter', 'jedi', 'parso', 'pygments', 'fastapi', 'uvicorn', 'starlette'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pyscan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
