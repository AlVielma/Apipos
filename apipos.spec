# -*- mode: python ; coding: utf-8 -*-
# Windows build. Produces a single-file .exe:
#   pyinstaller apipos.spec
import os

_app_name = os.environ.get('APP_NAME', 'Apipos')

a = Analysis(
    ['apipos.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('./assets/app-icon.png', 'assets'),
        ('./assets/APIPOS.pdf', 'assets'),
    ],
    hiddenimports=['win32print', 'win32timezone'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['escpos'],  # macOS/Linux-only backend; not used on Windows
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
    name=_app_name,
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
    icon=['assets/app-icon.png'],
)
