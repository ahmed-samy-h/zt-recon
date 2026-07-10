import json
import os
import hashlib

SESSION_DIR = "/tmp/.zt_sessions"


def _ensure_dir():
    os.makedirs(SESSION_DIR, mode=0o700, exist_ok=True)


def _session_path(target):
    """Builds a deterministic, collision-safe file path per target using MD5."""
    _ensure_dir()
    target_hash = hashlib.md5(target.encode("utf-8")).hexdigest()
    return os.path.join(SESSION_DIR, f"{target_hash}.json")


def save_session(target, state_data):
    """Saves the current scan state for a specific target."""
    path = _session_path(target)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state_data, f, indent=4)
    os.replace(tmp_path, path)


def load_session(target):
    """Loads a previous session for a specific target, if it exists."""
    path = _session_path(target)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def clear_session(target):
    """Clears the session file for a specific target after a successful run."""
    path = _session_path(target)
    if os.path.exists(path):
        os.remove(path)


def list_active_sessions():
    """Utility: lists all targets that currently have an unfinished session."""
    _ensure_dir()
    return [f for f in os.listdir(SESSION_DIR) if f.endswith(".json")]