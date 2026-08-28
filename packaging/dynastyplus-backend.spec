# PyInstaller spec for the Dynasty+ backend.
#
# Freezes the Flask companion server (run.py) into a standalone one-folder
# executable so the Electron shell can launch it with no Python on the target
# machine. It serves the single Tools frontend and API.
#
# Build via scripts/build_app.py (which sets --distpath dist-backend), or by hand:
#   pyinstaller packaging/dynastyplus-backend.spec --distpath dist-backend \
#       --workpath build/pyinstaller --noconfirm
import os

ROOT = os.path.dirname(SPECPATH)  # packaging/ -> repo root

# The Tools frontend and checked-in league seed. config._seed_bundled_data()
# copies the seed into the per-user DATA_DIR on first run.
datas = [
    (os.path.join(ROOT, "frontend", "dist"), "frontend/dist"),
    (os.path.join(ROOT, "data", "league_seed.json"), "data"),
]

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    # The in-app "Set up game art" button (POST /api/setup/extract) imports the
    # extractor lazily, so its chain and heavy texture-decode deps must be named
    # explicitly to be bundled (static analysis can't see a lazy import).
    hiddenimports=[
        "backend.assets.extract_art",
        "backend.assets.frostbite.extract",
        "backend.assets.frostbite.texture",
        "backend.assets.frostbite.bc7enc",
        "backend.assets.frostbite.cas",
        "backend.assets.frostbite.bundle",
        "backend.assets.frostbite.superbundle",
        "numpy",
        "texture2ddecoder",
        "zstandard",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "pytest"],
    noarchive=False,
)

# Keep numpy's bundled OpenBLAS library. It is tempting to drop it (~20 MB) since
# the art/logo pipeline only does element-wise array and bit operations and never
# touches numpy.linalg, but on numpy 2.x for Windows the vendored OpenBLAS DLL is
# a LOAD-TIME dependency of the core extension (numpy/_core/_multiarray_umath.pyd
# imports it, and numpy/__config__.py imports from that module during
# `import numpy`). Removing it makes every `import numpy` fail in the frozen build
# with the misleading "you should not try to import numpy from its source
# directory" ImportError, which surfaced in the logo-mod path on the Conferences
# tab. Never filter it out.

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="dynastyplus-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,          # hidden by Electron (windowsHide); visible if run directly
    icon=os.path.join(ROOT, "electron", "build", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="dynastyplus-backend",
)
