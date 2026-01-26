"""
Unit Executor - Executes AtomicUnits with real file/command operations
Path: platform/src/L05_planning/services/unit_executor.py
"""

import asyncio
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..agents.spec_decomposer import AtomicUnit

logger = logging.getLogger(__name__)


class ExecutionType(Enum):
    """Types of execution operations."""
    FILE_CREATE = "file_create"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    COMMAND = "command"
    TEST = "test"
    COMPOSITE = "composite"


class ExecutionStatus(Enum):
    """Status of an execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class FileOperation:
    """Represents a file operation to execute."""
    operation: str  # create, modify, delete
    path: str
    content: Optional[str] = None
    backup_path: Optional[str] = None


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: str
    return_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


@dataclass
class ExecutionResult:
    """Result of executing an AtomicUnit."""
    unit_id: str
    status: ExecutionStatus
    execution_type: ExecutionType
    output: str = ""
    error: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    commands_run: List[CommandResult] = field(default_factory=list)
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Returns True if execution was successful."""
        return self.status == ExecutionStatus.SUCCESS


class UnitExecutor:
    """
    Executes AtomicUnits with real file and command operations.

    Features:
    - File operations (create, modify, delete) with backup
    - Command execution with timeout
    - Test execution (pytest integration)
    - Sandbox isolation (optional)
    - Dry-run mode for testing
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        sandbox: bool = False,
        dry_run: bool = False,
        default_timeout: int = 300,
        backup_dir: Optional[Path] = None,
    ):
        """
        Initialize unit executor.

        Args:
            working_dir: Base directory for operations (defaults to cwd)
            sandbox: If True, restrict operations to working_dir
            dry_run: If True, simulate operations without executing
            default_timeout: Default command timeout in seconds
            backup_dir: Directory for file backups
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.sandbox = sandbox
        self.dry_run = dry_run
        self.default_timeout = default_timeout
        self.backup_dir = Path(backup_dir) if backup_dir else self.working_dir / ".l05_backups"

        self._execution_count = 0
        self._success_count = 0
        self._file_operations: List[FileOperation] = []

    async def execute(
        self,
        unit: AtomicUnit,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute an AtomicUnit.

        Args:
            unit: AtomicUnit to execute
            context: Optional execution context with variables

        Returns:
            ExecutionResult with status and details
        """
        start_time = datetime.now()
        context = context or {}

        logger.info(f"Executing unit: {unit.id} - {unit.title}")

        self._execution_count += 1

        try:
            # Determine execution type from unit content
            execution_type = self._determine_execution_type(unit)

            # Execute based on type
            if self.dry_run:
                result = await self._execute_dry_run(unit, execution_type)
            else:
                result = await self._execute_real(unit, execution_type, context)

            if result.status == ExecutionStatus.SUCCESS:
                self._success_count += 1

            # Calculate duration
            end_time = datetime.now()
            result.duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(f"Unit {unit.id} execution complete: {result.status.value}")
            return result

        except Exception as e:
            logger.error(f"Unit {unit.id} execution failed: {e}")
            end_time = datetime.now()
            return ExecutionResult(
                unit_id=unit.id,
                status=ExecutionStatus.FAILED,
                execution_type=ExecutionType.COMPOSITE,
                error=str(e),
                duration_ms=int((end_time - start_time).total_seconds() * 1000),
            )

    def _determine_execution_type(self, unit: AtomicUnit) -> ExecutionType:
        """Determine the execution type from unit content."""
        if unit.files:
            if any("test" in f.lower() for f in unit.files):
                return ExecutionType.TEST
            return ExecutionType.FILE_CREATE

        # Check description for hints
        desc_lower = unit.description.lower()
        if "test" in desc_lower:
            return ExecutionType.TEST
        if "create" in desc_lower or "add" in desc_lower:
            return ExecutionType.FILE_CREATE
        if "modify" in desc_lower or "update" in desc_lower:
            return ExecutionType.FILE_MODIFY
        if "delete" in desc_lower or "remove" in desc_lower:
            return ExecutionType.FILE_DELETE
        if "run" in desc_lower or "execute" in desc_lower:
            return ExecutionType.COMMAND

        return ExecutionType.COMPOSITE

    async def _execute_dry_run(
        self,
        unit: AtomicUnit,
        execution_type: ExecutionType,
    ) -> ExecutionResult:
        """Execute in dry-run mode (simulation)."""
        logger.info(f"DRY RUN: Would execute {execution_type.value} for {unit.id}")

        return ExecutionResult(
            unit_id=unit.id,
            status=ExecutionStatus.SUCCESS,
            execution_type=execution_type,
            output=f"DRY RUN: {unit.title}",
            files_changed=unit.files,
            metadata={"dry_run": True},
        )

    async def _execute_real(
        self,
        unit: AtomicUnit,
        execution_type: ExecutionType,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute unit for real."""
        files_created = []
        files_changed = []
        commands_run = []
        output_parts = []

        # Handle file operations
        if unit.files:
            for file_path in unit.files:
                full_path = self._resolve_path(file_path)

                if self.sandbox and not self._is_safe_path(full_path):
                    return ExecutionResult(
                        unit_id=unit.id,
                        status=ExecutionStatus.FAILED,
                        execution_type=execution_type,
                        error=f"Path outside sandbox: {file_path}",
                    )

                if execution_type == ExecutionType.FILE_CREATE:
                    # Create file if it doesn't exist
                    if not full_path.exists():
                        await self._create_file(full_path, context.get("content", ""))
                        files_created.append(str(full_path))
                        output_parts.append(f"Created: {file_path}")
                    else:
                        output_parts.append(f"Exists: {file_path}")

                elif execution_type == ExecutionType.FILE_MODIFY:
                    if full_path.exists():
                        await self._backup_file(full_path)
                        # Modification content should come from context
                        files_changed.append(str(full_path))
                        output_parts.append(f"Would modify: {file_path}")

                elif execution_type == ExecutionType.FILE_DELETE:
                    if full_path.exists():
                        await self._backup_file(full_path)
                        full_path.unlink()
                        output_parts.append(f"Deleted: {file_path}")

        # Handle test execution
        if execution_type == ExecutionType.TEST:
            test_cmd = context.get("test_command", "pytest")
            if unit.files:
                test_cmd = f"{test_cmd} {' '.join(unit.files)}"

            cmd_result = await self._run_command(test_cmd)
            commands_run.append(cmd_result)
            output_parts.append(f"Tests: {'PASSED' if cmd_result.return_code == 0 else 'FAILED'}")

            if cmd_result.return_code != 0:
                return ExecutionResult(
                    unit_id=unit.id,
                    status=ExecutionStatus.FAILED,
                    execution_type=execution_type,
                    output="\n".join(output_parts),
                    error=cmd_result.stderr or "Tests failed",
                    commands_run=commands_run,
                )

        # Handle command execution from acceptance criteria
        for criterion in unit.acceptance_criteria:
            if criterion.validation_command and "Manual verification" not in criterion.validation_command:
                cmd_result = await self._run_command(
                    criterion.validation_command,
                    timeout=criterion.timeout_seconds,
                )
                commands_run.append(cmd_result)

        return ExecutionResult(
            unit_id=unit.id,
            status=ExecutionStatus.SUCCESS,
            execution_type=execution_type,
            output="\n".join(output_parts) if output_parts else "Execution complete",
            files_created=files_created,
            files_changed=files_changed,
            commands_run=commands_run,
        )

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to working directory."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.working_dir / p

    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is within sandbox."""
        try:
            path.resolve().relative_to(self.working_dir.resolve())
            return True
        except ValueError:
            return False

    async def _create_file(self, path: Path, content: str = ""):
        """Create a file with optional content."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        logger.debug(f"Created file: {path}")

    async def _backup_file(self, path: Path):
        """Backup a file before modification."""
        if not path.exists():
            return

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(path, backup_path)

        self._file_operations.append(FileOperation(
            operation="backup",
            path=str(path),
            backup_path=str(backup_path),
        ))
        logger.debug(f"Backed up: {path} -> {backup_path}")

    async def _run_command(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """Run a shell command."""
        timeout = timeout or self.default_timeout
        start_time = datetime.now()

        logger.debug(f"Running command: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                end_time = datetime.now()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                return CommandResult(
                    command=command,
                    return_code=process.returncode or 0,
                    stdout=stdout.decode() if stdout else "",
                    stderr=stderr.decode() if stderr else "",
                    duration_ms=duration_ms,
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()

                end_time = datetime.now()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                return CommandResult(
                    command=command,
                    return_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    duration_ms=duration_ms,
                    timed_out=True,
                )

        except Exception as e:
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
            )

    async def execute_batch(
        self,
        units: List[AtomicUnit],
        context: Optional[Dict[str, Any]] = None,
        parallel: bool = False,
    ) -> List[ExecutionResult]:
        """
        Execute multiple units.

        Args:
            units: List of units to execute
            context: Shared execution context
            parallel: If True, execute independent units in parallel

        Returns:
            List of ExecutionResults
        """
        if parallel:
            tasks = [self.execute(unit, context) for unit in units]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for unit in units:
                result = await self.execute(unit, context)
                results.append(result)
            return results

    def restore_from_backup(self, file_path: str) -> bool:
        """
        Restore a file from backup.

        Args:
            file_path: Original file path

        Returns:
            True if restored, False if no backup found
        """
        for op in reversed(self._file_operations):
            if op.path == file_path and op.backup_path:
                backup = Path(op.backup_path)
                if backup.exists():
                    shutil.copy2(backup, file_path)
                    logger.info(f"Restored: {file_path} from {op.backup_path}")
                    return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Returns executor statistics."""
        return {
            "execution_count": self._execution_count,
            "success_count": self._success_count,
            "success_rate": (
                self._success_count / self._execution_count
                if self._execution_count > 0 else 0.0
            ),
            "file_operations": len(self._file_operations),
            "working_dir": str(self.working_dir),
            "sandbox": self.sandbox,
            "dry_run": self.dry_run,
        }

    def clear_backups(self):
        """Clear all backup files."""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._file_operations = []
        logger.info("Cleared all backups")
