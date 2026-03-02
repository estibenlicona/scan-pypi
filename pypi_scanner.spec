# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PyPI Scanner.

Generates a standalone executable with all dependencies bundled.
Build command:
    pyinstaller pypi_scanner.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all src submodules to ensure nothing is missed
src_hiddenimports = collect_submodules("src")

# Additional hidden imports that PyInstaller may not detect
extra_hiddenimports = [
    # aiohttp and its C extensions
    "aiohttp",
    "aiohttp.web",
    "aiohttp.client",
    "aiohttp.connector",
    "aiohttp.typedefs",
    "aiohttp._http_parser",
    "aiohttp._http_writer",
    "aiohttp._websocket",
    # multidict / yarl (aiohttp deps with C extensions)
    "multidict",
    "multidict._multidict",
    "yarl",
    "yarl._quoting",
    # async support
    "aiofiles",
    "asyncio",
    "asyncio.events",
    "asyncio.base_events",
    # pydantic v2
    "pydantic",
    "pydantic.deprecated",
    "pydantic._internal",
    "pydantic_core",
    "annotated_types",

    # requests
    "requests",
    "urllib3",
    "certifi",
    "charset_normalizer",
    "idna",
    # openpyxl
    "openpyxl",
    "openpyxl.workbook",
    "openpyxl.styles",
    "openpyxl.utils",
    "openpyxl.cell",
    "openpyxl.writer",
    "openpyxl.writer.excel",
    "et_xmlfile",
    # dotenv
    "dotenv",
    # pipgrip (fallback resolver)
    "pipgrip",
    # email/encodings (commonly missed)
    "email.mime.text",
    "email.mime.multipart",
    "encodings",
    "encodings.utf_8",
    "encodings.ascii",
    "encodings.latin_1",
    "encodings.cp1252",
    # json
    "json",
    # typing extensions
    "typing_extensions",
]

all_hiddenimports = src_hiddenimports + extra_hiddenimports

# Collect data files from packages that need them
datas = []

# Include certifi CA bundle (needed for HTTPS requests)
try:
    import certifi
    datas.append((certifi.where(), "certifi"))
except ImportError:
    pass

# Include .env.example as reference
if os.path.exists(".env.example"):
    datas.append((".env.example", "."))


a = Analysis(
    ["entry_point.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude dev/test dependencies to reduce size
        "pytest",
        "pytest_asyncio",
        "mypy",
        "setuptools",
        "pip",
        "wheel",
        "_pytest",
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pypi-scanner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pypi-scanner",
)
