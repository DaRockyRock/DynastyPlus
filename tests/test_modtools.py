"""MMC Modding Tools detection: tools folder resolution, anti-cheat swap
state, and the .fbmod handoff into the manager's mod library."""
import pytest

from backend import app_settings, modtools


@pytest.fixture
def tools_dir(tmp_path):
    """A fake extracted MMC_Modding_Tools folder (nested like the archive)."""
    manager = tmp_path / "tools" / "MMC_ModManager_v1.1.0.0"
    manager.mkdir(parents=True)
    (manager / modtools.MANAGER_EXE).write_bytes(b"exe")
    return tmp_path / "tools"


@pytest.fixture
def game_root(tmp_path):
    root = tmp_path / "game"
    root.mkdir()
    return root


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Never read or write the real app_settings.json / user folders."""
    monkeypatch.setattr(app_settings, "_STORE_FILE", tmp_path / "app_settings.json")
    monkeypatch.setattr(modtools, "discover", lambda: None)


def test_not_found_without_path(game_root, monkeypatch):
    monkeypatch.setattr(app_settings, "resolve_game_root", lambda: game_root)
    st = modtools.status()
    assert st["tools_found"] is False
    assert st["ready"] is False
    assert st["anticheat"] == "unknown"  # no launcher in the fake game root


def test_set_path_validates_and_detects(tools_dir, game_root, monkeypatch):
    monkeypatch.setattr(app_settings, "resolve_game_root", lambda: game_root)
    with pytest.raises(ValueError):
        modtools.set_path(str(tools_dir.parent / "nope"))
    with pytest.raises(ValueError):
        modtools.set_path(str(game_root))  # exists but has no manager exe

    st = modtools.set_path(str(tools_dir))
    assert st["tools_found"] is True
    assert st["tools_path_set"] is True
    assert st["manager_exe"].endswith(modtools.MANAGER_EXE)
    assert st["mods_dir"].endswith(modtools.PROFILE_NAME)

    # "" clears back to auto-discovery (stubbed to None here)
    st = modtools.set_path("")
    assert st["tools_found"] is False


def test_anticheat_states(tools_dir, game_root, monkeypatch):
    monkeypatch.setattr(app_settings, "resolve_game_root", lambda: game_root)
    modtools.set_path(str(tools_dir))

    ac = game_root / modtools.AC_EXE
    ac.write_bytes(b"\0" * (17 * 1024 * 1024))  # EA's real launcher size
    st = modtools.status()
    assert st["anticheat"] == "original"
    assert st["ready"] is False

    ac.write_bytes(b"\0" * (95 * 1024))         # the MMC stub
    (game_root / modtools.AC_BACKUPS[0]).write_bytes(b"\0")
    st = modtools.status()
    assert st["anticheat"] == "stub"
    assert st["anticheat_backup"] is True
    assert st["ready"] is True


def test_install_fbmod(tools_dir, tmp_path, monkeypatch):
    modtools.set_path(str(tools_dir))
    src = tmp_path / "DynastyPlus Conference Logos.fbmod"
    src.write_bytes(b"FBMOD")
    dest = modtools.install_fbmod(src)
    assert dest.exists()
    assert dest.parent.name == modtools.PROFILE_NAME
    assert dest.read_bytes() == b"FBMOD"
    assert "DynastyPlus Conference Logos.fbmod" in modtools.status()["installed_mods"]


def test_install_without_tools_raises(tmp_path):
    src = tmp_path / "x.fbmod"
    src.write_bytes(b"x")
    with pytest.raises(ValueError):
        modtools.install_fbmod(src)
