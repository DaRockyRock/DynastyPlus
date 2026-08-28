"""A faithful CFB27 engine emulator + harness for exercising the full custom
playoff loop (playoff_live.sync) without the game.

It models the reverse-engineered rules that the live playoff automation depends
on (see docs/custom-playoff-automation.md and the save-format research in
backend/saveparse/schedule.py):

  * The current week's SLATE is the SeasonGameRequest queue
    (schedule.week_slate). A matchup written into a PRE-LOCK slate record is
    adopted by the engine on load as if it had scheduled it.
  * On LOAD the engine LOCKS the week: every scheduled, result-less slate
    record is pre-simmed (byte 97 bit 0x10, distinct packed scores) and, once
    the user advances, marked OFFICIAL (bit 0x01). A record already official is
    left alone (already played). The app can ONLY obtain results from a load;
    it never sims.
  * The USER's own game is the one they play; the emulator writes the
    scenario's chosen result there (win until their elimination round, then a
    loss, or wins all the way to a title) while every other game gets a fresh,
    globally-distinct score.

The harness redirects the four things sync() reads (save payload, save table,
dynasty pointer, dynasty dict) at a throwaway copy of a real bowl-week-1 base
save plus a synthetic dynasty whose poll ranks that save's real teams, and
redirects the playoff state files to a temp dir, so nothing touches a real
dynasty. Requires a base save fixture (env CFBMOD_TEST_BASE_SAVE); tests that
use it skip when absent.
"""
import json
import os
import shutil
import struct
import tempfile
from pathlib import Path

from backend import confsetup, pipeline, playoff, playoff_live
from backend.saveparse import (container, schedule as savesched,
                               teams as saveteams, conferences as savestruct)


def base_save_path():
    """The base save fixture, or None to skip. A real bowl-week-1 arrival
    autosave (a cycle_base.sav works): pre-lock, full FBS roster, a 28-record
    postseason slate."""
    p = os.environ.get("CFBMOD_TEST_BASE_SAVE")
    return Path(p) if p and Path(p).exists() else None


def _put_bits(buf, base, off, width, val):
    for i in range(width):
        b = off + i
        idx = base + (b >> 3)
        bit = (val >> (width - 1 - i)) & 1
        buf[idx] = (buf[idx] & ~(1 << (7 - (b & 7)))) | (bit << (7 - (b & 7)))


class Engine:
    """Emulates one LOAD of the dynasty at the current (anchor) week.

    `dead_records` models the real engine DECLINING to run a slate record
    (observed in-game 2026-07-10: two records never simmed across many
    reloads). A dead record is never simmed; instead it is aged straight to
    OFFICIAL-with-no-result, the state a skipped game reaches once the user
    advances the week, which is what the app's unmap/quarantine keys on."""

    def __init__(self, save_path):
        self.save_path = str(save_path)
        self.tick = 40  # globally-distinct score source
        self.user_games = 0
        self.dead_records: set[int] = set()
        self.week = 1  # bowl week the slate currently points at (native mode)
        self._week_records: dict[int, list[int]] | None = None

    def _next_scores(self):
        # INJECTIVE tick -> pair: the old (tick % 30, tick*7 % 25) recipe
        # repeated with period 150, so a long run (64+ teams, many presims per
        # load) could hand two DIFFERENT games the same pair and trip the
        # frozen-replay detector on a false positive. Disjoint ranges also
        # guarantee no ties and no collision with the user-game generator
        # (whose scores stay below 74).
        self.tick += 1
        return 21 + (self.tick % 53), 74 + ((self.tick // 53) % 50)

    def load(self, user_row=None, user_result=None, official=True):
        # official=True models the app's normal observation point (the user
        # loaded, played/simmed, and ADVANCED: results are published).
        # official=False models a world the user merely LOADED and exited:
        # the week is locked and pre-simmed (byte 97 bit 0x10, result slots
        # allocated) but nothing is official yet, the exact shape of the
        # post-lock autosave the reported stuck run anchored on (2026-07-12).
        raw = open(self.save_path, "rb").read()
        payload = bytearray(container.decode(raw).payload)
        store = savesched.parse(bytes(payload))
        base0 = store.records_off
        next_id = 0x8000_5000
        simmed = 0
        for r in savesched.week_slate(bytes(payload)):
            g = store.games[r]
            if g.official or not g.scheduled or g.has_result:
                continue
            base = base0 + r * savesched.RECORD_SIZE
            if r in self.dead_records:
                # the engine declines this record: no lock, no sim; the user
                # advancing the week ages it to official-with-no-result
                if official:
                    payload[base + 97] |= 0x01
                continue
            for off in (52, 60):
                if struct.unpack_from(">I", payload, base + off)[0] >> 24 != 0x80:
                    struct.pack_into(">I", payload, base + off, next_id)
                    next_id += 1
            struct.pack_into(">I", payload, base + 56, 0x80000000)
            user_in = user_row is not None and user_row in (g.away_row, g.home_row)
            if user_in and user_result:
                # a distinct win/loss each round (fresh scores, clear margin):
                # winner always strictly outscores loser, but the numbers move
                # so a per-wave replay would still be detectable.
                self.tick += 1
                self.user_games += 1
                win = user_result == "win"
                # Key off the user's game count, not the global CPU sim tick.
                # Modular tick formulas can collide in a 128-team run even
                # though every game really ran, producing a false frozen-wave
                # failure. Both values stay below the CPU score band's 74+
                # away score, so user and CPU pairs are disjoint too.
                winner = 40 + self.user_games
                loser = 10 + self.user_games
                user_home = g.home_row == user_row
                home = winner if (user_home == win) else loser
                away = loser if (user_home == win) else winner
            else:
                home, away = self._next_scores()
            _put_bits(payload, base, 609, 7, home)
            _put_bits(payload, base, 617, 7, away)
            payload[base + 97] |= 0x11 if official else 0x10
            simmed += 1
        open(self.save_path, "wb").write(container.encode(raw, bytes(payload)))
        return simmed

    # -- the week-advance boundary (native-mode weeks) ---------------------

    def _weeks(self, payload):
        """Bowl-week -> record indices. Week 1 is the fixture's own slate
        (first round + early bowls); week 2 the stock quarterfinals plus
        every remaining bowl; weeks 3/4 the semifinals / championship."""
        if self._week_records is not None:
            return self._week_records
        store = savesched.parse(payload)
        slots = playoff_live._postseason_slots(payload)
        week1 = list(savesched.week_slate(payload))
        stock = {r for v in slots.values() for r in v}
        others = [g.index for g in store.games
                  if g.bowl_row is not None and g.index not in stock
                  and g.index not in week1]
        self._week_records = {
            1: week1,
            2: list(slots["quarterfinal"]) + others,
            3: list(slots["semifinal"]),
            4: list(slots["championship"]),
        }
        return self._week_records

    def advance_week(self):
        """The week-advance BOUNDARY, the adversarial part of the real
        engine that sank the old calendar-tail design: it points the request
        queue at the next bowl week's records and ADVANCES its own bracket
        into that week's stock records by filling their TBD slots from the
        prior round's winners (byes already penciled in a record's home slot
        stay put), then allocates each record's participant-request pair, producing
        the pre-lock arrival shape the app's native mode writes onto.

        Faithful to the engine, it never invents a participant: the QF is
        the 4 first-round winners plus the 4 byes, the SF the 4 QF winners,
        and so on, so no team is ever in two of the week's games (the engine
        assigns each team a single postseason destination and pulls its
        bracket teams out of the regular bowls)."""
        raw = open(self.save_path, "rb").read()
        payload = bytearray(container.decode(raw).payload)
        weeks = self._weeks(bytes(payload))
        self.week += 1
        if self.week not in weeks:
            # After the national championship CFB has no next bowl week, so
            # it empties SeasonGameRequest while leaving the official title
            # record in SeasonGameStore. This is the exact completion-boundary
            # shape the live sync must capture without resetting its bracket.
            self._retarget_queue(payload, [])
            open(self.save_path, "wb").write(
                container.encode(raw, bytes(payload)))
            return []
        store = savesched.parse(bytes(payload))
        slots = playoff_live._postseason_slots(bytes(payload))
        kind = {2: "quarterfinal", 3: "semifinal", 4: "championship"}[self.week]
        prev_kind = {2: "first_round", 3: "quarterfinal",
                     4: "semifinal"}[self.week]
        winners = [store.games[r].winner_row for r in slots[prev_kind]
                   if store.games[r].winner_row is not None]
        target = slots.get(kind) or []
        # teams already penciled into this round (byes): never re-place them
        placed = {t for r in target for t in
                  (store.games[r].away_row, store.games[r].home_row)
                  if t is not None}
        feed = [w for w in winners if w not in placed]
        fi = 0
        for r in target:
            g = store.games[r]
            if g.official:
                continue
            away, home = g.away_row, g.home_row
            if home is None and fi < len(feed):
                home = feed[fi]; fi += 1
            if away is None and fi < len(feed):
                away = feed[fi]; fi += 1
            if (away, home) != (g.away_row, g.home_row):
                savesched.clear_engine_state(payload, g)
                savesched.set_matchup(payload, g, away_row=away, home_row=home)
        # The boundary allocates one participant request per team. A native
        # bye record with only one team therefore receives only one object.
        # Adding its opponent after arrival makes a game that can launch but
        # cannot publish a result, the real SMU quarterfinal failure. The app
        # must pre-stage both teams before this point.
        store = savesched.parse(bytes(payload))
        recs = [r for r in weeks[self.week] if not store.games[r].official]
        next_id = 0x8000_7000 + self.week * 0x100
        for r in recs:
            base = store.records_off + r * savesched.RECORD_SIZE
            game = store.games[r]
            for off, participant in ((52, game.away_row),
                                     (60, game.home_row)):
                if participant is None:
                    continue
                cur = struct.unpack_from(">I", payload, base + off)[0]
                if cur >> 24 != 0x80:
                    struct.pack_into(">I", payload, base + off, next_id)
                    next_id += 1
            struct.pack_into(">I", payload, base + 56, 0x80000000)
        self._retarget_queue(payload, recs)
        open(self.save_path, "wb").write(container.encode(raw, bytes(payload)))
        return recs

    def _retarget_queue(self, payload, recs):
        """Point the SeasonGameRequest queue at the given records: two
        CPU-typed rows per game (the shape set_user_pending expects), extra
        rows dropped from pair detection by zeroing their game-ref word."""
        from backend.saveparse import bowls as savebowls
        rec0, stride, count, _ = savebowls._find_store(
            bytes(payload), b"SeasonGameRequest")
        words_n = stride // 4
        handle = 0x22000000 + self.week * 0x10000
        for i in range(count):
            base = rec0 + i * stride
            gpos = 32
            for j in range(words_n):
                v = struct.unpack_from(">I", payload, base + j * 4)[0]
                if (v >> 16) == savesched.GAME_REF:
                    gpos = j * 4
                    break
            gi = i // 2
            if gi < len(recs):
                struct.pack_into(">I", payload, base + gpos,
                                 (savesched.GAME_REF << 16) | recs[gi])
                struct.pack_into(">I", payload, base + 4, handle + i)
                struct.pack_into(">I", payload, base + 16, 0)
                struct.pack_into(">I", payload, base + 28, handle + i)
                struct.pack_into(">I", payload, base + 40, savesched.NO_RESULT)
                struct.pack_into(">I", payload, base + 48, handle + 0x8000 + i)
                struct.pack_into(">I", payload, base + 56, 0x09000000)
            else:
                struct.pack_into(">I", payload, base + gpos, 0)


def _fmt(teams, byes=None, reseed=False):
    f = {"teams": teams, "byes": byes or [], "bye_selection": "seeding",
         "auto_bids": {"champions": 0}, "disqualify": {}, "notre_dame_rule": False,
         "reseed": reseed,
         "sites": {"rounds": [], "championship": {"venue": "Neutral", "city": "City"}}}
    return playoff.normalize_format(f)


def _synth_dynasty(roster, user_name, user_rank, year=2026):
    names = [t.name for t in roster]
    names = [n for n in names if n != user_name]
    names.insert(min(user_rank - 1, len(names)), user_name)
    poll = [{"rank": i + 1, "team": n, "abbr": n[:4].upper(), "espn_id": 2000 + i,
             "record": "12-1", "conference": "Test"} for i, n in enumerate(names)]
    uid = next(p["espn_id"] for p in poll if p["team"] == user_name)
    return {"season": {"year": year, "week": 20, "phase": "postseason",
                       "week_label": "Bowls"},
            "team": {"name": user_name, "espn_id": uid},
            "national": {"ap_top25": poll}, "all_teams": poll}


class Harness:
    """Redirects sync()'s world at a throwaway save + synthetic dynasty."""

    def __init__(self, base_save, user_name, user_rank, fmt, monkeypatch):
        self.tmp = Path(tempfile.mkdtemp(prefix="pl_state_"))
        self.save = self.tmp / "work.sav"
        shutil.copyfile(base_save, self.save)
        payload = container.decode(self.save.read_bytes()).payload
        self.roster = saveteams.parse_teams(payload)
        self.user_name = user_name
        self.user_row = next(i for i, t in enumerate(self.roster) if t.name == user_name)
        self.dynasty = _synth_dynasty(self.roster, user_name, user_rank)
        self.fmt = fmt
        self.engine = Engine(self.save)
        self._patch(monkeypatch)

    def _read_table(self):
        raw = self.save.read_bytes()
        c = container.decode(raw)
        try:
            table = savestruct.parse(c.payload)
        except Exception:
            table = None
        roster = saveteams.parse_teams(c.payload)
        return {"path": self.save, "raw": raw, "payload": c.payload, "table": table,
                "roster": roster, "rows_by_name": {t.name: i for i, t in enumerate(roster)}}

    def _patch(self, mp):
        mp.setattr(confsetup, "_read_table", self._read_table)
        mp.setattr(confsetup, "current_payload", lambda: self._read_table()["payload"])
        mp.setattr(confsetup, "_backup_once", lambda p: None)
        mp.setattr(pipeline, "current_pointer", lambda: {"year": 2026, "week": 20})
        mp.setattr(pipeline, "load_dynasty", lambda *a, **k: self.dynasty)
        # sync() reads the LIVE save week through this (never the pointer, so
        # a lagging pointer can no longer freeze the field from an archived
        # week); in the harness the synthetic dynasty IS the live state
        mp.setattr(pipeline, "load_live_dynasty", lambda: self.dynasty)
        mp.setattr(playoff, "get_format", lambda: self.fmt)
        mp.setattr(playoff_live, "_state_path", lambda: self.tmp / "live.json")
        mp.setattr(playoff_live, "_snapshot_path", lambda: self.tmp / "cycle_base.sav")
        mp.setattr(playoff_live, "_restore_snapshot_path",
                   lambda: self.tmp / "restore_base.sav")
        mp.setattr(playoff_live, "_native_boundary_snapshot_path",
                   lambda: self.tmp / "native_boundary_base.sav")
        mp.setattr(playoff_live, "_failed_boundary_snapshot_path",
                   lambda: self.tmp / "native_boundary_failed.sav")
        mp.setattr(playoff_live, "_history_path", lambda: self.tmp / "history.json")

    # -- introspection ---------------------------------------------------
    def state(self):
        p = self.tmp / "live.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def slate(self):
        return set(savesched.week_slate(container.decode(self.save.read_bytes()).payload))

    def user_unfinished(self, bracket, plan):
        for rnd in bracket.get("rounds") or []:
            recs = plan.get(str(rnd["round"])) or []
            for g, r in zip(rnd["games"], recs):
                if g.get("status") == "final":
                    continue
                if any(s.get("team") == self.user_name for s in g["slots"]) and \
                        all(s.get("type") == "team" for s in g["slots"]):
                    return g, r
        return None, None

    def user_eliminated(self, bracket):
        for rnd in bracket.get("rounds") or []:
            for g in rnd["games"]:
                if g.get("winner") and g["winner"] != self.user_name and \
                        any(s.get("team") == self.user_name for s in g["slots"]):
                    return True
        return False

    def all_final_scores(self):
        st = self.state()
        return [tuple(g.get("scores") or ())
                for rnd in (st.get("bracket") or {}).get("rounds") or []
                for g in rnd["games"] if g.get("status") == "final" and g.get("scores")]


def postseason_health(save_path):
    """(#double-booked teams, #duplicate bowl identities) in a save's
    postseason - both must be 0 for the engine to advance without freezing.

    CYCLE-mode measure: every wave plays at ONE rewound week, so a team may
    legitimately appear only once across the whole postseason. In NATIVE
    mode a team advances through real records week by week (a champion is in
    four games by season end), so this all-postseason count does NOT apply
    there; use slate_double_books instead."""
    from collections import Counter
    payload = container.decode(save_path.read_bytes()).payload
    store = savesched.parse(payload)
    tcount = Counter()
    for g in store.games:
        if g.bowl_row is not None and g.scheduled:
            for r in (g.away_row, g.home_row):
                if r is not None:
                    tcount[r] += 1
    dbl = sum(1 for c in tcount.values() if c > 1)
    post = [g.bowl_row for g in store.games if g.bowl_row is not None]
    dups = sum(1 for _, c in Counter(post).items() if c > 1)
    return dbl, dups


def slate_double_books(save_path):
    """Teams appearing in more than one SCHEDULED game inside the CURRENT
    week's slate. This is the native-mode freeze condition: the engine
    processes exactly the slate's games for the week, so one team in two of
    them (e.g. a custom playoff game plus a leftover regular bowl) is what
    freezes the advance. Sequential bracket rounds across weeks are fine."""
    from collections import Counter
    payload = container.decode(save_path.read_bytes()).payload
    store = savesched.parse(payload)
    slate = set(savesched.week_slate(payload))
    tcount = Counter()
    for r in slate:
        if r >= len(store.games):
            continue
        g = store.games[r]
        if not g.scheduled:
            continue
        for row in (g.away_row, g.home_row):
            if row is not None:
                tcount[row] += 1
    return sum(1 for c in tcount.values() if c > 1)


def slate_incomplete_games(save_path):
    """Current-week request records missing either participant.

    CFB 27's native postseason loader expects every record named by the week
    request queue to contain a complete matchup. A blank or one-sided regular
    bowl in that queue can crash the dynasty even when the custom CFP records
    themselves are valid.
    """
    payload = container.decode(save_path.read_bytes()).payload
    store = savesched.parse(payload)
    return [r for r in savesched.week_slate(payload)
            if r < len(store.games)
            and (store.games[r].away_row is None
                 or store.games[r].home_row is None)]


def slate_partial_result_pairs(save_path):
    """Current scheduled games with exactly one participant request ID."""
    payload = container.decode(save_path.read_bytes()).payload
    store = savesched.parse(payload)
    return [r for r in savesched.week_slate(payload)
            if r < len(store.games) and store.games[r].scheduled
            and not store.games[r].official
            and savesched.result_pair_partial(payload, store.games[r])]


def run(harness, size, elim_round, max_waves=300):
    """Drive the full loop. elim_round: 1-based round the user loses; 0 = win
    it all. Returns a result dict with ok/champion/user_played/waves/state.

    Each wave: the app writes (sync write=True); the emulator loads (sims the
    slate, applying the scenario's win/loss to the user's game); the app
    captures (sync write=False). The user is 'playing' only when they have a
    decided, unfinished game mapped to a record in the current slate."""
    h = harness
    in_field = h.user_name in {
        s.get("team") for s in playoff.build_bracket(h.dynasty, h.fmt).get("seeds") or []}
    played = 0
    for wave in range(1, max_waves):
        out = playoff_live.sync(write=True)
        st = h.state()
        bracket = out.get("bracket") or {}
        if st.get("status") == "complete" or bracket.get("champion"):
            return {"ok": True, "champion": (bracket.get("champion") or {}).get("team"),
                    "user_played": played, "waves": wave, "state": st}
        ug, urec = h.user_unfinished(bracket, st.get("plan") or {})
        result = None
        if (in_field and ug is not None and urec in h.slate()
                and not h.user_eliminated(bracket)):
            played += 1
            result = "loss" if (elim_round and played == elim_round) else "win"
        simmed = h.engine.load(h.user_row if result else None, result)
        playoff_live.sync(write=False)
        if simmed == 0 and result is None:
            return {"ok": False, "reason": "stall", "user_played": played,
                    "waves": wave, "state": st}
    return {"ok": False, "reason": "did-not-complete", "user_played": played,
            "state": h.state()}


def run_native(harness, size, elim_round, max_rounds=8):
    """Drive a NATIVE-mode bracket (<=16 teams) forward through the game's
    own bowl-week calendar: each round is applied at its week's pre-lock
    arrival, the engine loads and sims it, the app captures the results, and
    the week advances. No rewinds. Verifies the bracket completes, the user
    plays exactly as many games as their finish implies, and no postseason
    record is ever double-booked (the freeze condition).

    elim_round: 1-based round the user loses; 0 = win it all.
    """
    h = harness
    in_field = h.user_name in {
        s.get("team") for s in playoff.build_bracket(h.dynasty, h.fmt).get("seeds") or []}
    played = 0
    for rnd_i in range(1, max_rounds + 1):
        # arrival: the app writes this week's round onto the pre-lock world
        out = playoff_live.sync(write=True)
        st = h.state()
        bracket = out.get("bracket") or {}
        assert st.get("mode") == "native", f"mode {st.get('mode')} != native"
        dbl = slate_double_books(h.save)
        if dbl:
            return {"ok": False, "reason": f"double-booked in slate ({dbl})",
                    "round": rnd_i, "state": st}
        if st.get("status") == "complete" or bracket.get("champion"):
            return {"ok": True, "champion": (bracket.get("champion") or {}).get("team"),
                    "user_played": played, "rounds": rnd_i - 1, "state": st}
        ug, urec = h.user_unfinished(bracket, st.get("plan") or {})
        result = None
        if (in_field and ug is not None and urec in h.slate()
                and not h.user_eliminated(bracket)):
            played += 1
            result = "loss" if (elim_round and played == elim_round) else "win"
        # the engine loads the arrival week and sims/plays the slate
        simmed = h.engine.load(h.user_row if result else None, result)
        # the app captures the results, then the user advances to next week
        playoff_live.sync(write=False)
        h.engine.advance_week()
        partial = slate_partial_result_pairs(h.save)
        if partial:
            return {"ok": False,
                    "reason": f"half-issued participant requests ({partial})",
                    "round": rnd_i, "state": st}
        if simmed == 0 and result is None:
            return {"ok": False, "reason": "stall", "round": rnd_i, "state": st}
    return {"ok": False, "reason": "did-not-complete", "user_played": played,
            "state": h.state()}


def _pre_tail_final(bracket):
    """True once every round OUTSIDE the native endgame (the final <=4 rounds)
    is final: the 16 survivors are known and the hybrid hands off to native."""
    tail = playoff_live.native_tail_rounds(bracket)
    if not tail:
        return True
    return all(g.get("status") == "final"
               for rnd in bracket.get("rounds") or []
               if str(rnd["round"]) not in tail
               for g in rnd["games"])


def run_hybrid(harness, size, elim_round, max_steps=80):
    """Drive a HYBRID bracket (>16 teams): cycle the early rounds at bowl week
    1 (rewinding, no calendar advance) until 16 teams remain, then hand off to
    the native forward calendar for the final four rounds (round of 16 through
    the championship), advancing a bowl week after each. Verifies the whole
    bracket completes, the endgame records forward with no double-book in any
    week's slate, and the user's finish is right.
    """
    h = harness
    in_field = h.user_name in {
        s.get("team") for s in playoff.build_bracket(h.dynasty, h.fmt).get("seeds") or []}
    played = 0
    advanced = False
    for step in range(1, max_steps + 1):
        out = playoff_live.sync(write=True)
        st = h.state()
        bracket = out.get("bracket") or {}
        if st.get("status") == "complete" or bracket.get("champion"):
            return {"ok": True, "champion": (bracket.get("champion") or {}).get("team"),
                    "user_played": played, "steps": step, "state": st,
                    "advanced": advanced}
        # Every oversized bracket hands off once 16 teams remain, including a
        # user the engine originally assigned to an ordinary bowl. This save
        # emulator validates the user request, week-one mapping, and native
        # forward progression.
        native_phase = _pre_tail_final(bracket)
        if native_phase:
            # the native endgame must never double-book a team in one week's
            # slate (the freeze condition), or leave a queued bowl without a
            # complete two-team matchup (the Penn State load-crash condition)
            dbl = slate_double_books(h.save)
            if dbl:
                return {"ok": False, "reason": f"double-booked in slate ({dbl})",
                        "step": step, "state": st}
            incomplete = slate_incomplete_games(h.save)
            if incomplete:
                return {"ok": False,
                        "reason": f"incomplete games in slate ({incomplete})",
                        "step": step, "state": st}
        ug, urec = h.user_unfinished(bracket, st.get("plan") or {})
        result = None
        if (in_field and ug is not None and urec in h.slate()
                and not h.user_eliminated(bracket)):
            played += 1
            result = "loss" if (elim_round and played == elim_round) else "win"
        simmed = h.engine.load(h.user_row if result else None, result)
        playoff_live.sync(write=False)
        if native_phase:
            # the endgame moves forward with the real calendar; the early
            # (cycle) rounds stay at bowl week 1 and rewind between waves
            h.engine.advance_week()
            advanced = True
            partial = slate_partial_result_pairs(h.save)
            if partial:
                return {"ok": False,
                        "reason": f"half-issued participant requests ({partial})",
                        "step": step, "state": st}
        if simmed == 0 and result is None and not native_phase:
            return {"ok": False, "reason": "stall (cycle phase)",
                    "step": step, "state": st}
    return {"ok": False, "reason": "did-not-complete", "user_played": played,
            "state": h.state()}
