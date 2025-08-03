"""Tests for the AnalyticsService."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.core.entities.activity import Activity
from src.core.events.event_dispatcher import EventDispatcher
from src.core.ml.activity_categorizer import ActivityCategorizer
from src.core.services.analytics_service import AnalyticsService


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
    """Create mock categorizer."""
    return MagicMock(spec=ActivityCategorizer)


@pytest.fixture
def analytics_service(mock_repository, mock_dispatcher, mock_categorizer):
    """Create analytics service for testing."""
    return AnalyticsService(
        repository=mock_repository,
        event_dispatcher=mock_dispatcher,
        categorizer=mock_categorizer,
        update_interval=timedelta(minutes=30),
        analysis_window=timedelta(days=30)
    )


@pytest.fixture
def sample_activities():
    """Create sample activities."""
    current_time = datetime.now()
    activities = []

    for i in range(8):
        start_time = current_time - timedelta(hours=i)
        end_time = start_time + timedelta(minutes=45)

        activity = Activity(
            app_name=f'test_app_{i}',
            window_title=f'Test Window {i}',
            process_id=1000 + i,
            executable_path=f'/path/to/test_{i}',
            start_time=start_time,
            end_time=end_time,
            active_time=2700,  # 45 minutes
            idle_time=300  # 5 minutes
        )
        activities.append(activity)

    return activities


def test_initialization(analytics_service):
    """Test service initialization."""
    assert analytics_service.analysis_window == timedelta(days=30)
    assert analytics_service.update_interval == timedelta(minutes=30)


def test_get_empty_report(analytics_service):
    """Test getting empty report."""
    start_time = datetime.now() - timedelta(days=30)
    end_time = datetime.now()

    report = analytics_service._get_empty_report(start_time, end_time)

    assert report['summary']['time_period']['start'] == start_time.isoformat()
    assert report['summary']['time_period']['end'] == end_time.isoformat()
    assert report['summary']['overall_productivity'] == 0.0
    assert report['summary']['total_active_time'] == 0.0
    assert report['summary']['total_idle_time'] == 0.0
    assert report['app_patterns'] == {}
    assert report['behavior_patterns'] == []
    assert report['daily_metrics'] == {}
    assert report['productivity_trends'] == {}


def test_calculate_overall_productivity(analytics_service, sample_activities):
    """Test overall productivity calculation."""
    productivity = analytics_service._calculate_overall_productivity(sample_activities)

    assert 0.0 <= productivity <= 1.0
    assert productivity > 0.8  # High productivity in sample data


def test_get_app_patterns(analytics_service, sample_activities):
    """Test app pattern analysis."""
    patterns = analytics_service._get_app_patterns(sample_activities)

    assert len(patterns) > 0
    for app_name, stats in patterns.items():
        assert 'total_time' in stats
        assert 'active_time' in stats
        assert 'idle_time' in stats
        assert 'usage_percentage' in stats
        assert stats['total_time'] > 0
        assert stats['active_time'] > 0
        assert stats['idle_time'] > 0
        assert 0.0 <= stats['usage_percentage'] <= 1.0


def test_get_behavior_patterns(analytics_service, sample_activities):
    """Test behavior pattern detection."""
    patterns = analytics_service._get_behavior_patterns(sample_activities)

    assert isinstance(patterns, list)
    for pattern in patterns:
        assert 'type' in pattern
        assert 'details' in pattern
        assert 'significance' in pattern
        assert 0.0 <= pattern['significance'] <= 1.0


def test_get_daily_metrics(analytics_service, sample_activities):
    """Test daily metrics calculation."""
    metrics = analytics_service._get_daily_metrics(sample_activities)

    assert len(metrics) > 0
    for date, stats in metrics.items():
        assert 'active_time' in stats
        assert 'idle_time' in stats
        assert 'productivity' in stats
        assert stats['active_time'] > 0
        assert stats['idle_time'] > 0
        assert 0.0 <= stats['productivity'] <= 1.0


def test_get_productivity_trends(analytics_service, sample_activities):
    """Test productivity trend analysis."""
    trends = analytics_service._get_productivity_trends(sample_activities)

    assert 'hourly' in trends
    assert 'daily' in trends
    assert len(trends['hourly']) == 24
    assert len(trends['daily']) == 7
    assert all(0.0 <= x <= 1.0 for x in trends['hourly'])
    assert all(0.0 <= x <= 1.0 for x in trends['daily'])


def test_update_analytics(analytics_service, mock_repository, mock_dispatcher):
    """Test analytics update process."""
    # Mock repository response
    mock_repository.get_by_timerange.return_value = []

    # Update analytics
    analytics_service.update_analytics()

    # Verify repository was called
    mock_repository.get_by_timerange.assert_called_once()

    # No events should be dispatched for empty activities
    assert not mock_dispatcher.dispatch.called


def test_get_productivity_report(
    analytics_service,
    mock_repository,
    sample_activities
):
    """Test productivity report generation."""
    # Mock repository response
    mock_repository.get_by_timerange.return_value = sample_activities

    report = analytics_service.get_productivity_report()

    assert 'summary' in report
    assert 'app_patterns' in report
    assert 'behavior_patterns' in report
    assert 'daily_metrics' in report
    assert 'productivity_trends' in report

    assert report['summary']['overall_productivity'] > 0.0
    assert report['summary']['total_active_time'] > 0.0
    assert report['summary']['total_idle_time'] > 0.0


def test_update_interval(analytics_service, mock_repository, mock_dispatcher):
    """Test update interval handling."""
    # Initialize last_update
    analytics_service.last_update = datetime.now()

    # Mock repository response
    mock_repository.get_by_timerange.return_value = []

    # First update should proceed
    analytics_service.update_analytics()
    initial_call_count = mock_repository.get_by_timerange.call_count

    # Immediate update should be skipped
    analytics_service.update_analytics()
    assert mock_repository.get_by_timerange.call_count == initial_call_count

    # Update after interval should proceed
    analytics_service.last_update -= timedelta(hours=2)
    analytics_service.update_analytics()
    assert mock_repository.get_by_timerange.call_count > initial_call_count