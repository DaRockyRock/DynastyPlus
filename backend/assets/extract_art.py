"""Extract the team, conference, font, and UI art used by Dynasty+ Tools.

The orchestration behind both the command-line extractor
(scripts/extract_game_assets.py) and the in-app "Set up game art" button
(backend/app.py -> /api/setup/extract). Reads the game's Frostbite image asset
library (backend/assets/frostbite) and writes PNGs under
DATA_DIR/game_assets/ plus a manifest.json, which both Flask apps serve at
/game-assets/*.

Parameterized by the game install root (so a non-default install works) and an
optional progress callback (so the UI can show a per-stage progress bar). The
extracted art is EA/school trademarked: it stays on the user's machine (the
output dir is gitignored) and is never shipped in a build.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Callable

from .. import config
from .frostbite.extract import ImageLibrary
from .frostbite.gamefs import DEFAULT_GAME_ROOT

ProgressFn = Callable[[str, int, int], None]

# The extraction stages, in run order. Exposed so the UI can show total steps.
STAGES = ["teams", "conferences", "fonts", "ui"]

# game slug -> normalized substring of the league_seed team name, for names
# simple prefixing can't match
SLUG_OVERRIDES = {
    "connecticut": "uconn",
    "louisianamonroe": "ulmonroe",
    "umass": "massachusetts",
    "texasam": "texasam",
    "miami": "miamihurricanes",
    "miamiuniversity": "miamioh",
    "miamiohio": "miamioh",
    "sanjosestate": "sanjos",
    "appalachianstate": "appstate",
    "ecu": "eastcarolina",
    "usf": "southflorida",
    "fiu": "floridainternational",
    "midtennstate": "middletennessee",
    "samhoustonstate": "samhouston",
    "centralflorida": "ucf",
}

# Safety net for installs whose per-user league_seed.json predates the 2026
# FBS newcomers (a frozen build never overwrites an already-seeded copy).
# Both programs are full league-seed members now (MWC / MAC), so on a current
# seed these are duplicates map_teams ignores (each espn id is claimed once);
# on a stale seed they keep the logos extracting.
FCS_TEAMS = [
    {"name": "North Dakota State Bison", "espn_id": 2449},
    {"name": "Sacramento State Hornets", "espn_id": 16},
]

CONF_SLUGS = {
    "acc": "acc",
    "american": "american",
    "aac": "american",
    "big 12": "big12",
    "big ten": "bigten",
    "c-usa": "cusa",
    "conference usa": "cusa",
    "cusa": "cusa",
    "mac": "mac",
    "mountain west": "mwc",
    "mwc": "mwc",
    "pac-12": "pac12",
    "pac 12": "pac12",
    "sec": "sec",
    "sun belt": "sunbelt",
    "independent": "fbs",
    "fbs independents": "fbs",
}

TEAM_VARIANTS = {
    # output filename -> (asset name template, max size)
    "logo.png": ("teamlogos/teamlogosonwhite/assets/tlow_{slug}", 512),
    "logo-white.png": ("teamlogos/whiteteamlogos/assets/wtl_{slug}", 384),
    "logo-dark.png": ("teamlogos/teamlogos/assets/ncaa/tmlg_ncaa_primary_{slug}", 512),
    "secondary.png": ("teamlogossecondary/assets/tlsec_secondary_{slug}", 384),
    "helmet-left.png": ("teamhelmets/assets/lthelmets/thel_lthelmets_{slug}", 512),
    "helmet-right.png": ("teamhelmets/assets/rthelmets/thel_rthelmets_{slug}", 512),
    "mascot.png": ("teammascots/assets/tma_{slug}", 384),
}

UI_PACKS = [
    # (output subdir, name prefix filter, strip prefix, max size, square pad)
    ("ui/icons", "icons/assets/global/icon_global_", "icon_global_", 128, False),
    ("ui/states", "icons/assets/cfm/states/", "icon_cfm_states_", 128, False),
    ("ui/currency", "icons/assets/currency/", "icon_currency_", 96, False),
    ("ui/keys", "buttonicons/assets/win64/bti_win64_", "bti_win64_", 64, False),
    ("ui/activity", "dynastyicons/assets/activityicons/dynas_activityicons_", "dynas_activityicons_", 128, False),
    ("rivalries", "rivalrylogos/assets/256/rylgs_256_", "rylgs_256_", 256, True),
    ("bowls", "bowlgamelogos/assets/logos/bgl_logos_", "bgl_logos_", 256, True),
    ("bowls/championships", "bowlgamelogos/assets/conferencechampionship/bgl_conferencechampionship_",
     "bgl_conferencechampionship_", 256, True),
]


def _log(progress: ProgressFn | None, stage: str, done: int, total: int) -> None:
    if progress:
        progress(stage, done, total)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def trim(img, pad_ratio=0.04, square=True):
    from PIL import Image
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    pad = int(max(img.size) * pad_ratio)
    w, h = img.width + 2 * pad, img.height + 2 * pad
    if square:
        side = max(w, h)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    else:
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(img, (pad, pad), img)
    return canvas


def save(img, path: Path, max_size: int):
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((round(img.width * ratio), round(img.height * ratio)))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)


def map_teams(lib: ImageLibrary, teams: list) -> dict:
    """Return game slug -> team dict (greedy, longest slug first)."""
    slugs = sorted({n.split("tmlg_ncaa_primary_")[1] for n in lib.names()
                    if "tmlg_ncaa_primary_" in n}, key=len, reverse=True)
    claimed: set = set()
    mapping = {}
    for slug in slugs:
        key = SLUG_OVERRIDES.get(slug)
        if key:
            cand = [t for t in teams if key in norm(t["name"]) and t["espn_id"] not in claimed]
        else:
            cand = [t for t in teams if norm(t["name"]).startswith(slug) and t["espn_id"] not in claimed]
        if not cand:
            continue
        team = min(cand, key=lambda t: len(norm(t["name"])))
        mapping[slug] = team
        claimed.add(team["espn_id"])
    return mapping


def extract_teams(lib, teams, manifest, out: Path):
    mapping = map_teams(lib, teams)
    for slug, team in sorted(mapping.items()):
        entry = {"slug": slug, "name": team["name"], "files": {}}
        for fname, (tpl, max_size) in TEAM_VARIANTS.items():
            asset = tpl.format(slug=slug)
            if asset not in lib.by_name:
                continue
            try:
                img = trim(lib.image(asset), square="helmet" not in fname)
                save(img, out / "teams" / str(team["espn_id"]) / fname, max_size)
                entry["files"][fname] = True
            except Exception:  # noqa: BLE001
                pass
        manifest["teams"][str(team["espn_id"])] = entry


def extract_conferences(lib, manifest, out: Path):
    for key in sorted(set(CONF_SLUGS.values())):
        for suffix, out_name in (("", f"{key}.png"), ("white", f"{key}-white.png")):
            asset = f"teamconferences/assets/tcon_{key}{suffix}"
            if asset not in lib.by_name:
                continue
            save(trim(lib.image(asset)), out / "conferences" / out_name, 384)
        manifest["conferences"][key] = True
    extract_historic_conferences(lib, out)


# The game ships classic conference marks (shown in its history tab) for five
# conferences. Their asset token maps to our conference logo slug.
HISTORIC_CONF_SLUGS = {
    "big12": "big12", "bigten": "bigten", "conferenceusa": "cusa",
    "pac12": "pac12", "sec": "sec",
}
_HISTORIC_PREFIX = "teamconferences/assets/historiclogos/tcon_historiclogos_"


def extract_historic_conferences(lib, out: Path) -> list[str]:
    """Extract every historic conference mark to
    conferences/historic/<slug>_<tail>.png. Idempotent; returns the relative
    filenames written. Safe to call on its own (lazy extraction)."""
    written: list[str] = []
    for asset in lib.by_name:
        if not asset.startswith(_HISTORIC_PREFIX):
            continue
        rest = asset[len(_HISTORIC_PREFIX):]              # e.g. "sec_1988_2008"
        token, _, tail = rest.partition("_")
        slug = HISTORIC_CONF_SLUGS.get(token)
        if slug is None:
            continue
        name = f"{slug}_{tail}.png" if tail else f"{slug}.png"
        try:
            save(trim(lib.image(asset)), out / "conferences" / "historic" / name, 384)
            written.append(name)
        except Exception:  # noqa: BLE001 - one bad asset never kills the batch
            continue
    return written


def extract_ui(lib, manifest, out: Path):
    for subdir, prefix, strip, max_size, square in UI_PACKS:
        count = 0
        for name in lib.names():
            if prefix not in name:
                continue
            short = name.rsplit("/", 1)[-1]
            if strip in short:
                short = short.split(strip, 1)[1]
            try:
                img = lib.image(name)
                img = trim(img, square=square) if square else img
                save(img, out / subdir / f"{short}.png", max_size)
                count += 1
            except Exception:  # noqa: BLE001
                pass
        manifest.setdefault("ui", {})[subdir] = count


def extract_fonts(game_root, manifest, out: Path):
    from .frostbite import bundle as bundle_mod
    from .frostbite import superbundle, toc
    from .frostbite.cas import CasReader
    from .frostbite.gamefs import GameFS

    fs = GameFS(game_root)
    reader = CasReader(fs)
    payload = toc.read_payload(fs.toc_path("Win32/ui"))
    sb = superbundle.parse(payload)
    ref = next(b for b in sb.bundles if "rimefontconfig" in b.name)
    b = bundle_mod.parse_bundle(payload, ref.offset, ref.size, read_cas=reader.read_raw)
    out_dir = out / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for res in b.res:
        if res.res_type != 0x063994C5:  # font resource
            continue
        data = reader.read(res.cas)
        ext = "otf" if data[:4] == b"OTTO" else "ttf"
        name = res.name.rsplit("/", 1)[-1]
        (out_dir / f"{name}.{ext}").write_bytes(data)
        manifest["fonts"][name] = ext


def _load_seed_teams() -> list:
    teams = json.loads((config.DATA_DIR / "league_seed.json").read_text(encoding="utf-8"))
    if isinstance(teams, dict):
        teams = teams["teams"]
    return teams


def run(game_root: str | Path | None = None, out: str | Path | None = None,
        stages: list[str] | None = None, only: str | None = None,
        progress: ProgressFn | None = None) -> dict:
    """Run the extraction. Returns a summary dict (per-category counts).

    game_root: the CFB 27 install folder (defaults to the Steam location).
    out:       output dir (defaults to DATA_DIR/game_assets).
    stages:    which Tools stages to run (subset of STAGES), or None for all.
    only:      run a single stage (convenience for the CLI); overrides `stages`.
    progress:  callback(stage, done_stages, total_stages) for a UI progress bar.
    """
    game_root = Path(game_root) if game_root else Path(DEFAULT_GAME_ROOT)
    out = Path(out) if out else (config.DATA_DIR / "game_assets")
    out.mkdir(parents=True, exist_ok=True)

    lib = ImageLibrary(game_root)
    teams = _load_seed_teams()

    manifest_path = out / "manifest.json"
    manifest = {"teams": {}, "conferences": {}, "fonts": {}}
    if manifest_path.exists():
        try:
            manifest.update(json.loads(manifest_path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    manifest.setdefault("fonts", {})

    if only:
        stages = [only]
    elif stages is None:
        stages = STAGES
    # Keep the requested stages in canonical order and drop anything unknown.
    stages = [s for s in STAGES if s in set(stages)]
    total = len(stages)
    for i, stage in enumerate(stages):
        _log(progress, stage, i, total)
        if stage == "teams":
            extract_teams(lib, teams + FCS_TEAMS, manifest, out)
        elif stage == "conferences":
            extract_conferences(lib, manifest, out)
        elif stage == "fonts":
            extract_fonts(game_root, manifest, out)
        elif stage == "ui":
            extract_ui(lib, manifest, out)

    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    _log(progress, "done", total, total)

    return {
        "teams": len(manifest.get("teams", {})),
        "conferences": len(manifest.get("conferences", {})),
        "fonts": len(manifest.get("fonts", {})),
        "manifest": str(manifest_path),
    }
