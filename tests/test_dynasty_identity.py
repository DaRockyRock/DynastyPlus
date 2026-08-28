"""Per-save-file identity: the library lists each save file, and one save
file's registry/store never collides with another's.

Regression guard for the adopt_legacy misfire that silently dropped a save
file: per-file ids ('cfb27-<digits>-<savename>') must NOT be treated as the
old build-id 'legacy' form, or sibling saves of the same school re-key into
each other."""
import json
from contextlib import contextmanager

from backend import config, dynasties, dynasty_paths, playoff_live
from backend.saveparse import cfb27


def test_file_id_is_per_save_file():
    a = cfb27.file_id("1920640934", "DYNASTY-WEEK3-AUTOSAVE")
    b = cfb27.file_id("1920640934", "DYNASTY-JUL06-01h20m57-AUTOSAVE")
    assert a != b                       # same dynasty world, different files
    assert a.startswith("cfb27-1920640934-")
    assert cfb27.file_id("1920640934", "DYNASTY-WEEK3-AUTOSAVE") == a  # stable


def _fresh_registry():
    (config.DATA_DIR / "dynasties.json").unlink(missing_ok=True)


def _entry(dynasty_id, school):
    return {"meta": {"dynasty_id": dynasty_id}, "team": {"school": school, "name": school}}


def test_two_saves_same_dynasty_both_register():
    _fresh_registry()
    dynasties.upsert_from_save(_entry("cfb27-42-week3", "Charlotte"),
                               save_name="DYNASTY-WEEK3", game_id="42", make_current=False)
    # the sibling save must survive registration, not get re-keyed away
    dynasties.adopt_legacy("cfb27-42-week9", "Charlotte")
    dynasties.upsert_from_save(_entry("cfb27-42-week9", "Charlotte"),
                               save_name="DYNASTY-WEEK9", game_id="42", make_current=False)
    ids = {d["id"] for d in dynasties.list_all()["dynasties"]}
    assert ids == {"cfb27-42-week3", "cfb27-42-week9"}


def test_remove_hides_card_until_explicit_unhide():
    _fresh_registry()
    dynasties.upsert_from_save(_entry("cfb27-42-old", "Charlotte"),
                               save_name="DYNASTY-OLD", game_id="42")
    dynasties.upsert_from_save(_entry("cfb27-42-live", "Charlotte"),
                               save_name="DYNASTY-LIVE", game_id="42")

    assert dynasties.remove("cfb27-42-old") is True
    assert dynasties.get("cfb27-42-old") is None
    assert dynasties.is_hidden("cfb27-42-old") is True
    # A scan pruning pass keeps a hidden id while its file is still valid.
    dynasties.prune_missing({"cfb27-42-old", "cfb27-42-live"})
    assert dynasties.is_hidden("cfb27-42-old") is True

    assert dynasties.unhide("cfb27-42-old") is True
    assert dynasties.is_hidden("cfb27-42-old") is False
    assert dynasties.remove("missing") is False


def test_adopt_legacy_only_rekeys_build_slug_ids():
    _fresh_registry()
    # a numeric per-file id and a genuine legacy build-slug id, same school
    dynasties.upsert_from_save(_entry("cfb27-42-week3", "Charlotte"),
                               save_name="DYNASTY-WEEK3", game_id="42", make_current=False)
    dynasties.upsert_from_save(_entry("cfb27-college-27-rl1-charlotte", "Charlotte"),
                               save_name="OLD", game_id=None, make_current=False)
    # adopting a new per-file id should migrate ONLY the build-slug entry
    dynasties.adopt_legacy("cfb27-42-week9", "Charlotte")
    ids = {d["id"] for d in dynasties.list_all()["dynasties"]}
    assert "cfb27-42-week3" in ids                 # per-file sibling untouched
    assert "cfb27-college-27-rl1-charlotte" not in ids  # legacy re-keyed away
    assert "cfb27-42-week9" in ids


def test_playoff_sync_pins_one_dynasty_during_concurrent_select(monkeypatch):
    """A current-pointer change cannot redirect a running sync's state path."""
    current = {"id": "cfb27-old-save"}
    monkeypatch.setattr(dynasties, "current_id", lambda: current["id"])
    # This exercises the real sync body, which only runs when the custom playoff
    # automation is on (off short-circuits to the native-playoff status).
    monkeypatch.setattr(playoff_live, "is_enabled", lambda: True)

    @contextmanager
    def no_process_lock():
        yield

    monkeypatch.setattr(playoff_live, "_cross_process_lock", no_process_lock)

    def fake_sync(*, write):
        current["id"] = "cfb27-new-save"  # Scan/select races this sync
        return {
            "write": write,
            "bound_id": dynasty_paths.current_id(),
            "bound_root": dynasty_paths.current_root().name,
        }

    monkeypatch.setattr(playoff_live, "_sync_locked", fake_sync)
    out = playoff_live.sync(write=False)
    assert out == {
        "write": False,
        "bound_id": "cfb27-old-save",
        "bound_root": "cfb27-old-save",
    }
    assert dynasty_paths.current_id() == "cfb27-new-save"


def _team(school, nickname="Tigers", slug=None):
    from backend.saveparse import teams as saveteams
    return saveteams.Team(slug=slug or school.lower().replace(" ", ""),
                          school=school, nickname=nickname,
                          abbreviation=school[:3].upper())


def _slot(school):
    from backend.saveparse import profile
    return profile.Slot(save_name="DYNASTY-X", dynasty_id="1", school=school,
                        next_game="", coach_first="A", coach_last="B",
                        week_label="Week", week=1, season=1, team_row=0,
                        wins=0, losses=0)


def test_user_team_matches_abbreviated_profile_school():
    # The FCS-to-FBS movers' profile rows can spell the school in forms the
    # save's team table does not use ("Sacramento St.", "North Dakota St.");
    # those dynasties silently failed both Scan and one-click Import.
    from backend.saveparse import cfb27
    roster = [_team("Sacramento State", "Hornets"),
              _team("North Dakota State", "Bison"),
              _team("Ohio State", "Buckeyes")]
    for spelled, want in (("Sacramento St.", "Sacramento State"),
                          ("Sacramento St", "Sacramento State"),
                          ("North Dakota St.", "North Dakota State"),
                          ("Ohio State", "Ohio State")):
        t = cfb27._user_team(roster, _slot(spelled), None)
        assert t is not None and t.school == want, (spelled, t)
    # unknown school still resolves to nothing (no false match)
    assert cfb27._user_team(roster, _slot("Delaware"), None) is None


def test_user_team_explicit_pick_beats_unresolvable_slot():
    # The import picker's explicit choice must win over a profile school the
    # roster cannot resolve, so the user always has a recovery path.
    from backend.saveparse import cfb27
    roster = [_team("Sacramento State", "Hornets")]
    t = cfb27._user_team(roster, _slot("Hornets U"), None,
                         user_school="Sacramento State")
    assert t is not None and t.school == "Sacramento State"
