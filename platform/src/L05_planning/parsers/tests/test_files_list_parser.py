"""
Tests for FilesListParser
Path: platform/src/L05_planning/parsers/tests/test_files_list_parser.py
"""
import pytest
from ..files_list_parser import FilesListParser
from ..format_detector import FormatDetector, FormatType
from ..multi_format_parser import MultiFormatParser


class TestFormatDetection:
    """Test format detection for files_list format."""

    def test_detects_files_list_format(self):
        """Test that format detector identifies files_list format."""
        plan = """# Test Plan

## Files to Create

### 1. `path/to/file.py`
Description here.

### 2. `path/to/another.py`
More description.
"""
        detector = FormatDetector()
        result = detector.detect(plan)

        assert result.format_type == FormatType.FILES_LIST
        assert result.confidence >= 0.5

    def test_detects_without_backticks(self):
        """Test detection works without backticks around paths."""
        plan = """# Test Plan

## Files to Create

### 1. src/module.py
Description.

### 2. src/other.py
Other description.
"""
        detector = FormatDetector()
        result = detector.detect(plan)

        assert result.format_type == FormatType.FILES_LIST


class TestFilesListParser:
    """Test FilesListParser functionality."""

    def test_parses_basic_files_list(self):
        """Test basic parsing of files list format."""
        plan = """# My Feature Plan

## Overview
This is the overview.

## Files to Create

### 1. `src/module/__init__.py`
Package init file.

### 2. `src/module/main.py`
Main module implementation.

### 3. `src/module/tests/test_main.py`
Test file.
"""
        parser = FilesListParser()
        result = parser.parse(plan)

        assert result.title == "My Feature Plan"
        assert len(result.steps) == 3
        assert result.overview == "This is the overview."

    def test_extracts_file_paths(self):
        """Test that file paths are extracted correctly."""
        plan = """# Plan

### 1. `../platform/src/L05_planning/v2/__init__.py`
Init file.

### 2. `../platform/src/L05_planning/v2/status.py`
Status module.
"""
        parser = FilesListParser()
        result = parser.parse(plan)

        assert result.steps[0].files == ["../platform/src/L05_planning/v2/__init__.py"]
        assert result.steps[1].files == ["../platform/src/L05_planning/v2/status.py"]

    def test_generates_meaningful_titles(self):
        """Test that titles are generated from file paths."""
        plan = """# Plan

### 1. `src/v2/__init__.py`
Init.

### 2. `src/v2/status.py`
Status.

### 3. `src/v2/tests/test_status.py`
Test.
"""
        parser = FilesListParser()
        result = parser.parse(plan)

        assert "v2 package" in result.steps[0].title.lower()
        assert "status" in result.steps[1].title.lower()
        assert "test" in result.steps[2].title.lower()

    def test_generates_acceptance_criteria(self):
        """Test that acceptance criteria are generated."""
        plan = """# Plan

### 1. `src/module.py`
Create the module.
"""
        parser = FilesListParser()
        result = parser.parse(plan)

        assert len(result.steps[0].acceptance_criteria) > 0
        assert any("exists" in c.lower() for c in result.steps[0].acceptance_criteria)


class TestMultiFormatParserIntegration:
    """Test MultiFormatParser routes to FilesListParser correctly."""

    def test_routes_to_files_list_parser(self):
        """Test that MultiFormatParser routes files_list format correctly."""
        plan = """# Feature Implementation

## Files to Create

### 1. `src/feature/__init__.py`
Package init.

### 2. `src/feature/core.py`
Core implementation.

### 3. `src/feature/tests/test_core.py`
Test file.

## Verification
Run the tests.
"""
        parser = MultiFormatParser()
        result = parser.parse(plan)

        assert result.format_type == FormatType.FILES_LIST
        assert len(result.steps) == 3
        assert result.title == "Feature Implementation"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_single_step(self):
        """Test parsing a plan with single step."""
        plan = """# Quick Fix

### 1. `src/fix.py`
Fix the bug.
"""
        parser = FilesListParser()
        result = parser.parse(plan)

        assert len(result.steps) == 1

    def test_handles_code_blocks_in_content(self):
        """Test that code blocks don't confuse the parser."""
        plan = """# Plan

### 1. `src/module.py`
Create module with:
```python
def hello():
    pass
```
"""
        parser = FilesListParser()
        result = parser.parse(plan)

        assert len(result.steps) == 1
        # Code block should not be in description
        assert "```" not in result.steps[0].description
