"""Tests for the poll editor (`backend.polledit`): config validation, the
desired-order semantics, and the apply flow (against a synthetic TeamStore
payload; the container encode/backup plumbing is stubbed)."""
import json
from types import SimpleNamespace

import pytest

from backend import polledit, rankings
from backend.saveparse import polls as savepolls

from test_saveparse_polls import build_payload


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Point the editor's per-dynasty state at a throwaway directory."""
    monkeypatch.setattr(polledit, "_state_path",
                        lambda: tmp_path / "editor.json")


def _fake_roster(n=6):
    names = ["Alpha A", "Bravo B", "Charlie C", "Delta D", "Echo E", "FCS Placeholder"]
    return [SimpleNamespace(name=names[i], school=names[i].split()[0],
                            abbreviation=names[i][:3].upper(), slug=str(i))
            for i in range(n)]


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def test_default_config_and_roundtrip():
    cfg = polledit.get_config()
    assert set(cfg["polls"]) == set(savepolls.POLLS)
    assert all(p["mode"] == "game" for p in cfg["polls"].values())
    saved = polledit.set_config({"polls": {"cfp": {"mode": "manual",
                                                   "manual": ["Alpha A", "Bravo B"]}},
                                 "auto_apply": False})
    assert saved["polls"]["cfp"]["mode"] == "manual"
    assert polledit.get_config()["polls"]["cfp"]["manual"] == ["Alpha A", "Bravo B"]
    assert polledit.get_config()["auto_apply"] is False


def test_set_config_rejects_bad_values():
    with pytest.raises(ValueError):
        polledit.set_config({"polls": {"cfp": {"mode": "vibes"}}})
    with pytest.raises(ValueError):
        polledit.set_config({"polls": {"cfp": {"algorithm": "magic"}}})
    with pytest.raises(ValueError):
        polledit.set_config({"polls": {"cfp": {"manual": ["Alpha A", "Alpha A"]}}})
    with pytest.raises(ValueError):
        polledit.set_config({"polls": {"cfp": {"manual": "Alpha A"}}})
    # unknown poll keys are ignored, not an error
    cfg = polledit.set_config({"polls": {"coaches": {"mode": "manual"}}})
    assert "coaches" not in cfg["polls"]


# ---------------------------------------------------------------------------
# desired order
# ---------------------------------------------------------------------------

def test_desired_rows_manual_head_plus_engine_tail(monkeypatch):
    payload = bytes(build_payload())  # cfp order: rows 0..4, row 5 unranked
    monkeypatch.setattr(polledit.saveteams, "parse_teams",
                        lambda p: _fake_roster())
    polledit.set_config({"polls": {"cfp": {
        "mode": "manual",
        # Echo to #1, a stale name skipped, the FCS row (unranked) skipped
        "manual": ["Echo E", "Gone State", "FCS Placeholder", "Alpha A"],
    }}})
    assert polledit.desired_rows("cfp", payload=payload) == [4, 0, 1, 2, 3]


def test_desired_rows_game_mode_is_none():
    assert polledit.desired_rows("cfp", payload=bytes(build_payload())) is None


def test_desired_rows_algorithm(monkeypatch):
    payload = bytes(build_payload())
    monkeypatch.setattr(polledit.saveteams, "parse_teams",
                        lambda p: _fake_roster())
    # a fake schedule: row 4 beat row 0; everything else idle
    games = [rankings.GameResult(home=4, away=0, home_score=28, away_score=7)]
    monkeypatch.setattr(polledit, "_official_games", lambda store: games)
    monkeypatch.setattr(polledit.savesched, "parse", lambda p: None)
    polledit.set_config({"polls": {"cfp": {"mode": "algorithm",
                                           "algorithm": "colley"}}})
    order = polledit.desired_rows("cfp", payload=payload)
    assert order[0] == 4
    assert order[-1] == 0
    assert set(order) == {0, 1, 2, 3, 4}


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

@pytest.fixture()
def _apply_env(tmp_path, monkeypatch):
    """Stub the save plumbing: a synthetic payload behind confsetup, a
    passthrough encoder, and no playoff hold."""
    payload = build_payload()
    save = tmp_path / "DYNASTY-TEST"
    save.write_bytes(b"raw")
    ctx = {"payload": bytes(payload), "raw": b"raw", "path": save}
    monkeypatch.setattr(polledit.confsetup, "_read_table", lambda: ctx)
    monkeypatch.setattr(polledit.confsetup, "_backup_once", lambda p: None)
    monkeypatch.setattr(polledit.confsetup, "_table_cache", {})
    monkeypatch.setattr(polledit.container, "encode",
                        lambda raw, p, saved_at=None: p)
    monkeypatch.setattr(polledit.savesched, "parse", lambda p: None)
    monkeypatch.setattr(polledit, "_playoff_hold", lambda: None)
    monkeypatch.setattr(polledit.saveteams, "parse_teams",
                        lambda p: _fake_roster())
    return ctx, save


def test_apply_writes_manual_order(_apply_env):
    ctx, save = _apply_env
    polledit.set_config({"polls": {"cfp": {"mode": "manual",
                                           "manual": ["Echo E", "Delta D"]}}})
    out = polledit._apply_locked(force=False)
    assert out["written"] is True
    assert out["changed"] == {"cfp": True}
    written = save.read_bytes()
    assert savepolls.poll_order(written, "cfp") == [4, 3, 0, 1, 2]
    assert savepolls.poll_order(written, "ap") == [1, 0, 2, 3, 4]  # untouched
    assert polledit.get_config()["last_applied"]["polls"] == ["cfp"]


def test_apply_skips_when_save_already_matches(_apply_env):
    polledit.set_config({"polls": {"cfp": {"mode": "manual",
                                           "manual": ["Alpha A", "Bravo B"]}}})
    out = polledit._apply_locked(force=False)
    assert out["written"] is False
    assert out["changed"] == {"cfp": False}


def test_apply_all_game_mode_is_noop(_apply_env):
    out = polledit._apply_locked(force=False)
    assert out["written"] is False
    assert polledit.auto_apply() is None


def test_apply_holds_committee_for_live_playoff(_apply_env, monkeypatch):
    monkeypatch.setattr(polledit, "_playoff_hold", lambda: "bracket is live")
    polledit.set_config({"polls": {
        "cfp": {"mode": "manual", "manual": ["Echo E"]},
        "ap": {"mode": "manual", "manual": ["Echo E"]},
    }})
    out = polledit._apply_locked(force=False)
    # the committee write is held with the reason; the AP write proceeds
    assert out["held"] == {"cfp": "bracket is live"}
    assert out["changed"] == {"ap": True}
    assert out["written"] is True


def test_auto_apply_respects_toggle(_apply_env):
    polledit.set_config({"polls": {"cfp": {"mode": "manual",
                                           "manual": ["Echo E"]}},
                         "auto_apply": False})
    assert polledit.auto_apply() is None


def test_auto_apply_respects_global_autosync(_apply_env, monkeypatch):
    from backend import app_settings
    monkeypatch.setattr(app_settings, "autosync_enabled", lambda: False)
    polledit.set_config({"polls": {"cfp": {"mode": "manual",
                                           "manual": ["Echo E"]}}})
    # per-dynasty auto_apply is on, but the global switch is off -> no push
    assert polledit.auto_apply() is None


def _fake_store(scheduled_indices, count=983):
    games = [SimpleNamespace(index=i, scheduled=i in scheduled_indices)
             for i in range(count)]
    return SimpleNamespace(games=games, count=count)


def test_native_seal_notice_fires_once_field_is_seeded(monkeypatch):
    # Automation OFF + the native first-round records hold real teams: the
    # committee field is only a seed label now, so the editor must say so.
    from backend import playoff_live
    monkeypatch.setattr(playoff_live, "is_enabled", lambda: False)
    monkeypatch.setattr(playoff_live, "_postseason_slots",
                        lambda p: {"first_round": [924, 925, 926, 927]})
    monkeypatch.setattr(polledit.savesched, "parse",
                        lambda p: _fake_store({924, 925, 926, 927}))
    assert polledit._native_seal_notice(b"") is not None


def test_native_seal_notice_quiet_before_selection(monkeypatch):
    # Same world but the first-round records are still TBD (regular season /
    # championship week): pushes still shape the selection, no notice.
    from backend import playoff_live
    monkeypatch.setattr(playoff_live, "is_enabled", lambda: False)
    monkeypatch.setattr(playoff_live, "_postseason_slots",
                        lambda p: {"first_round": [924, 925, 926, 927]})
    monkeypatch.setattr(polledit.savesched, "parse",
                        lambda p: _fake_store(set()))
    assert polledit._native_seal_notice(b"") is None


def test_native_seal_notice_quiet_when_automation_on(monkeypatch):
    # With the custom playoff ON the selection window re-seeds the bracket
    # from the poll (and the hold covers a live bracket), so no notice even
    # over a seeded field.
    from backend import playoff_live
    monkeypatch.setattr(playoff_live, "is_enabled", lambda: True)
    monkeypatch.setattr(playoff_live, "_postseason_slots",
                        lambda p: {"first_round": [924]})
    monkeypatch.setattr(polledit.savesched, "parse",
                        lambda p: _fake_store({924}))
    assert polledit._native_seal_notice(b"") is None


def test_native_seal_notice_quiet_on_unparseable_save(monkeypatch):
    # Best-effort flavor: a save whose postseason structures do not parse
    # must not break the polls endpoint.
    from backend import playoff_live
    monkeypatch.setattr(playoff_live, "is_enabled", lambda: False)
    assert polledit._native_seal_notice(b"not a save") is None


def test_playoff_hold_lifts_when_autosync_off(monkeypatch):
    from backend import app_settings, playoff_live
    monkeypatch.setattr(playoff_live, "_load_state",
                        lambda: {"status": "in_progress"})
    monkeypatch.setattr(app_settings, "autosync_enabled", lambda: True)
    assert polledit._playoff_hold() is not None   # automation on -> committee held
    monkeypatch.setattr(app_settings, "autosync_enabled", lambda: False)
    assert polledit._playoff_hold() is None        # automation off -> user rules


def test_playoff_hold_opens_the_pre_playoff_edit_window(monkeypatch):
    # A freshly SELECTED field with no recorded result must NOT hold the
    # committee: the playoff sync re-seeds the frozen field from the poll
    # until a game goes final, so bowl-week edits are exactly how the user
    # shapes the final field. A result (or in_progress) closes the window.
    from backend import app_settings, playoff_live
    monkeypatch.setattr(app_settings, "autosync_enabled", lambda: True)
    # The hold only exists to protect the AUTOMATION; it is meaningful only when
    # the custom playoff is on (off is covered below).
    monkeypatch.setattr(playoff_live, "is_enabled", lambda: True)
    final = {"rounds": [{"round": 1, "games": [{"status": "final", "slots": []}]}]}
    pending = {"rounds": [{"round": 1, "games": [{"status": "scheduled", "slots": []}]}]}
    monkeypatch.setattr(playoff_live, "_load_state",
                        lambda: {"status": "selected", "bracket": pending})
    assert polledit._playoff_hold() is None       # the edit window
    monkeypatch.setattr(playoff_live, "_load_state",
                        lambda: {"status": "selected", "bracket": final})
    assert polledit._playoff_hold() is not None   # a result locks the field
    monkeypatch.setattr(playoff_live, "_load_state",
                        lambda: {"status": "in_progress", "bracket": final})
    assert polledit._playoff_hold() is not None
    monkeypatch.setattr(playoff_live, "_load_state",
                        lambda: {"status": "projected", "rank_swap": {"user": 1}})
    assert polledit._playoff_hold() is not None   # legacy prepare swap planted
    # Turning the custom playoff OFF lifts every hold: the user's custom poll is
    # then authoritative and seeds the game's own native bracket.
    monkeypatch.setattr(playoff_live, "is_enabled", lambda: False)
    assert polledit._playoff_hold() is None
