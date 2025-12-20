"""
System Log Service
Centralized, structured log stream for UI "System Logs" (event-driven via Qt signals).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass(frozen=True)
class SystemLogEntry:
    timestamp: str  # "YYYY-MM-DD HH:MM:SS"
    log_type: str  # TRADING | MESSAGE | WARNING | ERROR | ATTENTION
    message: str
    user: str = ""
    strategy: str = ""
    portfolio: str = ""


class SystemLogService(QObject):
    """
    Stores a rolling list of structured log entries and notifies listeners in real time.
    """

    log_added = pyqtSignal(object)  # SystemLogEntry
    logs_cleared = pyqtSignal()

    def __init__(self, max_entries: int = 2000):
        super().__init__()
        self._max_entries = int(max_entries)
        self._entries: List[SystemLogEntry] = []

    def clear(self) -> None:
        self._entries.clear()
        self.logs_cleared.emit()

    def get_entries(self) -> List[SystemLogEntry]:
        return list(self._entries)

    def log(
        self,
        log_type: str,
        message: str,
        user: Optional[str] = None,
        strategy: Optional[str] = None,
        portfolio: Optional[str] = None,
    ) -> SystemLogEntry:
        entry = SystemLogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            log_type=(log_type or "MESSAGE").upper(),
            message=str(message),
            user=(user or ""),
            strategy=(strategy or ""),
            portfolio=(portfolio or ""),
        )

        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

        self.log_added.emit(entry)
        return entry


# Global singleton (importable from all pages)
system_log_service = SystemLogService()


