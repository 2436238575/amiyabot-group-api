"""Shared in-process game state for Amiya plugins and bridge clients."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class GameSession:
    group_id: str
    plugin_id: str
    plugin_name: str
    game_id: str
    started_at: float
    last_activity: float
    expires_at: float | None = None
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GameSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._generation = 0
        self._lock = threading.RLock()

    def _bump(self) -> None:
        self._generation += 1

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def start(self, group_id: int | str, plugin_id: str,
              plugin_name: str = "", game_id: str | None = None,
              timeout: float | None = None) -> str:
        now = time.time()
        identifier = game_id or uuid.uuid4().hex
        with self._lock:
            self._sessions[identifier] = GameSession(
                group_id=str(group_id), plugin_id=str(plugin_id),
                plugin_name=plugin_name or plugin_id, game_id=identifier,
                started_at=now, last_activity=now,
                expires_at=now + timeout if timeout and timeout > 0 else None,
            )
            self._bump()
        return identifier

    def touch(self, game_id: str, timeout: float | None = None) -> bool:
        now = time.time()
        with self._lock:
            session = self._sessions.get(str(game_id))
            if not session or session.status != "active":
                return False
            session.last_activity = now
            if timeout and timeout > 0:
                session.expires_at = now + timeout
            self._bump()
            return True

    def finish(self, game_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(str(game_id), None)
            if session is None:
                return False
            session.status = "finished"
            self._bump()
            return True

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._bump()

    def snapshot(self) -> list[dict[str, Any]]:
        now = time.time()
        with self._lock:
            expired = [
                key for key, item in self._sessions.items()
                if item.expires_at is not None and item.expires_at <= now
            ]
            if expired:
                for key in expired:
                    self._sessions.pop(key, None)
                self._bump()
            return [
                item.to_dict() for item in self._sessions.values()
                if item.status == "active"
            ]


game_registry = GameSessionRegistry()
start_game = game_registry.start
touch_game = game_registry.touch
finish_game = game_registry.finish
