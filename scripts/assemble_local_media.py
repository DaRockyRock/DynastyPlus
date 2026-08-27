"""Assemble data/local_media.json from a local-media research workflow journal.

The fbs-local-media-research workflow (run via the Workflow tool) writes a
journal.jsonl of cached agent results, each a schema-validated
{"schools": [{team, orgs, writers}, ...]} for a batch of programs. This script
collapses that journal into the per-team dataset the app reads
(backend/local_media.py), keyed by the canonical league-seed team name.

It is safe to re-run: later results for the same team win (so a verify-stage
result supersedes the earlier research-stage one), and every string is run
through the project's sanitizer (no dash punctuation, no emojis).

Usage:
    python scripts/assemble_local_media.py [path/to/journal.jsonl]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import config  # noqa: E402
from backend.modules.base import sanitize  # noqa: E402
from backend.sim import league  # noqa: E402

_CONF_TOKENS = {
    "acc", "american", "big 12", "big ten", "conference usa", "fbs independents",
    "mac", "mountain west", "pac-12", "sec", "sun belt",
    "aac", "cusa", "c-usa", "independent", "independents",
}


def _norm(name: str) -> str:
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def _strip_conf_suffix(name: str) -> str:
    """Drop a trailing parenthetical that is just the conference, e.g.
    'Oregon Ducks (Big Ten)' -> 'Oregon Ducks'. Leaves real parentheticals that
    are part of the name (e.g. 'Miami (OH) RedHawks') untouched."""
    s = (name or "").strip()
    if s.endswith(")") and "(" in s:
        head, _, tail = s.rpartition("(")
        inside = tail[:-1].strip().lower()
        if inside in _CONF_TOKENS:
            return head.strip()
    return s


def _canonical_index() -> dict[str, str]:
    return {_norm(r["name"]): r["name"] for r in league.load_seed()}


def _clean_orgs(orgs: list) -> list:
    out = []
    for o in orgs or []:
        name = sanitize((o or {}).get("name") or "").strip()
        if not name:
            continue
        out.append({
            "name": name,
            "voice": sanitize(o.get("voice") or "").strip(),
            "reliability": int(o.get("reliability") or 78),
        })
    return out


def _clean_writers(writers: list) -> list:
    out = []
    for w in writers or []:
        name = sanitize((w or {}).get("name") or "").strip()
        if not name:
            continue
        out.append({
            "name": name,
            "outlet": sanitize(w.get("outlet") or "").strip(),
            "beat": (w.get("beat") or "program").strip().lower(),
            "reliability": int(w.get("reliability") or 80),
            "bio": sanitize(w.get("bio") or "").strip(),
        })
    return out


def assemble(journal_path: Path) -> dict:
    canon = _canonical_index()
    dataset: dict[str, dict] = {}
    unmatched: list[str] = []
    matched = set()

    with journal_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") != "result":
                continue
            for school in (rec.get("result") or {}).get("schools") or []:
                raw = _strip_conf_suffix(school.get("team") or "")
                key = canon.get(_norm(raw))
                if not key:
                    unmatched.append(raw)
                    continue
                # Later result wins (verify supersedes research).
                dataset[key] = {
                    "orgs": _clean_orgs(school.get("orgs")),
                    "writers": _clean_writers(school.get("writers")),
                }
                matched.add(key)

    missing = [r["name"] for r in league.load_seed() if r["name"] not in matched]
    return {"dataset": dataset, "unmatched": unmatched, "missing": missing}


def main() -> None:
    if len(sys.argv) > 1:
        journal = Path(sys.argv[1])
    else:
        raise SystemExit("usage: python scripts/assemble_local_media.py <journal.jsonl>")
    if not journal.exists():
        raise SystemExit(f"journal not found: {journal}")

    res = assemble(journal)
    out_path = config.DATA_DIR / "local_media.json"
    # Stable, readable, key-sorted output.
    ordered = {k: res["dataset"][k] for k in sorted(res["dataset"])}
    out_path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {len(ordered)} teams -> {out_path}")
    if res["unmatched"]:
        uniq = sorted(set(res["unmatched"]))
        print(f"UNMATCHED team names ({len(uniq)}): {uniq}")
    if res["missing"]:
        print(f"MISSING (no data) {len(res['missing'])}: {res['missing']}")


if __name__ == "__main__":
    main()
