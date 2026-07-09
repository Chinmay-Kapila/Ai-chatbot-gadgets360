"""
In-memory session service.

No login system, no database. Each session is identified by a randomly
generated session_id and holds only the last N messages (default 5).
Sessions are deleted after a period of inactivity via a background
cleanup task started at application startup.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.config.settings import settings
from app.models.schemas import SessionData, SessionMessage
from app.utils.helpers import new_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionService:
    """Manages temporary, in-memory chat sessions."""

    def __init__(self, max_messages: int = None, ttl_seconds: int = None):
        self._sessions: Dict[str, SessionData] = {}
        self._lock = asyncio.Lock()
        self.max_messages = max_messages or settings.SESSION_MAX_MESSAGES
        self.ttl_seconds = ttl_seconds or settings.SESSION_INACTIVITY_TTL_SECONDS

    async def get_or_create_session(self, session_id: Optional[str]) -> SessionData:
        """Fetch an existing session or create a new one if not found/expired."""
        async with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if self._is_expired(session):
                    logger.info("Session %s expired, creating a new one.", session_id)
                    del self._sessions[session_id]
                else:
                    return session

            new_session_id = session_id or new_id(prefix="sess_")
            session = SessionData(session_id=new_session_id, messages=[])
            self._sessions[new_session_id] = session
            return session

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session, trimming to the last N messages."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = SessionData(session_id=session_id, messages=[])
                self._sessions[session_id] = session

            session.messages.append(SessionMessage(role=role, content=content))
            session.messages = session.messages[-self.max_messages:]
            session.last_active = datetime.utcnow()

    async def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Return the session's message history as plain dicts."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            return [{"role": m.role, "content": m.content} for m in session.messages]

    def _is_expired(self, session: SessionData) -> bool:
        expiry_time = session.last_active + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time

    async def cleanup_expired_sessions(self) -> int:
        """Remove all sessions that have exceeded their inactivity TTL."""
        async with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items() if self._is_expired(session)
            ]
            for sid in expired_ids:
                del self._sessions[sid]

            if expired_ids:
                logger.info("Cleaned up %d expired session(s).", len(expired_ids))

            return len(expired_ids)

    async def session_count(self) -> int:
        async with self._lock:
            return len(self._sessions)


# Singleton session service instance shared across the app.
session_service = SessionService()


async def start_session_cleanup_task() -> None:
    """Background task that periodically purges expired sessions."""
    while True:
        await asyncio.sleep(settings.SESSION_CLEANUP_INTERVAL_SECONDS)
        try:
            await session_service.cleanup_expired_sessions()
        except Exception as exc:  # noqa: BLE001
            logger.error("Session cleanup task error: %s", exc)
