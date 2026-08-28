"""Extract the local game art used by Dynasty+ Tools.

Thin command-line wrapper over backend.assets.extract_art (the same code the
in-app "Set up game art" button runs). Reads the game's Frostbite image asset
library and writes PNGs under DATA_DIR/game_assets/ plus a manifest.json, which
both Flask apps serve at /game-assets/*.

The extracted art is EA/school trademarked: it stays on this machine (the output
dir is gitignored) and must not ship in a distributed build.

Usage:
    python scripts/extract_game_assets.py                 # everything
    python scripts/extract_game_assets.py --only teams    # one stage
    python scripts/extract_game_assets.py --game-root "D:\\Games\\College Football 27"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.assets import extract_art  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=extract_art.STAGES)
    ap.add_argument("--game-root", default=None,
                    help="CFB 27 install folder (defaults to the Steam location)")
    args = ap.parse_args()

    def progress(stage: str, done: int, total: int) -> None:
        if stage != "done":
            print(f"[{done + 1}/{total}] extracting {stage} ...", flush=True)

    summary = extract_art.run(game_root=args.game_root, only=args.only, progress=progress)
    print(
        f"\nDone. teams={summary['teams']} conferences={summary['conferences']} "
        f"fonts={summary['fonts']}")
    print(f"manifest -> {summary['manifest']}")


if __name__ == "__main__":
    main()
