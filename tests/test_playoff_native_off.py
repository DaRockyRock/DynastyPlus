"""The custom playoff automation is opt-in: OFF by default, and OFF means CFB 27
runs its own native playoff while Dynasty+ writes nothing to the bracket."""

import contextlib

from backend import app_settings, dynasty_paths, playoff_live, polledit


@contextlib.contextmanager
def _dynasty(name):
    """Bind a clean per-dynasty playoff dir for one test."""
    with dynasty_paths.bind_current(name):
        for path in (playoff_live._config_path(), playoff_live._state_path()):
            if path.exists():
                path.unlink()
        yield


def test_defaults_to_off():
    with _dynasty("pnoff-default"):
        assert playoff_live.get_config() == {"enabled": False}
        assert playoff_live.is_enabled() is False


def test_active_run_is_not_stranded_until_the_user_chooses():
    with _dynasty("pnoff-active"):
        playoff_live._save_state({"status": "in_progress"})
        # No explicit choice yet: an in-flight bracket keeps running so shipping
        # the opt-in default never strands a playoff mid-season.
        assert playoff_live.is_enabled() is True
        # Once the user turns it off, that wins over the active-run default.
        playoff_live.set_config({"enabled": False})
        assert playoff_live.is_enabled() is False


def test_set_config_persists():
    with _dynasty("pnoff-persist"):
        assert playoff_live.set_config({"enabled": True}) == {"enabled": True}
        assert playoff_live.is_enabled() is True
        playoff_live.set_config({"enabled": False})
        assert playoff_live.is_enabled() is False


def test_sync_off_is_a_strict_no_op(monkeypatch):
    with _dynasty("pnoff-sync"):
        playoff_live.set_config({"enabled": False})
        monkeypatch.setattr(playoff_live.confsetup, "current_payload", lambda: None)

        def _boom(*_a, **_k):
            raise AssertionError("_sync_locked must not run while the tool is off")

        monkeypatch.setattr(playoff_live, "_sync_locked", _boom)
        # Even the manual "update dynasty file" apply (write=True) writes nothing.
        out = playoff_live.sync(write=True)
        assert out["status"] == "native"
        assert out["enabled"] is False
        assert out["needs_write"] is False
        assert out["save_written"] is False


def test_poll_hold_lifts_when_playoff_is_off(monkeypatch):
    with _dynasty("pnoff-hold"):
        monkeypatch.setattr(app_settings, "autosync_enabled", lambda: True)
        # A bracket that WOULD normally own the committee ranking, but with the
        # automation off the user's custom poll is authoritative and nothing holds.
        playoff_live._save_state({"status": "in_progress"})
        playoff_live.set_config({"enabled": False})
        assert polledit._playoff_hold() is None
