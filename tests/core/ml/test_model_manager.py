"""Tests for the ModelManager."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from src.core.entities.activity import Activity
from src.core.ml.model_manager import ModelManager


@pytest.fixture
def sample_activities():
    """Create sample activities for testing."""
    now = datetime.now()
    activities = []

    # Create activities with a pattern (alternating between two apps)
    for i in range(10):
        activity = Activity(
            app_name=f"app_{i % 2}",  # Alternates between app_0 and app_1
            window_title=f"window_{i}",
            process_id=i,
            executable_path=f"/path/to/app_{i % 2}",
            start_time=now + timedelta(minutes=i * 5),
        )
        activity.active_time = float(60)  # 1 minute active
        activity.idle_time = float(30)  # 30 seconds idle
        activity.end_time = activity.start_time + timedelta(
            seconds=activity.active_time + activity.idle_time
        )
        activities.append(activity)

    return activities


@pytest.fixture
def model_manager():
    """Create a temporary model manager."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield ModelManager(tmpdirname)


def test_model_manager_initialization(model_manager):
    """Test model manager initialization."""
    assert model_manager.current_model is None
    assert model_manager.model_metadata == {}
    assert model_manager.models_dir.exists()


def test_model_training(model_manager, sample_activities):
    """Test model training process."""
    metrics = model_manager.train_model(sample_activities)

    assert isinstance(metrics, dict)
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert all(0 <= v <= 1 for v in metrics.values())

    # Verify model was saved
    assert model_manager.current_model is not None
    assert isinstance(model_manager.current_model, RandomForestClassifier)
    assert model_manager.model_metadata != {}


def test_model_prediction(model_manager, sample_activities):
    """Test model prediction."""
    # Train model first
    model_manager.train_model(sample_activities)

    # Test prediction with recent activities
    prediction = model_manager.predict_next_activity(sample_activities[-3:])
    assert prediction in ["app_0", "app_1"]


def test_model_persistence(sample_activities):
    """Test model saving and loading."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Train and save model
        manager1 = ModelManager(tmpdirname)
        metrics1 = manager1.train_model(sample_activities)
        model1 = manager1.current_model

        # Create new manager and load model
        manager2 = ModelManager(tmpdirname)
        prediction1 = manager1.predict_next_activity(sample_activities[-3:])
        prediction2 = manager2.predict_next_activity(sample_activities[-3:])

        # Predictions should be the same
        assert prediction1 == prediction2


def test_model_evaluation(model_manager, sample_activities):
    """Test model evaluation metrics."""
    metrics = model_manager.train_model(sample_activities)

    assert metrics["accuracy"] > 0
    assert metrics["precision"] > 0
    assert metrics["recall"] > 0
    assert metrics["f1_score"] > 0


def test_empty_activities_handling(model_manager):
    """Test handling of empty activity list."""
    with pytest.raises(ValueError):
        model_manager.train_model([])


def test_model_info(model_manager, sample_activities):
    """Test getting model information."""
    # No model initially
    assert model_manager.get_model_info() == {}

    # Train model
    model_manager.train_model(sample_activities)
    info = model_manager.get_model_info()

    assert "trained_at" in info
    assert "n_samples" in info
    assert "feature_names" in info
    assert "metrics" in info
    assert "parameters" in info


def test_prediction_without_model(model_manager, sample_activities):
    """Test prediction behavior when no model exists."""
    prediction = model_manager.predict_next_activity(sample_activities)
    assert prediction is None


def test_model_metadata_format(model_manager, sample_activities):
    """Test the format of saved model metadata."""
    model_manager.train_model(sample_activities)

    # Find the metadata file
    meta_files = list(model_manager.models_dir.glob("metadata_*.json"))
    assert len(meta_files) == 1

    # Check metadata content
    with open(meta_files[0]) as f:
        metadata = json.load(f)

    assert isinstance(metadata["trained_at"], str)
    assert isinstance(metadata["n_samples"], int)
    assert isinstance(metadata["feature_names"], list)
    assert isinstance(metadata["metrics"], dict)
    assert isinstance(metadata["parameters"], dict)
