"""
Test Unit Executor - Tests for UnitExecutor service
Path: platform/src/L05_planning/tests/test_unit_executor.py
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from ..services.unit_executor import (
    UnitExecutor,
    ExecutionResult,
    ExecutionStatus,
    ExecutionType,
    CommandResult,
)
from ..agents.spec_decomposer import AtomicUnit, AcceptanceCriterion


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def executor(temp_dir):
    """Create a UnitExecutor instance for testing."""
    return UnitExecutor(
        working_dir=temp_dir,
        sandbox=True,
        dry_run=False,
        default_timeout=10,
    )


@pytest.fixture
def dry_run_executor(temp_dir):
    """Create a dry-run UnitExecutor instance for testing."""
    return UnitExecutor(
        working_dir=temp_dir,
        sandbox=True,
        dry_run=True,
        default_timeout=10,
    )


@pytest.fixture
def mock_unit():
    """Create a mock AtomicUnit for testing."""
    return AtomicUnit(
        id="unit-001",
        title="Create sample file",
        description="Create a new sample file in the project",
        files=["sample_file.py"],
        complexity=1,
        acceptance_criteria=[
            AcceptanceCriterion(
                id="ac-001",
                description="File exists",
                validation_command="test -f sample_file.py",
                timeout_seconds=5,
            ),
        ],
        dependencies=[],
    )


@pytest.fixture
def mock_test_unit():
    """Create a mock AtomicUnit for test execution."""
    return AtomicUnit(
        id="unit-002",
        title="Run tests",
        description="Run unit tests",
        files=["tests/test_example.py"],
        complexity=2,
        acceptance_criteria=[],
        dependencies=[],
    )


class TestUnitExecutorInit:
    """Tests for UnitExecutor initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        executor = UnitExecutor()
        assert executor.working_dir == Path.cwd()
        assert executor.sandbox is False
        assert executor.dry_run is False
        assert executor.default_timeout == 300

    def test_init_with_custom_params(self, temp_dir):
        """Test initialization with custom parameters."""
        executor = UnitExecutor(
            working_dir=temp_dir,
            sandbox=True,
            dry_run=True,
            default_timeout=60,
        )
        assert executor.working_dir == temp_dir
        assert executor.sandbox is True
        assert executor.dry_run is True
        assert executor.default_timeout == 60


class TestExecutionTypeDetection:
    """Tests for execution type detection."""

    def test_detect_file_create(self, executor):
        """Test detection of file create operation."""
        unit = AtomicUnit(
            id="u1",
            title="Create file",
            description="Create a new file",
            files=["new_file.py"],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )
        exec_type = executor._determine_execution_type(unit)
        assert exec_type == ExecutionType.FILE_CREATE

    def test_detect_test_execution(self, executor):
        """Test detection of test execution."""
        unit = AtomicUnit(
            id="u1",
            title="Run tests",
            description="Run unit tests",
            files=["test_something.py"],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )
        exec_type = executor._determine_execution_type(unit)
        assert exec_type == ExecutionType.TEST

    def test_detect_file_modify(self, executor):
        """Test detection of file modify operation."""
        unit = AtomicUnit(
            id="u1",
            title="Modify config",
            description="Modify the configuration file",
            files=[],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )
        exec_type = executor._determine_execution_type(unit)
        assert exec_type == ExecutionType.FILE_MODIFY

    def test_detect_command(self, executor):
        """Test detection of command execution."""
        unit = AtomicUnit(
            id="u1",
            title="Execute script",
            description="Run the deployment script",
            files=[],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )
        exec_type = executor._determine_execution_type(unit)
        assert exec_type == ExecutionType.COMMAND


class TestDryRunExecution:
    """Tests for dry-run execution mode."""

    @pytest.mark.asyncio
    async def test_dry_run_file_create(self, dry_run_executor, mock_unit):
        """Test dry-run of file creation."""
        result = await dry_run_executor.execute(mock_unit)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.execution_type == ExecutionType.FILE_CREATE
        assert "DRY RUN" in result.output
        assert result.metadata.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_no_files_created(self, dry_run_executor, mock_unit, temp_dir):
        """Test that dry-run doesn't create actual files."""
        await dry_run_executor.execute(mock_unit)

        # File should not exist
        file_path = temp_dir / "sample_file.py"
        assert not file_path.exists()


class TestRealExecution:
    """Tests for real execution mode."""

    @pytest.mark.asyncio
    async def test_create_file(self, executor, temp_dir):
        """Test actual file creation."""
        unit = AtomicUnit(
            id="u1",
            title="Create file",
            description="Create a new Python file",
            files=["new_file.py"],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )

        result = await executor.execute(unit, {"content": "# Test file\n"})

        assert result.status == ExecutionStatus.SUCCESS
        assert (temp_dir / "new_file.py").exists()
        # files_created contains full paths
        assert any("new_file.py" in path for path in result.files_created)

    @pytest.mark.asyncio
    async def test_skip_existing_file(self, executor, temp_dir):
        """Test that existing files are not overwritten."""
        # Create the file first
        existing_file = temp_dir / "existing.py"
        existing_file.write_text("# Existing content")

        unit = AtomicUnit(
            id="u1",
            title="Create file",
            description="Create a file",
            files=["existing.py"],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )

        result = await executor.execute(unit)

        assert result.status == ExecutionStatus.SUCCESS
        assert "existing.py" not in result.files_created
        assert existing_file.read_text() == "# Existing content"


class TestSandboxMode:
    """Tests for sandbox mode."""

    @pytest.mark.asyncio
    async def test_sandbox_blocks_outside_paths(self, temp_dir):
        """Test that sandbox blocks paths outside working directory."""
        executor = UnitExecutor(
            working_dir=temp_dir,
            sandbox=True,
        )

        unit = AtomicUnit(
            id="u1",
            title="Create file outside sandbox",
            description="Create a file",
            files=["/etc/passwd"],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )

        result = await executor.execute(unit)

        assert result.status == ExecutionStatus.FAILED
        assert "outside sandbox" in result.error.lower()

    def test_is_safe_path(self, executor, temp_dir):
        """Test safe path detection."""
        assert executor._is_safe_path(temp_dir / "some_file.py") is True
        assert executor._is_safe_path(Path("/etc/passwd")) is False
        assert executor._is_safe_path(temp_dir / ".." / "outside.py") is False


class TestCommandExecution:
    """Tests for command execution."""

    @pytest.mark.asyncio
    async def test_run_simple_command(self, executor):
        """Test running a simple command."""
        result = await executor._run_command("echo 'hello'")

        assert result.return_code == 0
        assert "hello" in result.stdout
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_command_timeout(self, executor):
        """Test command timeout handling."""
        result = await executor._run_command("sleep 10", timeout=1)

        assert result.return_code == -1
        assert result.timed_out is True
        assert "timed out" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_command_failure(self, executor):
        """Test handling of failed commands."""
        result = await executor._run_command("exit 1")

        assert result.return_code == 1
        assert result.timed_out is False


class TestFileBackup:
    """Tests for file backup functionality."""

    @pytest.mark.asyncio
    async def test_backup_before_modify(self, executor, temp_dir):
        """Test that files are backed up before modification."""
        # Create original file
        original_file = temp_dir / "original.txt"
        original_file.write_text("original content")

        await executor._backup_file(original_file)

        # Check backup was created
        backups = list(executor.backup_dir.glob("original.txt.*.bak"))
        assert len(backups) == 1
        assert backups[0].read_text() == "original content"

    def test_restore_from_backup(self, executor, temp_dir):
        """Test restoring a file from backup."""
        # Create and backup file
        original_file = temp_dir / "file.txt"
        original_file.write_text("original")

        # Simulate backup
        executor.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = executor.backup_dir / "file.txt.20240101-120000.bak"
        backup_path.write_text("original")

        executor._file_operations.append(Mock(
            path=str(original_file),
            backup_path=str(backup_path),
        ))

        # Modify file
        original_file.write_text("modified")

        # Restore
        result = executor.restore_from_backup(str(original_file))

        assert result is True
        assert original_file.read_text() == "original"


class TestBatchExecution:
    """Tests for batch execution."""

    @pytest.mark.asyncio
    async def test_sequential_execution(self, dry_run_executor):
        """Test sequential batch execution."""
        units = [
            AtomicUnit(
                id=f"u{i}",
                title=f"Unit {i}",
                description=f"Test unit {i}",
                files=[],
                complexity=1,
                acceptance_criteria=[],
                dependencies=[],
            )
            for i in range(3)
        ]

        results = await dry_run_executor.execute_batch(units, parallel=False)

        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)

    @pytest.mark.asyncio
    async def test_parallel_execution(self, dry_run_executor):
        """Test parallel batch execution."""
        units = [
            AtomicUnit(
                id=f"u{i}",
                title=f"Unit {i}",
                description=f"Test unit {i}",
                files=[],
                complexity=1,
                acceptance_criteria=[],
                dependencies=[],
            )
            for i in range(3)
        ]

        results = await dry_run_executor.execute_batch(units, parallel=True)

        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)


class TestStatistics:
    """Tests for executor statistics."""

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, dry_run_executor, mock_unit):
        """Test that statistics are tracked correctly."""
        await dry_run_executor.execute(mock_unit)
        await dry_run_executor.execute(mock_unit)

        stats = dry_run_executor.get_statistics()

        assert stats["execution_count"] == 2
        assert stats["success_count"] == 2
        assert stats["success_rate"] == 1.0
        assert stats["dry_run"] is True


class TestCleanup:
    """Tests for cleanup functionality."""

    def test_clear_backups(self, executor, temp_dir):
        """Test clearing backup files."""
        # Create some backups
        executor.backup_dir.mkdir(parents=True, exist_ok=True)
        (executor.backup_dir / "test.bak").write_text("backup")

        executor.clear_backups()

        assert executor.backup_dir.exists()
        assert len(list(executor.backup_dir.glob("*"))) == 0
        assert len(executor._file_operations) == 0
