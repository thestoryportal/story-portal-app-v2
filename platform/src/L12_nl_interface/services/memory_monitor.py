"""Memory Monitor for L12 Natural Language Interface.

This module implements memory tracking and leak detection for L12 sessions.
Uses tracemalloc for precise memory profiling per session to prevent leaks.

Key features:
- Per-session memory tracking
- Memory leak detection
- Configurable memory limits
- Automatic alerts on threshold breach
"""

import asyncio
import logging
import tracemalloc
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MemorySnapshot:
    """Snapshot of memory usage at a point in time.

    Attributes:
        timestamp: When snapshot was taken
        size_mb: Memory size in megabytes
        count: Number of allocated objects
        traceback: Optional traceback for debugging
    """

    def __init__(
        self,
        timestamp: datetime,
        size_mb: float,
        count: int,
        traceback: Optional[str] = None,
    ):
        self.timestamp = timestamp
        self.size_mb = size_mb
        self.count = count
        self.traceback = traceback


class MemoryMonitor:
    """Memory monitor for session-scoped memory tracking and leak detection.

    The MemoryMonitor tracks memory usage per session to detect leaks and
    enforce memory limits. It uses Python's tracemalloc for precise tracking.

    Attributes:
        enabled: Whether monitoring is enabled
        memory_limit_mb: Per-session memory limit in MB
        snapshots: Dict mapping session_id to list of snapshots
        started: Whether tracemalloc is started

    Example:
        >>> monitor = MemoryMonitor(memory_limit_mb=500)
        >>> monitor.start()
        >>> monitor.take_snapshot("session-123")
        >>> stats = monitor.get_session_stats("session-123")
        >>> print(f"Memory: {stats['current_mb']:.2f} MB")
    """

    def __init__(
        self,
        enabled: bool = True,
        memory_limit_mb: float = 500.0,
        snapshot_interval_seconds: int = 60,
    ):
        """Initialize memory monitor.

        Args:
            enabled: Whether to enable monitoring
            memory_limit_mb: Per-session memory limit in MB
            snapshot_interval_seconds: Interval for automatic snapshots
        """
        self.enabled = enabled
        self.memory_limit_mb = memory_limit_mb
        self.snapshot_interval_seconds = snapshot_interval_seconds
        self.snapshots: Dict[str, list[MemorySnapshot]] = {}
        self.started = False
        self._snapshot_task: Optional[asyncio.Task] = None

        if self.enabled:
            logger.info(
                f"MemoryMonitor initialized: limit={memory_limit_mb}MB, "
                f"interval={snapshot_interval_seconds}s"
            )
        else:
            logger.info("MemoryMonitor disabled")

    def start(self) -> None:
        """Start memory tracking with tracemalloc.

        Example:
            >>> monitor.start()
        """
        if not self.enabled:
            logger.debug("MemoryMonitor disabled, not starting")
            return

        if self.started:
            logger.warning("MemoryMonitor already started")
            return

        try:
            tracemalloc.start()
            self.started = True
            logger.info("MemoryMonitor started tracemalloc")
        except Exception as e:
            logger.error(f"Failed to start tracemalloc: {e}")
            self.enabled = False

    def stop(self) -> None:
        """Stop memory tracking.

        Example:
            >>> monitor.stop()
        """
        if not self.enabled or not self.started:
            return

        try:
            tracemalloc.stop()
            self.started = False
            logger.info("MemoryMonitor stopped tracemalloc")
        except Exception as e:
            logger.error(f"Failed to stop tracemalloc: {e}")

    def take_snapshot(self, session_id: str) -> Optional[MemorySnapshot]:
        """Take a memory snapshot for a session.

        Args:
            session_id: Session to snapshot

        Returns:
            MemorySnapshot if successful, None if monitoring disabled

        Example:
            >>> snapshot = monitor.take_snapshot("session-123")
            >>> print(f"Memory: {snapshot.size_mb:.2f} MB")
        """
        if not self.enabled or not self.started:
            return None

        try:
            # Get current memory statistics
            snapshot = tracemalloc.take_snapshot()
            statistics = snapshot.statistics("lineno")

            # Calculate total size
            total_size_bytes = sum(stat.size for stat in statistics)
            total_size_mb = total_size_bytes / (1024 * 1024)
            total_count = sum(stat.count for stat in statistics)

            # Create snapshot object
            memory_snapshot = MemorySnapshot(
                timestamp=datetime.utcnow(),
                size_mb=total_size_mb,
                count=total_count,
            )

            # Store in session snapshots
            if session_id not in self.snapshots:
                self.snapshots[session_id] = []
            self.snapshots[session_id].append(memory_snapshot)

            # Check if over limit
            if total_size_mb > self.memory_limit_mb:
                logger.warning(
                    f"Session '{session_id}' exceeds memory limit: "
                    f"{total_size_mb:.2f}MB > {self.memory_limit_mb}MB"
                )

            logger.debug(
                f"Memory snapshot for session '{session_id}': "
                f"{total_size_mb:.2f}MB, {total_count} objects"
            )

            return memory_snapshot

        except Exception as e:
            logger.error(f"Failed to take snapshot for session '{session_id}': {e}")
            return None

    def get_session_stats(self, session_id: str) -> Dict[str, any]:
        """Get memory statistics for a session.

        Args:
            session_id: Session to get stats for

        Returns:
            Dict with current_mb, peak_mb, average_mb, snapshot_count

        Example:
            >>> stats = monitor.get_session_stats("session-123")
            >>> print(f"Peak: {stats['peak_mb']:.2f} MB")
        """
        if session_id not in self.snapshots or not self.snapshots[session_id]:
            return {
                "current_mb": 0.0,
                "peak_mb": 0.0,
                "average_mb": 0.0,
                "snapshot_count": 0,
                "over_limit": False,
            }

        snapshots = self.snapshots[session_id]
        sizes = [s.size_mb for s in snapshots]

        current_mb = sizes[-1] if sizes else 0.0
        peak_mb = max(sizes) if sizes else 0.0
        average_mb = sum(sizes) / len(sizes) if sizes else 0.0

        return {
            "current_mb": current_mb,
            "peak_mb": peak_mb,
            "average_mb": average_mb,
            "snapshot_count": len(snapshots),
            "over_limit": current_mb > self.memory_limit_mb,
        }

    def detect_leak(self, session_id: str, threshold_mb: float = 50.0) -> bool:
        """Detect potential memory leak for a session.

        A leak is detected if memory usage has grown by threshold_mb
        between the first and last snapshot.

        Args:
            session_id: Session to check
            threshold_mb: Growth threshold in MB

        Returns:
            True if leak detected, False otherwise

        Example:
            >>> if monitor.detect_leak("session-123", threshold_mb=100):
            ...     print("Memory leak detected!")
        """
        if session_id not in self.snapshots or len(self.snapshots[session_id]) < 2:
            return False

        snapshots = self.snapshots[session_id]
        first_size = snapshots[0].size_mb
        last_size = snapshots[-1].size_mb
        growth = last_size - first_size

        if growth > threshold_mb:
            logger.warning(
                f"Potential memory leak detected for session '{session_id}': "
                f"growth of {growth:.2f}MB (from {first_size:.2f}MB to {last_size:.2f}MB)"
            )
            return True

        return False

    def clear_session(self, session_id: str) -> None:
        """Clear snapshots for a session.

        Args:
            session_id: Session to clear

        Example:
            >>> monitor.clear_session("session-123")
        """
        if session_id in self.snapshots:
            count = len(self.snapshots[session_id])
            del self.snapshots[session_id]
            logger.debug(f"Cleared {count} snapshots for session '{session_id}'")

    def get_global_stats(self) -> Dict[str, any]:
        """Get global memory statistics across all sessions.

        Returns:
            Dict with total_sessions, total_snapshots, total_mb, peak_mb

        Example:
            >>> stats = monitor.get_global_stats()
            >>> print(f"Total memory: {stats['total_mb']:.2f} MB")
        """
        total_sessions = len(self.snapshots)
        total_snapshots = sum(len(snapshots) for snapshots in self.snapshots.values())

        all_sizes = [
            snapshot.size_mb
            for snapshots in self.snapshots.values()
            for snapshot in snapshots
        ]

        total_mb = sum(all_sizes) if all_sizes else 0.0
        peak_mb = max(all_sizes) if all_sizes else 0.0

        return {
            "total_sessions": total_sessions,
            "total_snapshots": total_snapshots,
            "total_mb": total_mb,
            "peak_mb": peak_mb,
            "enabled": self.enabled,
            "started": self.started,
        }

    async def start_background_monitoring(self) -> None:
        """Start background task for automatic snapshots.

        Takes snapshots at regular intervals for all active sessions.

        Example:
            >>> await monitor.start_background_monitoring()
        """
        if not self.enabled:
            logger.info("Background monitoring disabled")
            return

        if self._snapshot_task is not None:
            logger.warning("Background monitoring already running")
            return

        async def snapshot_loop():
            """Background loop for taking snapshots."""
            while True:
                try:
                    await asyncio.sleep(self.snapshot_interval_seconds)

                    # Take snapshot for all active sessions
                    for session_id in list(self.snapshots.keys()):
                        self.take_snapshot(session_id)

                    logger.debug(
                        f"Background snapshot completed for {len(self.snapshots)} sessions"
                    )

                except asyncio.CancelledError:
                    logger.info("Background monitoring cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in background monitoring: {e}")

        self._snapshot_task = asyncio.create_task(snapshot_loop())
        logger.info("Started background memory monitoring")

    async def stop_background_monitoring(self) -> None:
        """Stop background monitoring task.

        Example:
            >>> await monitor.stop_background_monitoring()
        """
        if self._snapshot_task is not None:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
            self._snapshot_task = None
            logger.info("Stopped background memory monitoring")
