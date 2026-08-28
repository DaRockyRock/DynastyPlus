#!/usr/bin/env python3
"""Build Dynasty+ Tools into a distributable Electron desktop app.

The pipeline is:

  1. icon      - render the D+ app icon (scripts/make_icon.py)
  2. frontend  - build the Tools frontend
  3. backend   - freeze the Flask server into a standalone exe (PyInstaller)
  4. shell     - install the Electron shell's npm deps (electron, builder)
  5. installer - package the Windows installer under dist-app/tools/

Usage:
  python scripts/build_app.py                 # full Tools pipeline
  python scripts/build_app.py --skip-frontend --skip-icon   # iterate faster
  python scripts/build_app.py --no-installers # build backend only, skip Electron

Prereqs: Python deps from requirements-build.txt (pyinstaller), Node/npm on PATH.
The frozen build serves the UI itself; game art still comes from the local CFB 27
install on the target machine (scripts/extract_game_assets.py), never shipped.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
ELECTRON = ROOT / "electron"
SPEC = ROOT / "packaging" / "dynastyplus-backend.spec"
BACKEND_DIST = ROOT / "dist-backend"

_NPM = "npm.cmd" if sys.platform == "win32" else "npm"


def _step(msg: str) -> None:
    print(f"\n{'=' * 64}\n== {msg}\n{'=' * 64}", flush=True)


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(str(c) for c in cmd)
    print(f"$ {printable}   (cwd={cwd or ROOT})", flush=True)
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def build_icon() -> None:
    _step("1/5  Rendering the D+ app icon")
    _run([sys.executable, str(ROOT / "scripts" / "make_icon.py")])


def build_frontend() -> None:
    _step("2/5  Building the Tools frontend")
    if not (FRONTEND / "node_modules").exists():
        _run([_NPM, "install"], cwd=FRONTEND)
    _run([_NPM, "run", "build"], cwd=FRONTEND)


def build_backend() -> None:
    _step("3/5  Freezing the backend (PyInstaller)")
    if not (FRONTEND / "dist").exists():
        raise SystemExit("missing frontend/dist: run without --skip-frontend first")
    if BACKEND_DIST.exists():
        shutil.rmtree(BACKEND_DIST)
    _run([
        sys.executable, "-m", "PyInstaller", str(SPEC),
        "--distpath", str(BACKEND_DIST),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--noconfirm",
    ])
    exe = BACKEND_DIST / "dynastyplus-backend" / "dynastyplus-backend.exe"
    if not exe.exists():
        raise SystemExit(f"backend build did not produce {exe}")
    print(f"backend exe: {exe}")


def smoke_test_backend() -> None:
    """Confirm the frozen Tools backend answers /api/config."""
    _step("3b   Smoke-testing the frozen backend")
    import json
    import os
    import socket
    import urllib.request

    def free_port() -> int:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    exe = BACKEND_DIST / "dynastyplus-backend" / "dynastyplus-backend.exe"
    port = free_port()
    env = {**os.environ, "CFBMOD_PORT": str(port)}
    proc = subprocess.Popen([str(exe)], env=env, cwd=str(exe.parent),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ok = False
        for _ in range(60):
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/config", timeout=1) as r:
                    data = json.loads(r.read())
                ok = data.get("app_name") == "Dynasty+ Tools"
                break
            except Exception:
                time.sleep(0.5)
        if not ok:
            raise SystemExit("frozen Tools backend failed health check")
        print(f"  /api/config OK (Dynasty+ Tools, port={port})")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def install_electron_deps() -> None:
    _step("4/5  Installing the Electron shell deps")
    if not (ELECTRON / "node_modules").exists():
        _run([_NPM, "install"], cwd=ELECTRON)
    else:
        print("electron/node_modules present, skipping npm install")


def build_installer() -> None:
    _step("5/5  Packaging the Tools installer with electron-builder")
    _run([_NPM, "run", "dist"], cwd=ELECTRON)
    out = ROOT / "dist-app"
    print(f"\nInstaller written under: {out / 'tools'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build Dynasty+ Tools.")
    ap.add_argument("--skip-icon", action="store_true")
    ap.add_argument("--skip-frontend", action="store_true")
    ap.add_argument("--skip-backend", action="store_true")
    ap.add_argument("--no-smoke-test", action="store_true",
                    help="skip launching the frozen backend to health-check it")
    ap.add_argument("--no-installers", action="store_true",
                    help="build the backend but stop before electron-builder")
    args = ap.parse_args()

    if not args.skip_icon:
        build_icon()
    if not args.skip_frontend:
        build_frontend()
    if not args.skip_backend:
        build_backend()
        if not args.no_smoke_test:
            smoke_test_backend()

    if args.no_installers:
        print("\n--no-installers: stopping after the backend build.")
        return

    install_electron_deps()
    build_installer()
    print("\nDone.")


if __name__ == "__main__":
    main()
