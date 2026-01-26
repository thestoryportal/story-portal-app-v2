"""
Checkpoint Manager - Creates and manages execution checkpoints
Path: platform/src/L05_planning/checkpoints/checkpoint_manager.py
"""

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionCheckpoint:
    """Represents an execution checkpoint."""
    hash: str
    name: str
    git_commit: str
    git_branch: str
    timestamp: datetime
    unit_id: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    files_snapshot: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts checkpoint to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionCheckpoint':
        """Creates checkpoint from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class CheckpointManager:
    """
    Manages execution checkpoints for the planning pipeline.

    Features:
    - Creates git-based checkpoints
    - Stores execution state snapshots
    - Supports checkpoint persistence
    - Provides checkpoint comparison
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        storage_path: Optional[str] = None,
    ):
        """
        Initialize checkpoint manager.

        Args:
            repo_path: Path to git repository (defaults to cwd)
            storage_path: Path to store checkpoint data (optional)
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.storage_path = Path(storage_path) if storage_path else None
        self._checkpoints: Dict[str, ExecutionCheckpoint] = {}
        self._checkpoint_order: List[str] = []  # Maintains creation order

    def create_checkpoint(
        self,
        name: str,
        unit_id: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionCheckpoint:
        """
        Creates a new execution checkpoint.

        Args:
            name: Checkpoint name/identifier
            unit_id: Optional associated unit ID
            state: Optional execution state to snapshot
            metadata: Optional metadata

        Returns:
            ExecutionCheckpoint with hash and git info
        """
        git_commit = self._get_current_commit()
        git_branch = self._get_current_branch()
        timestamp = datetime.now()

        # Generate unique hash
        hash_input = f"{name}:{git_commit}:{timestamp.isoformat()}"
        checkpoint_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

        # Get file snapshot if git is available
        files_snapshot = self._get_modified_files()

        checkpoint = ExecutionCheckpoint(
            hash=checkpoint_hash,
            name=name,
            git_commit=git_commit,
            git_branch=git_branch,
            timestamp=timestamp,
            unit_id=unit_id,
            state=state or {},
            files_snapshot=files_snapshot,
            metadata=metadata or {},
        )

        # Store checkpoint
        self._checkpoints[checkpoint_hash] = checkpoint
        self._checkpoint_order.append(checkpoint_hash)

        # Persist if storage path configured
        if self.storage_path:
            self._persist_checkpoint(checkpoint)

        logger.info(f"Created checkpoint '{name}' with hash {checkpoint_hash}")
        return checkpoint

    def get_checkpoint(self, hash_or_name: str) -> Optional[ExecutionCheckpoint]:
        """
        Gets a checkpoint by hash or name.

        Args:
            hash_or_name: Checkpoint hash or name

        Returns:
            ExecutionCheckpoint if found, None otherwise
        """
        # Try by hash first
        if hash_or_name in self._checkpoints:
            return self._checkpoints[hash_or_name]

        # Try by name
        for cp in self._checkpoints.values():
            if cp.name == hash_or_name:
                return cp

        return None

    def get_latest_checkpoint(self) -> Optional[ExecutionCheckpoint]:
        """Gets the most recent checkpoint."""
        if not self._checkpoint_order:
            return None
        return self._checkpoints.get(self._checkpoint_order[-1])

    def get_checkpoint_by_unit(self, unit_id: str) -> Optional[ExecutionCheckpoint]:
        """Gets the most recent checkpoint for a unit."""
        for cp_hash in reversed(self._checkpoint_order):
            cp = self._checkpoints.get(cp_hash)
            if cp and cp.unit_id == unit_id:
                return cp
        return None

    def list_checkpoints(
        self,
        unit_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ExecutionCheckpoint]:
        """
        Lists checkpoints, optionally filtered.

        Args:
            unit_id: Filter by unit ID
            limit: Maximum number to return

        Returns:
            List of checkpoints in creation order (newest first)
        """
        checkpoints = []

        for cp_hash in reversed(self._checkpoint_order):
            cp = self._checkpoints.get(cp_hash)
            if cp is None:
                continue

            if unit_id and cp.unit_id != unit_id:
                continue

            checkpoints.append(cp)

            if limit and len(checkpoints) >= limit:
                break

        return checkpoints

    def delete_checkpoint(self, hash: str) -> bool:
        """
        Deletes a checkpoint.

        Args:
            hash: Checkpoint hash

        Returns:
            True if deleted, False if not found
        """
        if hash not in self._checkpoints:
            return False

        del self._checkpoints[hash]
        self._checkpoint_order.remove(hash)

        # Remove persisted file if exists
        if self.storage_path:
            checkpoint_file = self.storage_path / f"{hash}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()

        logger.info(f"Deleted checkpoint {hash}")
        return True

    def compare_checkpoints(
        self,
        hash1: str,
        hash2: str,
    ) -> Dict[str, Any]:
        """
        Compares two checkpoints.

        Args:
            hash1: First checkpoint hash
            hash2: Second checkpoint hash

        Returns:
            Comparison dictionary with differences
        """
        cp1 = self.get_checkpoint(hash1)
        cp2 = self.get_checkpoint(hash2)

        if not cp1 or not cp2:
            raise ValueError("One or both checkpoints not found")

        # Compare files
        files1 = set(cp1.files_snapshot)
        files2 = set(cp2.files_snapshot)

        return {
            "checkpoint1": hash1,
            "checkpoint2": hash2,
            "time_diff_seconds": (cp2.timestamp - cp1.timestamp).total_seconds(),
            "git_commits_differ": cp1.git_commit != cp2.git_commit,
            "files_added": list(files2 - files1),
            "files_removed": list(files1 - files2),
            "state_keys_added": list(set(cp2.state.keys()) - set(cp1.state.keys())),
            "state_keys_removed": list(set(cp1.state.keys()) - set(cp2.state.keys())),
        }

    def _get_current_commit(self) -> str:
        """Gets current HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _get_current_branch(self) -> str:
        """Gets current branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _get_modified_files(self) -> List[str]:
        """Gets list of modified files in git."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path),
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\n') if f]
            return []
        except Exception:
            return []

    def _persist_checkpoint(self, checkpoint: ExecutionCheckpoint):
        """Persists checkpoint to storage."""
        if not self.storage_path:
            return

        self.storage_path.mkdir(parents=True, exist_ok=True)
        checkpoint_file = self.storage_path / f"{checkpoint.hash}.json"

        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    def load_checkpoints(self):
        """Loads checkpoints from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return

        for checkpoint_file in self.storage_path.glob("*.json"):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)
                cp = ExecutionCheckpoint.from_dict(data)
                self._checkpoints[cp.hash] = cp
                if cp.hash not in self._checkpoint_order:
                    self._checkpoint_order.append(cp.hash)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")

        # Sort by timestamp
        self._checkpoint_order.sort(
            key=lambda h: self._checkpoints[h].timestamp
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Returns checkpoint statistics."""
        if not self._checkpoints:
            return {
                "total_checkpoints": 0,
                "units_with_checkpoints": 0,
            }

        units = set(cp.unit_id for cp in self._checkpoints.values() if cp.unit_id)

        return {
            "total_checkpoints": len(self._checkpoints),
            "units_with_checkpoints": len(units),
            "oldest_checkpoint": self._checkpoints[self._checkpoint_order[0]].timestamp.isoformat()
                if self._checkpoint_order else None,
            "newest_checkpoint": self._checkpoints[self._checkpoint_order[-1]].timestamp.isoformat()
                if self._checkpoint_order else None,
        }

    def clear(self):
        """Clears all checkpoints."""
        self._checkpoints = {}
        self._checkpoint_order = []
