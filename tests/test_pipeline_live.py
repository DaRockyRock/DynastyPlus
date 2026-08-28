"""load_live_dynasty: the playoff sync's view of the world must be the SAVE's
own current week, never an archived snapshot served through a lagging app
pointer (the stale-freeze bug: fields frozen with pre-CCG rankings and
projected champions instead of the real CCG winners)."""
from backend import confsetup, pipeline


def test_load_live_dynasty_prefers_save_week(monkeypatch):
    live = {"season": {"year": 2026, "week": 17}, "meta": {"dynasty_id": "x"}}
    monkeypatch.setattr(pipeline, "_read_save", lambda: dict(live))
    monkeypatch.setattr(pipeline, "_archive", lambda *a, **k: None)
    monkeypatch.setattr(confsetup, "apply_overlay", lambda d: d)
    # the pointer lags at the CCG week; the live save is at bowl week
    monkeypatch.setattr(pipeline, "current_pointer",
                        lambda: {"year": 2026, "week": 14})
    out = pipeline.load_live_dynasty()
    assert out["season"]["week"] == 17


def test_load_live_dynasty_falls_back_to_pointer(monkeypatch):
    monkeypatch.setattr(pipeline, "_read_save", lambda: None)
    monkeypatch.setattr(pipeline, "current_pointer",
                        lambda: {"year": 2025, "week": 9})
    monkeypatch.setattr(pipeline, "load_dynasty",
                        lambda y, w: {"year": y, "week": w})
    assert pipeline.load_live_dynasty() == {"year": 2025, "week": 9}
