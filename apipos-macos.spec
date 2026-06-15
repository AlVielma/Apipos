# -*- mode: python ; coding: utf-8 -*-
# macOS build. Produces a .app bundle:
#   pyinstaller apipos-macos.spec

a = Analysis(
    ['apipos.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('./assets/app-icon.png', 'assets'),
        ('./assets/APIPOS.pdf', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['win32print'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Apipos',
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

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Apipos',
)

app = BUNDLE(
    coll,
    name='Apipos.app',
    icon='assets/app-icon.png',
    bundle_identifier='mx.tecsom.apipos',
    info_plist={
        'LSUIElement': True,  # menu-bar / tray app, no Dock icon
        'NSHighResolutionCapable': True,
    },
)
