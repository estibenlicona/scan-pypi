# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['aiohttp', 'pydantic', 'pydantic_core', 'requests', 'openpyxl', 'et_xmlfile', 'dotenv', 'certifi', 'multidict', 'yarl', 'aiofiles', 'annotated_types', 'typing_extensions', 'click', 'charset_normalizer', 'idna', 'urllib3']
hiddenimports += collect_submodules('src')
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('aiohttp')


a = Analysis(
    ['entry_point.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
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
    name='pypi-scanner',
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
