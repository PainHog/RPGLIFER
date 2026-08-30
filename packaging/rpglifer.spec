# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for RPG Lifer.

Produces a single self-contained executable (``dist/RPGLifer.exe`` on Windows).
Build from the repository root:

    pyinstaller --noconfirm --clean packaging/rpglifer.spec

``SPECPATH`` is injected by PyInstaller and points at this file's directory
(``packaging/``); the repo root is its parent. Building against ``run.py`` (a
plain top-level script) keeps PyInstaller's import analysis simple.
"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.dirname(SPECPATH)  # noqa: F821 - SPECPATH is provided by PyInstaller

# CustomTkinter ships theme JSON and assets that must be bundled, plus its
# submodules need to be collected so PyInstaller doesn't miss them.
ctk_datas = collect_data_files("customtkinter")
ctk_hidden = collect_submodules("customtkinter")

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    binaries=[],
    # Bundle the activity catalog so the frozen app can find it at runtime
    # (activities.py looks under sys._MEIPASS/rpglifer/data first).
    datas=[(os.path.join(ROOT, "rpglifer", "data", "activities.json"),
            "rpglifer/data")] + ctk_datas,
    hiddenimports=["tkinter", "darkdetect"] + ctk_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RPGLifer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # don't depend on UPX being installed on the build machine
    runtime_tmpdir=None,
    console=False,  # windowed GUI app: no console window on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: add packaging/rpglifer.ico for a custom icon
)
