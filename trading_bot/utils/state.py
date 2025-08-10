import os
from pathlib import Path


def default_state_dir() -> str:
    """Return the default directory for runtime state."""
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Roaming")
        return os.path.join(base, "trading-bot")
    base = os.environ.get("XDG_STATE_HOME")
    if not base:
        base = str(Path.home() / ".local" / "state")
    return os.path.join(base, "trading-bot")
