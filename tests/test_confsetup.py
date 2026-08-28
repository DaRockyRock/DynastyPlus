"""Tests for the conference setup editor (`backend.confsetup`) against a
synthetic save (structures from test_saveparse_conferences + a fake roster)."""
import copy
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend import confsetup
from backend.saveparse import conferences as savestruct
from backend.saveparse import container, teams as saveteams
from test_saveparse_conferences import build_payload

TEAM_COUNT = 92  # covers every row referenced by the synthetic membership lists


def _teams_blob() -> bytes:
    out = bytearray()
    for i in range(TEAM_COUNT):
        rec = bytearray(saveteams.RECORD_STRIDE)

        def put(off: int, s: str) -> None:
            rec[off:off + len(s)] = s.encode("latin1")

        put(300 + saveteams._OFF_SCHOOL, f"School{i:02d}")
        put(300 + saveteams._OFF_ABBR, f"S{i:02d}")
        put(300 + saveteams._OFF_NICK, "Tigers")
        put(300, f"teamdb_s{i:02d}")
        out += rec
    return bytes(out)


def _fbchunks(payload: bytes) -> bytes:
    buf = bytearray(82)
    buf[0:8] = container.MAGIC
    struct.pack_into("<H", buf, 8, 1)
    struct.pack_into("<6H", buf, 22, 2026, 7, 6, 12, 0, 0)
    build = b"College-27-RL1-9039126\x00"
    buf[34:34 + len(build)] = build
    stream = zlib.compress(payload, 6)
    struct.pack_into("<I", buf, 74, len(stream))
    return bytes(buf) + stream + b"\x00" * 200_000


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    payload = build_payload() + _teams_blob()
    save = tmp_path / "DYNASTY-TEST"
    save.write_bytes(_fbchunks(payload))
    # newest DYNASTY-* in the sandbox, like production (apply writes a new file)
    monkeypatch.setattr(confsetup, "_save_file",
                        lambda: max(tmp_path.glob("DYNASTY-*"),
                                    key=lambda p: p.stat().st_mtime_ns))
    monkeypatch.setattr(confsetup.dynasty_paths, "current_root", lambda: tmp_path / "dyn")
    monkeypatch.setattr(confsetup.cfb27, "_identity",
                        lambda name: {"espn_id": None, "logo": None, "conference": None})
    import backend.pipeline as pipeline
    monkeypatch.setattr(pipeline, "current_pointer", lambda: {"year": 2026, "week": 0})
    confsetup._table_cache.clear()
    confsetup._overlay_cache.clear()
    return save


def _name(i: int) -> str:
    return f"School{i:02d} Tigers"


def test_get_state(sandbox):
    state = confsetup.get_state()
    assert state["available"] and state["writable"]
    assert state["apply_gate"]["ok"]  # no WEEK marker + pointer at preseason
    by = {c["name"]: c for c in state["conferences"]}
    assert by["ACC"]["teams"] == [_name(i) for i in (0, 1, 2, 3)]
    assert [d["name"] for d in by["Sun Belt"]["divisions"]] == ["East", "West"]
    ind = next(c for c in state["conferences"] if c["independents"])
    assert ind["teams"] == [_name(90), _name(91)]
    assert not state["dirty"]


def test_validation_rejects_bad_setups(sandbox):
    state = confsetup.get_state()
    # dropping a team entirely
    draft = copy.deepcopy(state["conferences"])
    next(c for c in draft if c["name"] == "ACC")["teams"].pop()
    with pytest.raises(ValueError, match="needs a conference"):
        confsetup.set_state(draft)
    # under the game's 4-team minimum
    draft = copy.deepcopy(state["conferences"])
    acc = next(c for c in draft if c["name"] == "ACC")
    sec = next(c for c in draft if c["name"] == "SEC")
    moved = acc["teams"].pop()
    sec["teams"].append(moved)
    with pytest.raises(ValueError, match="at least 4"):
        confsetup.set_state(draft)
    # divisions must partition the conference
    draft = copy.deepcopy(state["conferences"])
    sb = next(c for c in draft if c["name"] == "Sun Belt")
    sb["divisions"][0]["teams"].pop()
    with pytest.raises(ValueError, match="every member"):
        confsetup.set_state(draft)
    # name too long for the save's fixed slot
    draft = copy.deepcopy(state["conferences"])
    next(c for c in draft if c["name"] == "ACC")["name"] = "X" * 25
    with pytest.raises(ValueError, match="longer than 20"):
        confsetup.set_state(draft)


def test_save_applies_in_place_and_overlay(sandbox):
    # preseason (fixture pointer week 0): Save writes names AND membership into
    # the SAME save file, and the overlay reflects the setup
    state = confsetup.get_state()
    draft = copy.deepcopy(state["conferences"])
    mac = next(c for c in draft if c["key"] == "MAC")   # 8 teams: room to give
    sec = next(c for c in draft if c["key"] == "SEC")
    sec["teams"].append(mac["teams"].pop())              # School83 to the SEC
    sec["name"] = "Super East"
    res = confsetup.set_state(draft)
    assert res["last_apply"]["saved_to"] == str(sandbox)  # in place, same file

    # the sandbox save itself now carries both changes
    t = savestruct.parse(container.decode(sandbox.read_bytes()).payload)
    assert t.by_name("SEC").display == "Super East"
    assert 83 in t.by_name("SEC").team_rows and 83 not in t.by_name("MAC").team_rows

    over = confsetup.alignment_overlay()
    assert over[_name(83)]["conference"] == "Super East"
    dyn = {"team": {"name": _name(83), "conference": "MAC"}, "all_teams": []}
    confsetup.apply_overlay(dyn)
    assert dyn["team"]["conference"] == "Super East"


def test_orphaned_teams_return_to_their_save_conference(sandbox):
    # A stored setup that claims a conference has NO teams (saved while an
    # older build misparsed a realigned save; reported: the American showed
    # zero teams and its members were in no conference at all, though still
    # in the polls) must not strand the members forever: any save-known team
    # no entry claims goes back to its save conference on read.
    state = confsetup.get_state()
    stored = copy.deepcopy(state["conferences"])
    acc = next(c for c in stored if c["name"] == "ACC")
    acc_teams = list(acc["teams"])
    acc["teams"] = []          # the poisoned store entry
    confsetup._write_store(stored)
    confsetup._overlay_cache.clear()
    healed = confsetup.get_state()
    acc2 = next(c for c in healed["conferences"] if c["name"] == "ACC")
    assert acc2["teams"] == acc_teams, "orphaned teams were not rescued"
    everywhere = [t for c in healed["conferences"] for t in c["teams"]]
    assert sorted(everywhere) == sorted(set(everywhere)), "a team is in two conferences"
    # the healed state also round-trips through validation (a later Save works)
    confsetup.set_state(copy.deepcopy(healed["conferences"]))


def test_reset_clears_companion_edits(sandbox):
    # reset clears the companion store (abbr/logo/rivalries/pending edits). It
    # does NOT un-write changes already applied to the game save (those are the
    # game's now); that is by design.
    state = confsetup.get_state()
    big12 = next(c for c in state["conferences"] if c["key"] == "Big_12")
    default_abbr = big12["abbr"]
    draft = copy.deepcopy(state["conferences"])
    next(c for c in draft if c["key"] == "Big_12")["abbr"] = "B1G12"  # companion-only
    confsetup.set_state(draft)
    assert next(c for c in confsetup.get_state()["conferences"]
                if c["key"] == "Big_12")["abbr"] == "B1G12"
    confsetup.reset()
    assert next(c for c in confsetup.get_state()["conferences"]
                if c["key"] == "Big_12")["abbr"] == default_abbr


def test_save_no_new_files(sandbox, tmp_path):
    before = {p.name for p in tmp_path.glob("DYNASTY-*")}
    state = confsetup.get_state()
    draft = copy.deepcopy(state["conferences"])
    next(c for c in draft if c["key"] == "Big_12")["name"] = "Big Twelve"
    confsetup.set_state(draft)
    after = {p.name for p in tmp_path.glob("DYNASTY-*")}
    assert before == after  # patched in place, no DYNASTY-CONFSETUP created


def test_save_gates_moves_midseason(sandbox, monkeypatch):
    import backend.pipeline as pipeline
    monkeypatch.setattr(pipeline, "current_pointer", lambda: {"year": 2026, "week": 5})
    assert not confsetup.get_state()["apply_gate"]["ok"]

    draft = copy.deepcopy(confsetup.get_state()["conferences"])
    acc = next(c for c in draft if c["key"] == "ACC")
    mac = next(c for c in draft if c["key"] == "MAC")
    acc["name"] = "Atlantic Coast"
    moved = mac["teams"].pop()
    acc["teams"].append(moved)
    res = confsetup.set_state(draft)

    # rename applied; move deferred to the offseason
    assert any("Atlantic Coast" in a for a in res["last_apply"]["applied"])
    assert res["last_apply"]["pending"]
    written = container.decode(sandbox.read_bytes()).payload
    t = savestruct.parse(written)
    assert t.by_name("ACC").display == "Atlantic Coast"
    rows = savestruct.team_rows_by_name(written)
    assert rows[moved] in t.by_name("MAC").team_rows      # move did NOT happen
    assert rows[moved] not in t.by_name("ACC").team_rows


def test_save_pure_rename_writes_any_week(sandbox, monkeypatch):
    import backend.pipeline as pipeline
    monkeypatch.setattr(pipeline, "current_pointer", lambda: {"year": 2026, "week": 9})
    draft = copy.deepcopy(confsetup.get_state()["conferences"])
    next(c for c in draft if c["key"] == "Big_12")["name"] = "Big Twelve"
    confsetup.set_state(draft)  # not gated: rename only, written in place
    t = savestruct.parse(container.decode(sandbox.read_bytes()).payload)
    assert t.by_name("Big_12").display == "Big Twelve"


def test_original_save_backed_up(sandbox, monkeypatch):
    import backend.pipeline as pipeline
    monkeypatch.setattr(pipeline, "current_pointer", lambda: {"year": 2026, "week": 9})
    original = sandbox.read_bytes()
    draft = copy.deepcopy(confsetup.get_state()["conferences"])
    next(c for c in draft if c["key"] == "Big_12")["name"] = "Big Twelve"
    confsetup.set_state(draft)
    backup = confsetup.config.DATA_DIR / "save_backups" / f"{sandbox.name}.original"
    assert backup.exists() and backup.read_bytes() == original


# --- logo source resolution + historic (classic) conference marks -----------

def test_historic_label_formats():
    assert confsetup._historic_label("1988_2008") == "1988 to 2008"
    assert confsetup._historic_label("2023_present") == "2023 to Present"
    assert confsetup._historic_label("pac10_1") == "Pac 10 1"
    assert confsetup._historic_label("pcc") == "PCC"
    assert confsetup._historic_label("circle") == "Circle"
    assert confsetup._historic_label("") == "Classic"


def test_is_custom_logo_covers_uploads_and_historic():
    assert confsetup._is_custom_logo("/uploads/ab.png")
    assert confsetup._is_custom_logo("/game-assets/conferences/historic/sec_1988_2008.png")
    assert not confsetup._is_custom_logo("/game-assets/conferences/sec.png")  # stock mark
    assert not confsetup._is_custom_logo(None)
    assert not confsetup._is_custom_logo("")


def test_upload_path_resolves_both_sources():
    ga = confsetup.config.DATA_DIR / "game_assets" / "conferences" / "historic"
    ga.mkdir(parents=True, exist_ok=True)
    (ga / "sec_1988_2008.png").write_bytes(b"x")
    up = confsetup.config.UPLOADS_DIR
    up.mkdir(parents=True, exist_ok=True)
    (up / "deadbeef.png").write_bytes(b"y")

    assert confsetup._upload_path("/game-assets/conferences/historic/sec_1988_2008.png") is not None
    assert confsetup._upload_path("/uploads/deadbeef.png") is not None
    assert confsetup._upload_path("/game-assets/conferences/historic/missing.png") is None
    assert confsetup._upload_path("http://example.com/x.png") is None


def test_historic_logos_groups_by_conference_key():
    hist = confsetup.config.DATA_DIR / "game_assets" / "conferences" / "historic"
    hist.mkdir(parents=True, exist_ok=True)
    for name in ("sec_1988_2008.png", "sec_2008_2022.png", "big12_2014_2026.png"):
        (hist / name).write_bytes(b"x")

    res = confsetup.historic_logos()
    assert res["available"] is True
    assert set(res["logos"]) == {"SEC", "Big_12"}
    assert len(res["logos"]["SEC"]) == 2
    sec = res["logos"]["SEC"][0]
    assert sec["url"].startswith("/game-assets/conferences/historic/")
    assert sec["label"] == "1988 to 2008"  # sorted by label


def test_logo_builders_use_the_configured_game_install(tmp_path, monkeypatch):
    """Logo export must follow Setup's game path, including another drive."""
    from backend.assets.frostbite import modbuild

    game_root = tmp_path / "E Drive" / "College Football 27"
    seen = []

    class FakeLogoMod:
        def __init__(self, root):
            seen.append(Path(root))
            self.fs = SimpleNamespace(root=Path(root), data=Path(root) / "Data")

        def build(self, edits, out):
            return {"edits": len(edits), "root": str(out)}

    monkeypatch.setattr(confsetup.app_settings, "resolve_game_root", lambda: game_root)
    monkeypatch.setattr(modbuild, "ConferenceLogoMod", FakeLogoMod)
    monkeypatch.setattr(confsetup, "_collect_logo_edits",
                        lambda _mod: ([], ["SEC"], []))
    monkeypatch.setattr(confsetup, "_require_asset_pipeline", lambda: None)

    confsetup.build_logo_mod(tmp_path / "legacy-mod")
    exported = tmp_path / "logos.fbmod"
    confsetup.export_logo_fbmod(exported)

    assert seen == [game_root, game_root]
    assert exported.is_file()
