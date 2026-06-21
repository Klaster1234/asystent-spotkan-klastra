# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for "Asystent Spotkan Klastra".
# One-folder, windowed build. The Whisper engine (bin/) and model (models/)
# are NOT bundled here - the Inno Setup installer lays them down next to the
# resulting .exe. Only the UI assets are embedded.
#
# Build:  pyinstaller installer/AsystentSpotkan.spec --noconfirm
import os
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

datas = []
binaries = []
hiddenimports = ["clr", "_cffi_backend"]

# Pull data files + native DLLs for the WebView2 backend and the mic recorder.
# "_sounddevice_data" carries the PortAudio DLL the recorder loads at import time;
# collecting it explicitly means the build does not silently depend on the
# pyinstaller-hooks-contrib sounddevice hook being present.
for pkg in ("webview", "sounddevice", "_sounddevice_data", "clr_loader", "pythonnet"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# Embed the UI graphics (logo, mascot, icons).
datas += [(os.path.join(ROOT, "assets"), "assets")]

a = Analysis(
    [os.path.join(ROOT, "AsystentSpotkan.pyw")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "numpy", "matplotlib", "PIL"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AsystentSpotkan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "assets", "klaster.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AsystentSpotkan",
)
