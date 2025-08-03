"""Tests for the prediction service."""

import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

import pytest

from src.core.entities.activity import Activity
from src.core.services.prediction_service import PredictionService


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    mock = MagicMock()
    # Configure mock to handle iteration and boolean checks
    mock.get_by_timerange.return_value = []
    return mock


@pytest.fixture
def mock_learner():
    """Create mock learner."""
    return MagicMock()


@pytest.fixture
def mock_categorizer():
    """Create mock categorizer."""
    return MagicMock()


@pytest.fixture
def prediction_service(mock_repository, mock_learner, mock_categorizer):
    """Create prediction service for testing."""
    return PredictionService(
        repository=mock_repository,
        learner=mock_learner,
        categorizer=mock_categorizer,
        prediction_window=timedelta(hours=1),
        load_initial_data=False  # Don't load data during initialization
    )


@pytest.fixture
def sample_activities():
    """Create sample activities."""
    current_time = datetime.now()
    return [
        Activity(
            app_name="code.exe",
            window_title=f"Working on project {i}",
            process_id=i,
            executable_path="/path/to/test",
            start_time=current_time - timedelta(minutes=30),
            active_time=240.0,
            idle_time=60.0
        )
        for i in range(10)
    ]


def test_initialization_with_data_loading(
    mock_repository,
    mock_learner,
    mock_categorizer,
    sample_activities
):
    """Test service initialization with data loading."""
    mock_repository.get_by_timerange.return_value = sample_activities

    service = PredictionService(
        repository=mock_repository,
        learner=mock_learner,
        categorizer=mock_categorizer,
        load_initial_data=True
    )

    assert mock_repository.get_by_timerange.call_count == 1
    assert len(mock_repository.get_by_timerange.call_args_list) == 1


def test_load_initial_data(prediction_service, mock_repository, sample_activities):
    """Test loading initial data."""
    mock_repository.get_by_timerange.return_value = sample_activities
    mock_repository.get_by_timerange.reset_mock()  # Reset any previous calls

    prediction_service._load_initial_data()

    assert mock_repository.get_by_timerange.call_count == 1
    assert len(mock_repository.get_by_timerange.call_args_list) == 1


def test_get_prediction_data(prediction_service, mock_repository, sample_activities):
    """Test getting prediction data."""
    mock_repository.get_by_timerange.return_value = sample_activities[-5:]
    mock_repository.get_by_timerange.reset_mock()  # Reset any previous calls

    activities = prediction_service._get_prediction_data()

    assert activities == sample_activities[-5:]
    assert mock_repository.get_by_timerange.call_count == 1
    assert len(mock_repository.get_by_timerange.call_args_list) == 1


def test_predict_next_activity(
    prediction_service,
    mock_repository,
    mock_learner,
    sample_activities
):
    """Test activity prediction."""
    mock_repository.get_by_timerange.return_value = sample_activities
    mock_learner.predict_next.return_value = "test_app"
    mock_repository.get_by_timerange.reset_mock()  # Reset any previous calls

    # Test with provided activities
    result = prediction_service.predict_next_activity(sample_activities)
    assert result == "test_app"
    assert mock_repository.get_by_timerange.call_count == 0

    # Test without provided activities
    result = prediction_service.predict_next_activity()
    assert result == "test_app"
    assert mock_repository.get_by_timerange.call_count == 1


def test_predict_next_activity_insufficient_data(
    prediction_service,
    mock_repository,
    mock_learner
):
    """Test prediction with insufficient data."""
    mock_repository.get_by_timerange.return_value = []
    mock_learner.predict_next.return_value = None

    result = prediction_service.predict_next_activity()

    assert result is None


def test_predict_next_activity_error(
    prediction_service,
    mock_repository,
    mock_learner,
    sample_activities
):
    """Test prediction error handling."""
    mock_repository.get_by_timerange.return_value = sample_activities
    mock_learner.predict_next.side_effect = Exception("Test error")

    result = prediction_service.predict_next_activity()

    assert result is None


def test_get_activity_insights_custom_window(
    prediction_service,
    mock_repository,
    mock_categorizer,
    mock_learner,
    sample_activities
):
    """Test getting insights with custom time window."""
    mock_repository.get_by_timerange.return_value = sample_activities
    mock_categorizer.get_activity_insights.return_value = {
        'overall_productivity': 0.8,
        'time_productivity': {
            'morning': 0.9,
            'afternoon': 0.7,
            'evening': 0.6,
            'night': 0.5
        }
    }
    mock_learner.predict_next.return_value = 'code.exe'
    mock_repository.get_by_timerange.reset_mock()  # Reset any previous calls

    insights = prediction_service.get_activity_insights(
        time_window=timedelta(days=1)
    )

    assert insights['productivity']['overall'] == 0.8
    assert insights['productivity']['by_time']['morning'] == 0.9
    assert insights['predicted_next'] == 'code.exe'
    assert mock_repository.get_by_timerange.call_count == 1
    assert len(mock_repository.get_by_timerange.call_args_list) == 1


def test_get_activity_insights_no_data(
    prediction_service,
    mock_repository,
    mock_categorizer,
    mock_learner
):
    """Test getting insights with no data."""
    mock_repository.get_by_timerange.return_value = []

    insights = prediction_service.get_activity_insights()

    assert insights['productivity']['overall'] == 0.0
    assert all(v == 0.0 for v in insights['productivity']['by_time'].values())


def test_update_model(prediction_service, mock_learner, sample_activities):
    """Test model update."""
    mock_learner.performance_history = [0.8]

    was_adapted, accuracy = prediction_service.update_model(sample_activities[0])

    assert was_adapted is True
    assert accuracy == 0.8


def test_update_model_error(prediction_service, mock_learner, sample_activities):
    """Test model update error handling."""
    mock_learner.adapt_model.side_effect = Exception("Test error")

    was_adapted, accuracy = prediction_service.update_model(sample_activities[0])

    assert was_adapted is False
    assert accuracy is None