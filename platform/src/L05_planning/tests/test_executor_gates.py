"""
L05 Planning Pipeline - UnitExecutor Gate Tests (Phase 2).

These tests MUST pass before proceeding to Phase 3.
Gate 2 validates:
1. FILE_CREATE tasks actually create files on disk
2. FILE_MODIFY tasks actually write content to files
3. No mock strings appear in execution outputs

Run: pytest test_executor_gates.py -v
Expected: 3/3 pass
"""

import os
import pytest
import asyncio
from pathlib import Path
from uuid import uuid4

from ..agents.spec_decomposer import AtomicUnit
from ..services.unit_executor import UnitExecutor, ExecutionType


class TestExecutorGates:
    """
    Gate 2: UnitExecutor Tests

    These tests verify that file operations actually happen
    on disk, not just return mock strings.
    """

    @pytest.fixture
    def executor(self, tmp_path) -> UnitExecutor:
        """Create a UnitExecutor for testing with real file operations."""
        return UnitExecutor(
            working_dir=tmp_path,
            sandbox=True,  # Sandbox to tmp_path
            dry_run=False,  # CRITICAL: Must be False for real operations
            default_timeout=30,
        )

    @pytest.fixture
    def file_create_unit(self, tmp_path) -> AtomicUnit:
        """Create a FILE_CREATE AtomicUnit."""
        return AtomicUnit(
            id=str(uuid4()),
            title="Create sample file",
            description="Create a new sample file",  # "create" triggers FILE_CREATE
            files=["gate2_sample.txt"],
        )

    @pytest.fixture
    def file_modify_unit(self, tmp_path) -> AtomicUnit:
        """Create a FILE_MODIFY AtomicUnit that modifies an existing file."""
        # First create the file to modify
        sample_file = tmp_path / "gate2_sample_modify.txt"
        sample_file.write_text("Original content before modification")

        return AtomicUnit(
            id=str(uuid4()),
            title="Modify sample file",
            description="Update the existing sample file",  # "modify/update" triggers FILE_MODIFY
            files=["gate2_sample_modify.txt"],
        )

    @pytest.mark.asyncio
    async def test_file_create_actually_creates(
        self, executor: UnitExecutor, file_create_unit: AtomicUnit, tmp_path
    ):
        """
        GATE 2.1: FILE_CREATE actually creates files on disk.

        Verifies that:
        1. Executing a FILE_CREATE unit creates a real file
        2. The file exists on disk after execution
        3. The file contains the specified content
        """
        target_path = tmp_path / file_create_unit.files[0]
        expected_content = "Gate 2 test content - this should be on disk"

        # Ensure file doesn't exist before
        assert not target_path.exists(), "File should not exist before creation"

        # Execute the unit with content in context
        result = await executor.execute(
            file_create_unit,
            context={"content": expected_content}
        )

        # Verify unit completed
        assert result is not None, "Execute returned None"
        assert result.error is None, f"Unit failed: {result.error}"

        # CRITICAL: Verify file actually exists on disk
        assert target_path.exists(), (
            f"GATE 2.1 FAILED: File was not created on disk.\n"
            f"Path: {target_path}\n"
            f"This indicates FILE_CREATE is returning mock results."
        )

        # Verify content is correct
        actual_content = target_path.read_text()
        assert actual_content == expected_content, (
            f"GATE 2.1 FAILED: File content doesn't match.\n"
            f"Expected: {expected_content}\n"
            f"Actual: {actual_content}"
        )

    @pytest.mark.asyncio
    async def test_file_modify_actually_writes(
        self, executor: UnitExecutor, file_modify_unit: AtomicUnit, tmp_path
    ):
        """
        GATE 2.2: FILE_MODIFY actually writes content to files.

        Verifies that:
        1. Executing a FILE_MODIFY unit modifies an existing file
        2. The new content is written to disk
        3. The original content is replaced
        """
        target_path = tmp_path / "gate2_sample_modify.txt"
        expected_content = "Modified content after Gate 2 verification"
        original_content = "Original content before modification"

        # Verify file exists with original content before
        assert target_path.exists(), "Test file should exist before modification"
        assert target_path.read_text() == original_content, "Original content should be set"

        # Execute the unit with content in context
        result = await executor.execute(
            file_modify_unit,
            context={"content": expected_content}
        )

        # Verify unit completed
        assert result is not None, "Execute returned None"
        assert result.error is None, f"Unit failed: {result.error}"

        # CRITICAL: Verify file content actually changed on disk
        actual_content = target_path.read_text()
        assert actual_content != original_content, (
            f"GATE 2.2 FAILED: File content was not modified.\n"
            f"Content is still: {actual_content}\n"
            f"This indicates FILE_MODIFY is returning mock results.\n"
            f"Result output: {result.output}"
        )

        assert actual_content == expected_content, (
            f"GATE 2.2 FAILED: File content doesn't match expected.\n"
            f"Expected: {expected_content}\n"
            f"Actual: {actual_content}"
        )

    @pytest.mark.asyncio
    async def test_no_mock_strings_in_output(
        self, executor: UnitExecutor, file_create_unit: AtomicUnit, tmp_path
    ):
        """
        GATE 2.3: No mock strings appear in execution outputs.

        Verifies that:
        1. Result doesn't contain "(mock)"
        2. Result doesn't contain "Would modify"
        3. Result doesn't contain "Would create"
        4. Result doesn't contain "dry_run"
        """
        # Execute the unit
        result = await executor.execute(
            file_create_unit,
            context={"content": "Test content"}
        )

        assert result is not None, "Execute returned None"

        # Convert result to string for searching
        result_str = str(result).lower()

        # List of forbidden mock indicators
        mock_indicators = [
            "(mock)",
            "would modify",
            "would create",
            "would delete",
            "dry_run",
            "dry run",
            "simulated",
            "skipped",
        ]

        for indicator in mock_indicators:
            assert indicator not in result_str, (
                f"GATE 2.3 FAILED: Mock indicator '{indicator}' found in result.\n"
                f"Result: {result}\n"
                f"This indicates executor is in mock/dry-run mode."
            )


class TestUnitExecutorConfiguration:
    """
    Additional tests for UnitExecutor configuration.
    These help diagnose issues but are not blocking gates.
    """

    def test_dry_run_false_by_default_for_execution(self, tmp_path):
        """Test that dry_run can be disabled for real execution."""
        executor = UnitExecutor(
            working_dir=tmp_path,
            sandbox=True,
            dry_run=False,
        )
        assert executor.dry_run == False, "dry_run should be False when explicitly set"

    def test_sandbox_restricts_to_working_dir(self, tmp_path):
        """Test that sandbox mode restricts operations to working_dir."""
        executor = UnitExecutor(
            working_dir=tmp_path,
            sandbox=True,
            dry_run=False,
        )
        assert executor.sandbox == True, "sandbox should be True"
        assert executor.working_dir == tmp_path, "working_dir should be set"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
