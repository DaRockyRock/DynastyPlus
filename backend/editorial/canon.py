"""The Entity Canon: the single source of truth for who/what exists.

Every team, coach, player, and recruit in the universe is registered here with
canonical attributes (position, stars, team, tenure, seat) and aliases. Briefs
draw their cast list from it (step 3), and the validator rejects any generated
text that contradicts it: a recruit who is a 4-star CB cannot be written up as a
5-star WR, and a real-life coach (or a fabricated one) cannot be attributed to a
team whose coach is canonical. Built fresh from the save each tick (cheap), per
the repo rule that game data flows only through the save.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    id: str
    kind: str                       # team | coach | player | recruit
    name: str
    attrs: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)


def norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()


# Position synonym groups: the validator compares GROUPS, not raw tokens, so a CB
# written up as "defensive back" or "cornerback" is NOT a mismatch (only a real
# position change, e.g. CB -> WR, is). Tokens are matched longest-first.
_POS_GROUPS: dict[str, set[str]] = {
    "QB": {"qb", "quarterback", "signal caller", "passer"},
    "RB": {"rb", "running back", "tailback", "halfback", "rusher"},
    "WR": {"wr", "wide receiver", "receiver", "wideout", "pass catcher"},
    "TE": {"te", "tight end"},
    "OL": {"ol", "ot", "og", "iol", "c", "g", "t", "offensive line", "offensive lineman",
           "lineman", "tackle", "guard", "center", "blocker"},
    "DL": {"dl", "dt", "de", "defensive line", "defensive lineman", "defensive tackle",
           "nose tackle", "nose"},
    "EDGE": {"edge", "edge rusher", "pass rusher", "defensive end"},
    "LB": {"lb", "ilb", "olb", "linebacker", "mike", "will", "sam"},
    "DB": {"db", "cb", "s", "fs", "ss", "nb", "cornerback", "corner", "safety",
           "defensive back", "nickel", "nickelback"},
    "ST": {"k", "p", "ls", "kicker", "punter", "long snapper", "specialist", "athlete", "ath"},
}
_POS_LOOKUP: dict[str, str] = {tok: grp for grp, toks in _POS_GROUPS.items() for tok in toks}
_POS_TOKENS = sorted(_POS_LOOKUP, key=len, reverse=True)


def position_group(token: str) -> str | None:
    """Resolve a free-text position phrase to its group, or None if unrecognized
    (unrecognized -> the validator does not flag, to avoid false positives)."""
    t = norm(token)
    if t in _POS_LOOKUP:
        return _POS_LOOKUP[t]
    for tok in _POS_TOKENS:                 # phrase containment ("star defensive back")
        if re.search(rf"\b{re.escape(tok)}\b", t):
            return _POS_LOOKUP[tok]
    return None


class Canon:
    def __init__(self) -> None:
        self.teams: dict[str, Entity] = {}
        self.people: dict[str, Entity] = {}      # norm(name) -> Entity
        self.coach_names: set[str] = set()        # norm names of all known coaches
        self.user_team: str | None = None
        self.user_coach: str | None = None

    # --- lookups ---
    def find_person(self, name: str) -> Entity | None:
        return self.people.get(norm(name))

    def is_known_coach(self, name: str) -> bool:
        return norm(name) in self.coach_names

    def cast_for_scope(self, scope: str, dynasty: dict) -> list[Entity]:
        """The entities a brief in this scope may name (step 3 uses this; the
        validator uses the person/coach indexes directly)."""
        if scope == "program":
            out = [e for e in self.people.values()
                   if e.attrs.get("team") in (self.user_team, None) or e.kind == "recruit"]
            return out
        return [e for e in self.teams.values()]


def _add_person(c: Canon, ent: Entity) -> None:
    c.people.setdefault(norm(ent.name), ent)


def build(dynasty: dict) -> Canon:
    c = Canon()
    team = dynasty.get("team") or {}
    c.user_team = team.get("name")
    hc = team.get("head_coach") or {}
    c.user_coach = hc.get("name")

    # teams + their coaches from the league directory
    for tname, cc in (dynasty.get("coaches") or {}).items():
        if not isinstance(cc, dict):
            continue
        nick = (tname or "").split()[-1] if tname else ""
        c.teams[tname] = Entity(id=f"team:{norm(tname)}", kind="team", name=tname,
                                attrs={"conference": cc.get("conference"), "abbr": cc.get("abbr"),
                                       "prestige": cc.get("prestige")},
                                aliases=[a for a in (cc.get("abbr"), nick) if a])
        if cc.get("name"):
            c.coach_names.add(norm(cc["name"]))
            _add_person(c, Entity(id=f"coach:{norm(cc['name'])}", kind="coach", name=cc["name"],
                                  attrs={"team": tname, "tenure": cc.get("tenure_years"),
                                         "seat": cc.get("hot_seat"), "is_user": bool(cc.get("is_user"))}))
    # the user's coach (and team if the directory omitted it)
    if c.user_coach:
        c.coach_names.add(norm(c.user_coach))
        _add_person(c, Entity(id=f"coach:{norm(c.user_coach)}", kind="coach", name=c.user_coach,
                              attrs={"team": c.user_team, "tenure": hc.get("tenure_years"),
                                     "seat": hc.get("hot_seat"), "is_user": True}))
    # rivals' + the next opponent's coaches (named in previews)
    for r in dynasty.get("rivals") or []:
        if isinstance(r, dict) and r.get("coach"):
            c.coach_names.add(norm(r["coach"]))
    up = (dynasty.get("schedule") or {}).get("upcoming") or {}
    if up.get("opponent_coach"):
        c.coach_names.add(norm(up["opponent_coach"]))

    # the user's roster
    for p in (team and (dynasty.get("roster") or {}).get("key_players")) or []:
        if isinstance(p, dict) and p.get("name"):
            _add_person(c, Entity(id=f"player:{norm(p['name'])}", kind="player", name=p["name"],
                                  attrs={"team": c.user_team, "position": p.get("position"),
                                         "ovr": p.get("rating")}))
    # national players who appear in coverage (Heisman / stat leaders)
    nat = dynasty.get("national") or {}
    for h in nat.get("heisman_frontrunners") or []:
        if isinstance(h, dict) and h.get("name"):
            _add_person(c, Entity(id=f"player:{norm(h['name'])}", kind="player", name=h["name"],
                                  attrs={"team": h.get("team"), "position": h.get("position")}))
    for key in ("passing", "rushing", "receiving", "sacks"):
        for p in (nat.get("stat_leaders") or {}).get(key) or []:
            if isinstance(p, dict) and p.get("name"):
                _add_person(c, Entity(id=f"player:{norm(p['name'])}", kind="player", name=p["name"],
                                      attrs={"team": p.get("team"), "position": p.get("position")}))
    # recruits (targets + commits)
    rec = dynasty.get("recruiting") or {}
    for grp in ("targets", "commits"):
        for t in rec.get(grp) or []:
            if isinstance(t, dict) and t.get("name"):
                _add_person(c, Entity(id=f"recruit:{norm(t['name'])}", kind="recruit", name=t["name"],
                                      attrs={"position": t.get("position"), "stars": t.get("stars"),
                                             "committed": grp == "commits", "leader": t.get("leader")}))
    return c
