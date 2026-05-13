# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Catchphrase.
#
# Build with:  python3 -m PyInstaller Catchphrase.spec --noconfirm
#
# Produces dist/Catchphrase.app on macOS and dist/Catchphrase/ on Linux/Windows.

import sys

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("static", "static"),
        ("main.py", "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "playwright", "pytest"],
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
    name="Catchphrase",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # No terminal window — pure GUI bundle
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Catchphrase",
)

# Build a proper .app bundle on macOS
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Catchphrase.app",
        icon=None,
        bundle_identifier="com.emelialei.catchphrase",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
            "NSHumanReadableCopyright": "© 2026 Emelia Lei",
        },
    )
