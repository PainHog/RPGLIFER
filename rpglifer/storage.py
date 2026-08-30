"""Where a character is saved, and how.

The save is a single human-readable JSON file in the per-user application data
directory:

* Windows: ``%APPDATA%\\RPGLifer\\save.json``
* macOS:   ``~/Library/Application Support/RPGLifer/save.json``
* Linux:   ``$XDG_DATA_HOME/rpglifer/save.json`` (else ``~/.local/share/...``)

Set ``RPGLIFER_DATA_DIR`` to override the location (handy for tests and portable
installs). Loading is defensive: a missing file yields a fresh character, and a
corrupt file is set aside as ``save.corrupt-<timestamp>.json`` rather than lost.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from .character import Character

APP_DIR_NAME = "RPGLifer"
SAVE_FILENAME = "save.json"
ENV_OVERRIDE = "RPGLIFER_DATA_DIR"


def data_dir() -> Path:
    """Return the directory that holds the save file (created if missing)."""
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        path = Path(override).expanduser()
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        path = Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
        path = Path(base) / "rpglifer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_path() -> Path:
    return data_dir() / SAVE_FILENAME


def load() -> Character:
    """Load the saved character, or return a fresh one if none exists."""
    path = save_path()
    if not path.exists():
        return Character()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Character.from_dict(data)
    except (json.JSONDecodeError, ValueError, TypeError, OSError):
        _quarantine(path)
        return Character()


def save(character: Character) -> Path:
    """Write ``character`` to disk atomically and return the save path."""
    path = save_path()
    tmp = path.with_suffix(".json.tmp")
    payload = json.dumps(character.to_dict(), indent=2, ensure_ascii=False)
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)  # atomic on the same filesystem
    return path


def backup() -> Path | None:
    """Copy the current save to ``save.backup-<timestamp>.json`` beside it.

    Returns the backup's path, or ``None`` if there is no save yet. A plain file
    copy so the original keeps being the live save — peace of mind for a
    local-only tracker.
    """
    src = save_path()
    if not src.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = src.with_name(f"save.backup-{stamp}.json")
    shutil.copy2(src, dst)
    return dst


def _quarantine(path: Path) -> None:
    """Move an unreadable save aside so a fresh one can take its place."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"save.corrupt-{stamp}.json")
    try:
        os.replace(path, backup)
    except OSError:
        pass
