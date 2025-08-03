"""Test configuration and shared fixtures."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.core.entities.activity import Activity
from src.infrastructure.storage.encrypted_json_storage import EncryptedJsonStorage


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def storage(temp_dir):
    """Create a temporary storage instance."""
    storage_path = os.path.join(temp_dir, "test.db")
    return EncryptedJsonStorage(storage_path)


@pytest.fixture
def sample_activity():
    """Create a sample activity for testing."""
    return Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/to/test",
        start_time=datetime.now()
    )