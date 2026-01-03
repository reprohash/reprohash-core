#!/usr/bin/env python3
"""
Test configuration and fixtures.
"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def tmp_workspace():
    """Temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(tmp_workspace):
    """Single test file."""
    file = tmp_workspace / "test.txt"
    file.write_text("hello world")
    return file


@pytest.fixture
def sample_files(tmp_workspace):
    """Multiple test files."""
    (tmp_workspace / "data").mkdir()
    (tmp_workspace / "data" / "file1.txt").write_text("content1")
    (tmp_workspace / "data" / "file2.txt").write_text("content2")
    (tmp_workspace / "data" / "file3.txt").write_text("content3")
    return tmp_workspace / "data"
