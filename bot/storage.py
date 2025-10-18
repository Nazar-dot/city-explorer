from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional


@dataclass
class WatchEntry:
    """Represents a single Upwork search watch."""

    name: str
    url: str
    last_seen_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, name: str, data: MutableMapping[str, object]) -> "WatchEntry":
        return cls(
            name=name,
            url=str(data.get("url", "")),
            last_seen_ids=list(data.get("last_seen_ids", [])),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "url": self.url,
            "last_seen_ids": list(self.last_seen_ids),
        }


class Storage:
    """Async-safe JSON storage for chat-specific watch configuration."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._data: Dict[str, Dict[str, Dict[str, object]]] = {"chats": {}}

    async def load(self) -> None:
        async with self._lock:
            if not self._path.exists():
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._write_locked()
                return

            with self._path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
                if not isinstance(raw, dict):
                    raise ValueError("Storage file is not a JSON object")
                self._data = raw

            # Normalise structure
            self._data.setdefault("chats", {})

    async def save(self) -> None:
        async with self._lock:
            self._write_locked()

    async def list_watches(self, chat_id: int) -> List[WatchEntry]:
        async with self._lock:
            watches = self._chat(chat_id).get("watches", {})
            return [WatchEntry.from_dict(name, data) for name, data in watches.items()]

    async def all_watches(self) -> Dict[int, List[WatchEntry]]:
        async with self._lock:
            result: Dict[int, List[WatchEntry]] = {}
            for chat_id_str, chat_data in self._data.get("chats", {}).items():
                watches_data = chat_data.get("watches", {})
                result[int(chat_id_str)] = [
                    WatchEntry.from_dict(name, data) for name, data in watches_data.items()
                ]
            return result

    async def add_watch(self, chat_id: int, name: str, url: str, last_seen_ids: Optional[Iterable[str]] = None) -> WatchEntry:
        async with self._lock:
            chat = self._chat(chat_id)
            watches = chat.setdefault("watches", {})
            if name in watches:
                raise ValueError(f"A watch named '{name}' already exists")
            entry = WatchEntry(name=name, url=url, last_seen_ids=list(last_seen_ids or []))
            watches[name] = entry.to_dict()
            self._write_locked()
            return entry

    async def update_watch(self, chat_id: int, entry: WatchEntry) -> None:
        async with self._lock:
            chat = self._chat(chat_id)
            watches = chat.setdefault("watches", {})
            watches[entry.name] = entry.to_dict()
            self._write_locked()

    async def remove_watch(self, chat_id: int, name: str) -> bool:
        async with self._lock:
            chat = self._chat(chat_id)
            watches = chat.setdefault("watches", {})
            removed = watches.pop(name, None) is not None
            if removed:
                self._write_locked()
            return removed

    async def get_watch(self, chat_id: int, name: str) -> Optional[WatchEntry]:
        async with self._lock:
            watches = self._chat(chat_id).get("watches", {})
            data = watches.get(name)
            return WatchEntry.from_dict(name, data) if data else None

    def _chat(self, chat_id: int) -> Dict[str, Dict[str, object]]:
        chats = self._data.setdefault("chats", {})
        return chats.setdefault(str(chat_id), {})

    def _write_locked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, sort_keys=True)
            fh.write("\n")


__all__ = ["Storage", "WatchEntry"]
