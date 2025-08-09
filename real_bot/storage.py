# real_bot/storage.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional

# data dir next to this file: real_bot/data/guilds.json
DATA_DIR = Path(__file__).parent / "data"
GUILDS_FILE = DATA_DIR / "guilds.json"

def ensure_storage() -> None:
    """Ensure storage folder and JSON file exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not GUILDS_FILE.exists():
        GUILDS_FILE.write_text("{}", encoding="utf-8")

def _load() -> Dict[str, Any]:
    ensure_storage()
    try:
        return json.loads(GUILDS_FILE.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}

def _save(data: Dict[str, Any]) -> None:
    ensure_storage()
    GUILDS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_channel_id(guild_id: int) -> Optional[int]:
    data = _load()
    entry = data.get(str(guild_id))
    if not entry:
        return None
    cid = entry.get("channel_id")
    return int(cid) if cid is not None else None

def set_channel_id(guild_id: int, channel_id: int) -> None:
    data = _load()
    data[str(guild_id)] = {"channel_id": int(channel_id)}
    _save(data)

def dump_all() -> Dict[str, Any]:
    """Return the raw dict for debug/!showdb style commands."""
    return _load()

def delete_by_guild(guild_id: int) -> bool:
    """Remove a guild's record; returns True if deleted."""
    data = _load()
    removed = data.pop(str(guild_id), None) is not None
    if removed:
        _save(data)
    return removed

def delete_where_value_matches(substr: str) -> int:
    """Delete any entries whose stringified value contains substr."""
    data = _load()
    to_delete = [k for k, v in data.items() if substr in json.dumps(v)]
    for k in to_delete:
        data.pop(k, None)
    if to_delete:
        _save(data)
    return len(to_delete)
