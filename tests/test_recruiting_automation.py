"""Ordering checks for the shared weekly save automation chain."""

from backend import app_settings, playoff_live, polledit, recruiting_fix


def test_recruiting_tool_defaults_to_off():
    assert recruiting_fix._default_config()["enabled"] is False


def test_weekly_tools_run_in_order_and_can_wait(monkeypatch):
    calls = []
    monkeypatch.setattr(app_settings, "autosync_enabled", lambda: True)
    monkeypatch.setattr(recruiting_fix, "is_enabled", lambda: True)
    monkeypatch.setattr(
        recruiting_fix, "auto_apply",
        lambda path=None: calls.append(("recruiting", path)) or {"written": False},
    )
    monkeypatch.setattr(
        recruiting_fix, "mark_shared_tools",
        lambda: calls.append(("tools", None)) or {},
    )
    monkeypatch.setattr(
        recruiting_fix, "finish_shared_tools",
        lambda: calls.append(("complete", None)) or {},
    )
    monkeypatch.setattr(
        playoff_live, "sync",
        lambda *, write: calls.append(("playoff", write)) or {"status": "ready"},
    )
    monkeypatch.setattr(
        polledit, "auto_apply",
        lambda: calls.append(("polls", None)) or {"changed": {}},
    )

    playoff_live._on_saves_changed("DYNASTY-AUTOSAVE", wait=True)

    assert calls == [
        ("recruiting", "DYNASTY-AUTOSAVE"),
        ("tools", None),
        ("playoff", False),
        ("polls", None),
        ("complete", None),
    ]


def test_explicit_scan_does_not_repeat_recruiting(monkeypatch):
    calls = []
    monkeypatch.setattr(app_settings, "autosync_enabled", lambda: True)
    monkeypatch.setattr(recruiting_fix, "is_enabled", lambda: True)
    monkeypatch.setattr(
        recruiting_fix, "auto_apply",
        lambda path=None: calls.append("recruiting") or {"written": False},
    )
    monkeypatch.setattr(recruiting_fix, "mark_shared_tools", lambda: calls.append("tools") or {})
    monkeypatch.setattr(recruiting_fix, "finish_shared_tools", lambda: calls.append("complete") or {})
    monkeypatch.setattr(playoff_live, "sync", lambda *, write: {"status": "ready"})
    monkeypatch.setattr(polledit, "auto_apply", lambda: {"changed": {}})

    playoff_live._on_saves_changed(recruiting_done=True, wait=True)

    assert calls == ["tools", "complete"]
    assert "recruiting" not in calls


def test_disabled_tool_never_opens_or_writes_the_save(monkeypatch):
    monkeypatch.setattr(recruiting_fix, "get_config", lambda: {"enabled": False})
    monkeypatch.setattr(
        recruiting_fix.confsetup, "_read_table",
        lambda: (_ for _ in ()).throw(AssertionError("disabled tool read the save")),
    )

    result = recruiting_fix.apply_to_current_save()

    assert result["written"] is False
    assert result["reason"] == "recruiting correction is off"


def test_disabled_tool_runs_other_syncs_without_recruiting_progress(monkeypatch):
    calls = []
    monkeypatch.setattr(app_settings, "autosync_enabled", lambda: True)
    monkeypatch.setattr(recruiting_fix, "is_enabled", lambda: False)
    monkeypatch.setattr(
        recruiting_fix, "auto_apply",
        lambda path=None: calls.append("recruiting") or {"written": False},
    )
    monkeypatch.setattr(recruiting_fix, "mark_shared_tools", lambda: calls.append("tools") or {})
    monkeypatch.setattr(recruiting_fix, "finish_shared_tools", lambda: calls.append("complete") or {})
    monkeypatch.setattr(playoff_live, "sync", lambda *, write: calls.append("playoff") or {"status": "ready"})
    monkeypatch.setattr(polledit, "auto_apply", lambda: calls.append("polls") or {"changed": {}})

    playoff_live._on_saves_changed("DYNASTY-AUTOSAVE", wait=True)

    assert calls == ["playoff", "polls"]
