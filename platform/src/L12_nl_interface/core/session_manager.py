"""Session Manager for L12 Natural Language Interface.

This module implements the SessionManager class which handles conversation-scoped
service lifecycle management with lazy initialization, TTL-based expiration, and
memory tracking.

Key features:
- Session-scoped service instances (isolated per conversation)
- Lazy initialization via ServiceFactory
- TTL-based automatic cleanup (default 1 hour)
- Memory monitoring per session
- Background cleanup task
- Session metrics and statistics

Example:
    >>> manager = SessionManager(factory, memory_monitor)
    >>> await manager.start()
    >>> service = await manager.get_service("session-123", "PlanningService")
    >>> await manager.cleanup_session("session-123")
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .service_factory import ServiceFactory
from ..services.memory_monitor import MemoryMonitor

logger = logging.getLogger(__name__)


class SessionInfo:
    """Information about an active session.

    Attributes:
        session_id: Unique session identifier
        created_at: When the session was created
        last_accessed: When the session was last accessed
        service_count: Number of services in this session
        memory_mb: Current memory usage in megabytes
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.service_count = 0
        self.memory_mb = 0.0

    def update_access(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.utcnow()

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if session has exceeded TTL.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if session is expired, False otherwise
        """
        expiry_time = self.last_accessed + timedelta(seconds=ttl_seconds)
        return datetime.utcnow() > expiry_time

    def get_age_seconds(self) -> float:
        """Get session age in seconds.

        Returns:
            Age in seconds since creation
        """
        delta = datetime.utcnow() - self.created_at
        return delta.total_seconds()

    def get_idle_seconds(self) -> float:
        """Get idle time in seconds.

        Returns:
            Idle time in seconds since last access
        """
        delta = datetime.utcnow() - self.last_accessed
        return delta.total_seconds()


class SessionManager:
    """Manager for conversation-scoped service lifecycle.

    The SessionManager handles the lifecycle of service instances within
    conversation sessions. It provides:
    1. Lazy initialization of services via ServiceFactory
    2. TTL-based session expiration and cleanup
    3. Memory monitoring per session
    4. Session isolation (no shared state between sessions)
    5. Background cleanup task for expired sessions

    Attributes:
        factory: ServiceFactory for creating service instances
        memory_monitor: MemoryMonitor for tracking memory usage
        ttl_seconds: Session time-to-live in seconds
        cleanup_interval_seconds: Interval for cleanup task
        sessions: Dict mapping session_id to SessionInfo
        _cleanup_task: Background cleanup task

    Example:
        >>> manager = SessionManager(factory, memory_monitor, ttl_seconds=3600)
        >>> await manager.start()
        >>> service = await manager.get_service("session-123", "PlanningService")
        >>> metrics = manager.get_session_metrics("session-123")
        >>> await manager.stop()
    """

    def __init__(
        self,
        factory: ServiceFactory,
        memory_monitor: MemoryMonitor,
        ttl_seconds: int = 3600,
        cleanup_interval_seconds: int = 300,
    ):
        """Initialize the session manager.

        Args:
            factory: ServiceFactory for creating services
            memory_monitor: MemoryMonitor for memory tracking
            ttl_seconds: Session TTL in seconds (default: 1 hour)
            cleanup_interval_seconds: Cleanup interval in seconds (default: 5 minutes)
        """
        self.factory = factory
        self.memory_monitor = memory_monitor
        self.ttl_seconds = ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.sessions: Dict[str, SessionInfo] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._started = False

        logger.info(
            f"SessionManager initialized: ttl={ttl_seconds}s, "
            f"cleanup_interval={cleanup_interval_seconds}s"
        )

    async def start(self) -> None:
        """Start the session manager and background cleanup task.

        Example:
            >>> await manager.start()
        """
        if self._started:
            logger.warning("SessionManager already started")
            return

        # Start memory monitor if not already started
        self.memory_monitor.start()

        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._started = True
        logger.info("SessionManager started")

    async def stop(self) -> None:
        """Stop the session manager and cleanup all sessions.

        Example:
            >>> await manager.stop()
        """
        if not self._started:
            return

        # Cancel cleanup task
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Cleanup all sessions
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.cleanup_session(session_id)

        # Stop memory monitor
        self.memory_monitor.stop()

        self._started = False
        logger.info("SessionManager stopped")

    async def get_service(
        self,
        session_id: str,
        service_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Get or create a service instance for a session.

        This is the main entry point for accessing services. It:
        1. Creates session if it doesn't exist
        2. Updates session access time
        3. Delegates to ServiceFactory for lazy initialization
        4. Takes memory snapshot after service creation
        5. Returns the service instance

        Args:
            session_id: Session identifier
            service_name: Name of service to get
            config: Optional configuration overrides

        Returns:
            Service instance

        Raises:
            ValueError: If service not found
            Exception: If service creation fails

        Example:
            >>> service = await manager.get_service("session-123", "PlanningService")
            >>> result = await service.create_plan(goal)
        """
        # Ensure session exists
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionInfo(session_id)
            logger.info(f"Created new session: {session_id}")

        # Update access time
        session_info = self.sessions[session_id]
        session_info.update_access()

        # Get or create service via factory
        logger.debug(
            f"Getting service '{service_name}' for session '{session_id}'"
        )
        service = await self.factory.create_service(
            service_name, session_id, config
        )

        # Update session metrics
        cached_services = self.factory.get_cached_services(session_id)
        session_info.service_count = len(cached_services)

        # Take memory snapshot
        snapshot = self.memory_monitor.take_snapshot(session_id)
        if snapshot:
            session_info.memory_mb = snapshot.size_mb

        logger.debug(
            f"Service '{service_name}' ready for session '{session_id}' "
            f"({session_info.service_count} services, {session_info.memory_mb:.2f}MB)"
        )

        return service

    async def cleanup_session(self, session_id: str) -> bool:
        """Cleanup a specific session.

        This removes all cached services for the session and clears
        memory snapshots.

        Args:
            session_id: Session to cleanup

        Returns:
            True if session was cleaned up, False if not found

        Example:
            >>> await manager.cleanup_session("session-123")
        """
        if session_id not in self.sessions:
            logger.debug(f"Session '{session_id}' not found for cleanup")
            return False

        # Get session info for logging
        session_info = self.sessions[session_id]
        age_seconds = session_info.get_age_seconds()
        service_count = session_info.service_count

        # Clear factory cache
        cleared_count = self.factory.clear_session_cache(session_id)

        # Clear memory snapshots
        self.memory_monitor.clear_session(session_id)

        # Remove session info
        del self.sessions[session_id]

        logger.info(
            f"Cleaned up session '{session_id}': "
            f"{cleared_count} services cleared, "
            f"age={age_seconds:.1f}s"
        )

        return True

    async def cleanup_expired_sessions(self) -> int:
        """Cleanup all expired sessions based on TTL.

        Returns:
            Number of sessions cleaned up

        Example:
            >>> count = await manager.cleanup_expired_sessions()
            >>> print(f"Cleaned up {count} expired sessions")
        """
        expired_sessions = [
            session_id
            for session_id, session_info in self.sessions.items()
            if session_info.is_expired(self.ttl_seconds)
        ]

        count = 0
        for session_id in expired_sessions:
            if await self.cleanup_session(session_id):
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    async def _cleanup_loop(self) -> None:
        """Background task for periodic session cleanup.

        This task runs every cleanup_interval_seconds and removes
        expired sessions.
        """
        logger.info("Started session cleanup background task")

        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)

                # Cleanup expired sessions
                count = await self.cleanup_expired_sessions()

                # Check for memory leaks
                for session_id in list(self.sessions.keys()):
                    if self.memory_monitor.detect_leak(session_id):
                        logger.warning(
                            f"Memory leak detected in session '{session_id}'"
                        )

                logger.debug(
                    f"Cleanup cycle complete: {count} sessions cleaned, "
                    f"{len(self.sessions)} active"
                )

            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific session.

        Args:
            session_id: Session to get metrics for

        Returns:
            Dict with session metrics, or None if session not found

        Example:
            >>> metrics = manager.get_session_metrics("session-123")
            >>> print(f"Memory: {metrics['memory_mb']:.2f}MB")
        """
        if session_id not in self.sessions:
            return None

        session_info = self.sessions[session_id]

        # Get memory stats from monitor
        memory_stats = self.memory_monitor.get_session_stats(session_id)

        return {
            "session_id": session_id,
            "created_at": session_info.created_at.isoformat(),
            "last_accessed": session_info.last_accessed.isoformat(),
            "age_seconds": session_info.get_age_seconds(),
            "idle_seconds": session_info.get_idle_seconds(),
            "service_count": session_info.service_count,
            "memory_mb": session_info.memory_mb,
            "memory_peak_mb": memory_stats.get("peak_mb", 0.0),
            "memory_average_mb": memory_stats.get("average_mb", 0.0),
            "is_expired": session_info.is_expired(self.ttl_seconds),
        }

    def get_all_session_metrics(self) -> List[Dict[str, Any]]:
        """Get metrics for all active sessions.

        Returns:
            List of session metrics dicts

        Example:
            >>> all_metrics = manager.get_all_session_metrics()
            >>> for metrics in all_metrics:
            ...     print(f"{metrics['session_id']}: {metrics['service_count']} services")
        """
        return [
            self.get_session_metrics(session_id)
            for session_id in self.sessions.keys()
        ]

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global metrics across all sessions.

        Returns:
            Dict with global metrics

        Example:
            >>> metrics = manager.get_global_metrics()
            >>> print(f"Active sessions: {metrics['active_sessions']}")
        """
        total_services = sum(
            info.service_count for info in self.sessions.values()
        )
        total_memory_mb = sum(
            info.memory_mb for info in self.sessions.values()
        )

        # Get factory cache stats
        factory_stats = self.factory.get_cache_statistics()

        # Get memory monitor stats
        memory_stats = self.memory_monitor.get_global_stats()

        return {
            "active_sessions": len(self.sessions),
            "total_services": total_services,
            "total_memory_mb": total_memory_mb,
            "average_services_per_session": (
                total_services / len(self.sessions) if self.sessions else 0
            ),
            "average_memory_per_session_mb": (
                total_memory_mb / len(self.sessions) if self.sessions else 0
            ),
            "ttl_seconds": self.ttl_seconds,
            "cleanup_interval_seconds": self.cleanup_interval_seconds,
            "factory_cache_size": factory_stats.get("total_cached", 0),
            "memory_monitor_enabled": memory_stats.get("enabled", False),
            "memory_monitor_started": memory_stats.get("started", False),
        }

    def list_sessions(self) -> List[str]:
        """List all active session IDs.

        Returns:
            List of session IDs

        Example:
            >>> sessions = manager.list_sessions()
            >>> print(f"Active sessions: {sessions}")
        """
        return list(self.sessions.keys())

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: Session to check

        Returns:
            True if session exists, False otherwise

        Example:
            >>> if manager.session_exists("session-123"):
            ...     print("Session is active")
        """
        return session_id in self.sessions

    def get_session_age(self, session_id: str) -> Optional[float]:
        """Get age of a session in seconds.

        Args:
            session_id: Session to query

        Returns:
            Age in seconds, or None if session not found

        Example:
            >>> age = manager.get_session_age("session-123")
            >>> print(f"Session age: {age:.1f}s")
        """
        if session_id not in self.sessions:
            return None
        return self.sessions[session_id].get_age_seconds()

    async def refresh_session(self, session_id: str) -> bool:
        """Refresh a session's access time to prevent expiration.

        Args:
            session_id: Session to refresh

        Returns:
            True if refreshed, False if session not found

        Example:
            >>> await manager.refresh_session("session-123")
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id].update_access()
        logger.debug(f"Refreshed session '{session_id}'")
        return True
