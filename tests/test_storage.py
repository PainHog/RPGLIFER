import json

from rpglifer import storage
from rpglifer.activities import activity_by_name
from rpglifer.character import Character


def test_data_dir_honors_override(tmp_path, monkeypatch):
    monkeypatch.setenv(storage.ENV_OVERRIDE, str(tmp_path))
    assert storage.data_dir() == tmp_path


def test_load_returns_fresh_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv(storage.ENV_OVERRIDE, str(tmp_path))
    c = storage.load()
    assert isinstance(c, Character)
    assert c.total_xp() == 0


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv(storage.ENV_OVERRIDE, str(tmp_path))
    c = Character(name="Saver")
    c.log_activity(activity_by_name("Meditation"), minutes=25)
    path = storage.save(c)
    assert path.exists()

    loaded = storage.load()
    assert loaded.name == "Saver"
    assert loaded.stat_xp["WIS"] == c.stat_xp["WIS"]
    assert len(loaded.log) == 1


def test_corrupt_save_is_quarantined_not_lost(tmp_path, monkeypatch):
    monkeypatch.setenv(storage.ENV_OVERRIDE, str(tmp_path))
    storage.save_path().write_text("{ this is not valid json", encoding="utf-8")

    loaded = storage.load()  # should not raise
    assert isinstance(loaded, Character)
    assert loaded.total_xp() == 0
    # A quarantine copy should now exist.
    corrupt = list(tmp_path.glob("save.corrupt-*.json"))
    assert len(corrupt) == 1


def test_save_is_valid_json(tmp_path, monkeypatch):
    monkeypatch.setenv(storage.ENV_OVERRIDE, str(tmp_path))
    c = Character(name="JSON")
    storage.save(c)
    data = json.loads(storage.save_path().read_text(encoding="utf-8"))
    assert data["name"] == "JSON"
    assert data["schema"] == 2


def test_backup_copies_the_save(tmp_path, monkeypatch):
    import json as _json
    from rpglifer import storage
    from rpglifer.character import Character
    monkeypatch.setenv("RPGLIFER_DATA_DIR", str(tmp_path))
    c = Character(name="Backup Hero")
    from rpglifer.activities import activity_by_name
    c.log_activity(activity_by_name("Reading"), 30)
    storage.save(c)
    dst = storage.backup()
    assert dst is not None and dst.exists()
    assert dst.name.startswith("save.backup-")
    # The backup is a faithful copy that reloads to an equivalent character.
    data = _json.loads(dst.read_text(encoding="utf-8"))
    restored = Character.from_dict(data)
    assert restored.name == "Backup Hero"
    assert restored.overall_level() == c.overall_level()
    # The live save is untouched.
    assert storage.save_path().exists()


def test_backup_without_save_returns_none(tmp_path, monkeypatch):
    from rpglifer import storage
    monkeypatch.setenv("RPGLIFER_DATA_DIR", str(tmp_path))
    # Nothing saved yet.
    assert storage.backup() is None
