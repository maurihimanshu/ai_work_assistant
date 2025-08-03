"""Tests for the task suggestion service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.core.entities.activity import Activity
from src.core.events.event_dispatcher import EventDispatcher
from src.core.events.event_types import ActivityEndEvent, ProductivityAlertEvent
from src.core.ml.activity_categorizer import ActivityCategorizer
from src.core.ml.continuous_learner import ContinuousLearner
from src.core.services.task_suggestion_service import TaskSuggestionService


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return MagicMock()


@pytest.fixture
def mock_dispatcher():
    """Create mock event dispatcher."""
    return MagicMock(spec=EventDispatcher)


@pytest.fixture
def mock_categorizer():
    """Create mock activity categorizer."""
    categorizer = MagicMock(spec=ActivityCategorizer)
    categorizer.get_activity_insights.return_value = {
        "overall_productivity": 0.75,
        "category_distribution": {
            "Development": {"productivity_score": 0.8, "occurrence_count": 2},
            "Communication": {"productivity_score": 0.7, "occurrence_count": 1},
            "Research": {"productivity_score": 0.6, "occurrence_count": 1}
        },
        "time_productivity": {
            "morning": 0.8,
            "afternoon": 0.6,
            "evening": 0.7
        }
    }
    return categorizer


@pytest.fixture
def mock_learner():
    """Create mock continuous learner."""
    learner = MagicMock(spec=ContinuousLearner)
    learner.predict_next.return_value = "Development IDE"
    return learner


@pytest.fixture
def suggestion_service(
    mock_repository,
    mock_dispatcher,
    mock_categorizer,
    mock_learner
):
    """Create task suggestion service."""
    return TaskSuggestionService(
        repository=mock_repository,
        event_dispatcher=mock_dispatcher,
        categorizer=mock_categorizer,
        learner=mock_learner
    )


@pytest.fixture
def sample_activities():
    """Create sample activities."""
    current_time = datetime.now()
    activities = []

    # Create activities over last 4 hours
    for i in range(4):
        start_time = current_time - timedelta(hours=4-i)
        end_time = start_time + timedelta(minutes=50)

        activity = Activity(
            app_name=f"test_app_{i}",
            window_title=f"Test Window {i}",
            process_id=1000 + i,
            executable_path=f"/path/to/test_{i}",
            start_time=start_time,
            end_time=end_time
        )
        activities.append(activity)

    return activities


def test_initialization(suggestion_service, mock_dispatcher):
    """Test service initialization."""
    assert suggestion_service.productivity_threshold == 0.7
    assert suggestion_service.suggestion_interval == timedelta(hours=1)
    assert suggestion_service.analysis_window == timedelta(days=7)
    mock_dispatcher.subscribe.assert_called_once()


def test_time_based_suggestions(suggestion_service):
    """Test time-based suggestions."""
    # Test morning suggestions
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 10, 0)  # 10 AM
        suggestions = suggestion_service._get_time_based_suggestions(
            mock_dt.now(),
            []
        )
        assert len(suggestions) == 3
        assert "Review your goals for the day" in suggestions

    # Test afternoon suggestions
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 15, 0)  # 3 PM
        suggestions = suggestion_service._get_time_based_suggestions(
            mock_dt.now(),
            []
        )
        assert len(suggestions) == 3
        assert "Focus on completing ongoing tasks" in suggestions


def test_productivity_based_suggestions(
    suggestion_service,
    mock_categorizer,
    sample_activities
):
    """Test productivity-based suggestions."""
    # Mock low productivity scenario
    mock_categorizer.get_activity_insights.return_value = {
        "overall_productivity": 0.5,
        "category_distribution": {
            "Social Media": {"productivity_score": 0.3, "occurrence_count": 5},
            "Development": {"productivity_score": 0.8, "occurrence_count": 3}
        }
    }

    suggestions = suggestion_service._get_productivity_based_suggestions(
        0.5,  # Below threshold
        sample_activities
    )

    assert len(suggestions) > 0
    assert any("break" in s.lower() for s in suggestions)
    assert any("Social Media" in s for s in suggestions)


def test_pattern_based_suggestions(
    suggestion_service,
    mock_learner,
    mock_categorizer,
    sample_activities
):
    """Test pattern-based suggestions."""
    # Mock learner prediction
    mock_learner.predict_next.return_value = "Development IDE"

    # Mock categorizer insights
    mock_categorizer.get_activity_insights.return_value = {
        "overall_productivity": 0.75,
        "category_distribution": {
            "Development": {"productivity_score": 0.8, "occurrence_count": 4},
            "Communication": {"productivity_score": 0.7, "occurrence_count": 4},
            "Research": {"productivity_score": 0.6, "occurrence_count": 4}
        },
        "time_productivity": {
            "morning": 0.8,
            "afternoon": 0.6,
            "evening": 0.7
        },
        "context_switches": {
            "frequency": "high",
            "impact": -0.2
        }
    }

    suggestions = suggestion_service._get_pattern_based_suggestions(
        sample_activities
    )

    assert len(suggestions) > 0
    assert any("Development IDE" in s for s in suggestions)
    assert any("context switch" in s.lower() for s in suggestions)


def test_break_suggestions(suggestion_service, sample_activities):
    """Test break-related suggestions."""
    # Modify sample activities to simulate long work session
    for activity in sample_activities:
        activity.active_time = 3600.0  # 1 hour each

    suggestions = suggestion_service._get_break_suggestions(sample_activities)

    # Should suggest breaks for long work session
    assert len(suggestions) > 0
    assert any("break" in s.lower() for s in suggestions)
    assert any("walk" in s.lower() or "stretch" in s.lower() for s in suggestions)


def test_handle_activity_end(
    suggestion_service,
    mock_repository,
    mock_dispatcher,
    mock_categorizer,
    sample_activities
):
    """Test activity end event handling."""
    # Mock repository response
    mock_repository.get_by_timerange.return_value = sample_activities

    # Create activity end event
    event = ActivityEndEvent(
        activity=sample_activities[-1],
        duration=3600,
        timestamp=datetime.now()
    )

    # Handle event
    suggestion_service._handle_activity_end(event)

    # Verify productivity alert was dispatched
    mock_dispatcher.dispatch.assert_called()
    call_args = mock_dispatcher.dispatch.call_args[0][0]
    assert isinstance(call_args, ProductivityAlertEvent)
    assert call_args.productivity_score == 0.75
    assert len(call_args.suggestions) > 0


def test_get_current_suggestions(
    suggestion_service,
    mock_repository,
    mock_categorizer,
    sample_activities
):
    """Test getting current suggestions."""
    # Mock repository response
    mock_repository.get_by_timerange.return_value = sample_activities

    suggestions, score = suggestion_service.get_current_suggestions()

    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert isinstance(score, float)
    assert score == 0.75


def test_error_handling(
    suggestion_service,
    mock_repository,
    mock_dispatcher
):
    """Test error handling in suggestion generation."""
    # Mock repository to raise exception
    mock_repository.get_by_timerange.side_effect = Exception("Test error")

    # Should not raise exception
    suggestions, score = suggestion_service.get_current_suggestions()

    assert suggestions == []
    assert score == 0.5
    mock_dispatcher.dispatch.assert_not_called()


def test_suggestion_interval(
    suggestion_service,
    mock_repository,
    mock_dispatcher,
    sample_activities
):
    """Test suggestion interval handling."""
    # Mock repository response
    mock_repository.get_by_timerange.return_value = sample_activities

    # Create activity end event
    event = ActivityEndEvent(
        activity=sample_activities[-1],
        duration=3600,
        timestamp=datetime.now()
    )

    # First call should generate suggestions
    suggestion_service._handle_activity_end(event)
    assert mock_dispatcher.dispatch.call_count == 1

    # Second immediate call should not generate suggestions
    suggestion_service._handle_activity_end(event)
    assert mock_dispatcher.dispatch.call_count == 1

    # Call after interval should generate suggestions
    suggestion_service.last_suggestion_time -= timedelta(hours=2)
    suggestion_service._handle_activity_end(event)
    assert mock_dispatcher.dispatch.call_count == 2