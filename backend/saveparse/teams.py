"""Team identity extraction from the FrTk payload.

The team table is a contiguous array of fixed-size records (503-byte stride),
one per team, each keyed by a `teamdb_<slug>` string. The identity fields sit at
fixed byte offsets relative to that key (verified across teams):

    key - 227   school name        "Alabama",  "Appalachian State"
    key - 204   abbreviation       "ALA", "APP" (standard TV abbr; blank for some teams)
    key - 146   nickname           "Crimson Tide", "Mountaineers"
    key -  77   brand code         "BAMA", "MICH", "FSU" (present for all; abbr fallback)
    key +   0   teamdb_ key        "teamdb_bama", "teamdb_app"

The standard abbreviation slot (-204) is blank for a handful of teams (Michigan,
Florida State, ...), so we fall back to the brand code (-77). The first key,
`teamdb_practice`, is a placeholder scrimmage team and is skipped. Only identity
is here; ratings/colors/logo-refs are other (binary) fields in the same record
and are not decoded yet.
"""
from __future__ import annotations

from dataclasses import dataclass

RECORD_STRIDE = 503
_KEY = b"teamdb_"
_OFF_SCHOOL = -227
_OFF_ABBR = -204
_OFF_ABBR_ALT = -77
_OFF_NICK = -146
_SKIP_SLUGS = {"practice"}


@dataclass(frozen=True)
class Team:
    slug: str          # stable game key, e.g. "bama"
    school: str        # "Alabama"
    nickname: str      # "Crimson Tide"
    abbreviation: str  # "ALA"

    @property
    def name(self) -> str:
        """Full name for the schema, e.g. 'Alabama Crimson Tide'."""
        return f"{self.school} {self.nickname}".strip()

    def to_schema(self) -> dict[str, str]:
        return {
            "name": self.name,
            "school": self.school,
            "nickname": self.nickname,
            "abbreviation": self.abbreviation,
            "slug": self.slug,
        }


def _cstr(payload: bytes, off: int, limit: int = 64) -> str:
    if off < 0 or off >= len(payload):
        return ""
    end = payload.find(b"\x00", off, off + limit)
    if end == -1:
        end = off + limit
    return payload[off:end].decode("latin1", "replace").strip()


def _key_offsets(payload: bytes) -> list[int]:
    offs: list[int] = []
    start = 0
    while True:
        i = payload.find(_KEY, start)
        if i == -1:
            break
        offs.append(i)
        start = i + 1
    return offs


def parse_teams(payload: bytes) -> list[Team]:
    """Extract every real team's identity from the FrTk payload."""
    teams: list[Team] = []
    for off in _key_offsets(payload):
        slug = _cstr(payload, off)[len("teamdb_"):]
        if not slug or slug in _SKIP_SLUGS:
            continue
        school = _cstr(payload, off + _OFF_SCHOOL)
        abbr = _cstr(payload, off + _OFF_ABBR) or _cstr(payload, off + _OFF_ABBR_ALT)
        nick = _cstr(payload, off + _OFF_NICK)
        if not school:
            continue
        teams.append(Team(slug=slug, school=school, nickname=nick, abbreviation=abbr))
    return teams
