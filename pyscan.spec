# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PyPI Scanner (onefile build → pyscan.exe).

Bundles all Python dependencies AND the ``uv`` binary inside the
executable so the end user only needs to provide a ``.env`` file
alongside ``pyscan.exe``.
"""

import os
import shutil
import sys

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    'aiohttp', 'pydantic', 'pydantic_core', 'requests', 'openpyxl',
    'et_xmlfile', 'dotenv', 'certifi', 'multidict', 'yarl', 'aiofiles',
    'annotated_types', 'typing_extensions', 'click', 'charset_normalizer',
    'idna', 'urllib3',
]
hiddenimports += collect_submodules('src')
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('aiohttp')


def _locate_uv_binary():
    """Find the ``uv`` binary so it can be bundled inside the exe.

    Looks first on ``PATH``, then in common ``Scripts``/``bin`` folders
    of the current Python interpreter (where ``pip install uv`` drops
    the executable).
    """
    candidates = ['uv.exe', 'uv'] if os.name == 'nt' else ['uv', 'uv.exe']
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    # Fall back to interpreter-relative locations
    base = os.path.dirname(sys.executable)
    for sub in ('Scripts', 'bin', '.'):
        for name in candidates:
            candidate = os.path.join(base, sub, name)
            if os.path.isfile(candidate):
                return candidate
    return None


uv_binary = _locate_uv_binary()
binaries = []
if uv_binary:
    print(f'[pyscan.spec] Bundling uv from: {uv_binary}')
    binaries.append((uv_binary, '.'))
else:
    raise SystemExit(
        '[pyscan.spec] ERROR: uv binary not found. '
        'Run "pip install uv" before building.'
    )

datas = []
if os.path.exists('.env.example'):
    datas.append(('.env.example', '.'))


a = Analysis(
    ['entry_point.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest', 'mypy', 'tkinter', 'matplotlib', 'numpy', 'scipy',
        'pandas', 'PIL', 'IPython', 'notebook', 'nbformat', 'nbconvert',
        'jupyter', 'jedi', 'parso', 'pygments', 'fastapi', 'uvicorn',
        'starlette',
    ],
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
