# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path


PYTHON_TCL_DIR = Path(sys.base_prefix) / 'tcl'

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('..\\WB+SNV2\\HisenseLogo.png', '.'),
        (str(PYTHON_TCL_DIR / 'tcl8.6'), 'tcl\\tcl8.6'),
        (str(PYTHON_TCL_DIR / 'tk8.6'), 'tcl\\tk8.6'),
    ],
    hiddenimports=['tkinter', 'tkinter.ttk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='TCP Client Hisense',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
