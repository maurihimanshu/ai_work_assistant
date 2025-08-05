"""Tests for the ActivityCategorizer."""

from datetime import datetime, timedelta

import numpy as np
import pytest

from src.core.entities.activity import Activity
from src.core.ml.activity_categorizer import ActivityCategorizer, ActivityCategory


@pytest.fixture
def sample_activities():
    """Create sample activities for testing."""
    now = datetime.now()
    activities = []

    # Create work activities (morning)
    for i in range(10):
        activity = Activity(
            app_name="code.exe",
            window_title=f"Working on project {i}",
            process_id=i,
            executable_path=r"C:\Program Files\VSCode\code.exe",
            start_time=now.replace(hour=9) + timedelta(minutes=i * 5),
        )
        activity.active_time = 600.0  # 10 minutes
        activity.idle_time = 60.0  # 1 minute
        activities.append(activity)

    # Create communication activities (afternoon)
    for i in range(5):
        activity = Activity(
            app_name="teams.exe",
            window_title="Team Meeting",
            process_id=100 + i,
            executable_path=r"C:\Program Files\Teams\teams.exe",
            start_time=now.replace(hour=14) + timedelta(minutes=i * 10),
        )
        activity.active_time = 300.0  # 5 minutes
        activity.idle_time = 30.0  # 30 seconds
        activities.append(activity)

    # Create entertainment activities (evening)
    for i in range(3):
        activity = Activity(
            app_name="netflix.exe",
            window_title="Netflix",
            process_id=200 + i,
            executable_path=r"C:\Program Files\Netflix\netflix.exe",
            start_time=now.replace(hour=20) + timedelta(minutes=i * 20),
        )
        activity.active_time = 1800.0  # 30 minutes
        activity.idle_time = 120.0  # 2 minutes
        activities.append(activity)

    return activities


@pytest.fixture
def categorizer():
    """Create an activity categorizer instance."""
    return ActivityCategorizer(min_cluster_size=2, similarity_threshold=0.5)


def test_categorizer_initialization(categorizer):
    """Test categorizer initialization."""
    assert categorizer.min_cluster_size == 2
    assert categorizer.similarity_threshold == 0.5
    assert isinstance(categorizer.productivity_rules, dict)
    assert len(categorizer.categories) == 0


def test_get_time_period():
    """Test time period classification."""
    categorizer = ActivityCategorizer()
    now = datetime.now()

    assert categorizer._get_time_period(now.replace(hour=9)) == "morning"
    assert categorizer._get_time_period(now.replace(hour=14)) == "afternoon"
    assert categorizer._get_time_period(now.replace(hour=19)) == "evening"
    assert categorizer._get_time_period(now.replace(hour=23)) == "night"


def test_calculate_productivity_score(categorizer):
    """Test productivity score calculation."""
    # Test development tool
    score = categorizer._calculate_productivity_score({"code.exe"}, [3600.0])
    assert score == 1.0

    # Test entertainment app
    score = categorizer._calculate_productivity_score({"netflix.exe"}, [3600.0])
    assert score == 0.1

    # Test mixed apps
    score = categorizer._calculate_productivity_score(
        {"code.exe", "netflix.exe"}, [3600.0, 3600.0]
    )
    assert 0.1 < score < 1.0


def test_extract_category_features(categorizer, sample_activities):
    """Test feature extraction for categorization."""
    features, app_names, durations = categorizer._extract_category_features(
        sample_activities
    )

    assert isinstance(features, np.ndarray)
    assert len(features) == len(sample_activities)
    assert len(app_names) == len(sample_activities)
    assert len(durations) == len(sample_activities)
    assert all(isinstance(d, float) for d in durations)


def test_create_category(categorizer, sample_activities):
    """Test category creation."""
    # Get work activities
    work_activities = [a for a in sample_activities if a.app_name == "code.exe"]

    category = categorizer._create_category(sample_activities, work_activities)

    assert isinstance(category, ActivityCategory)
    assert "code.exe" in category.name
    assert "code.exe" in category.apps
    assert category.productivity_score == 1.0
    assert sum(category.time_patterns.values()) == pytest.approx(1.0)


def test_categorize_activities(categorizer, sample_activities):
    """Test activity categorization."""
    categories = categorizer.categorize_activities(sample_activities)

    assert len(categories) > 0
    assert all(isinstance(c, ActivityCategory) for c in categories.values())

    # Should have at least work, communication, and entertainment categories
    app_types = set()
    for category in categories.values():
        if "code.exe" in category.apps:
            app_types.add("work")
        elif "teams.exe" in category.apps:
            app_types.add("communication")
        elif "netflix.exe" in category.apps:
            app_types.add("entertainment")

    assert len(app_types) >= 3


def test_get_activity_insights(categorizer, sample_activities):
    """Test getting activity insights."""
    insights = categorizer.get_activity_insights(sample_activities)

    assert "overall_productivity" in insights
    assert "time_productivity" in insights
    assert "category_distribution" in insights
    assert "total_duration" in insights
    assert "unique_apps" in insights
    assert "activity_count" in insights

    assert 0 <= insights["overall_productivity"] <= 1
    assert len(insights["time_productivity"]) == 4
    assert insights["unique_apps"] == 3
    assert insights["activity_count"] == len(sample_activities)


def test_empty_activities(categorizer):
    """Test handling empty activity list."""
    categories = categorizer.categorize_activities([])
    assert categories == {}

    insights = categorizer.get_activity_insights([])
    assert insights == {}


def test_category_update_stats():
    """Test category statistics updates."""
    category = ActivityCategory(
        name="Test",
        apps={"test.exe"},
        typical_duration=100.0,
        time_patterns={"morning": 0.5, "afternoon": 0.5},
        productivity_score=0.8,
    )

    # Update with new duration
    category.update_stats(200.0)

    assert category.occurrence_count == 1
    assert category.total_duration == 200.0
    assert category.typical_duration == 200.0

    # Update again
    category.update_stats(300.0)

    assert category.occurrence_count == 2
    assert category.total_duration == 500.0
    assert category.typical_duration == 250.0  # Average of 200 and 300


def test_productivity_patterns(categorizer, sample_activities):
    """Test productivity pattern detection."""
    insights = categorizer.get_activity_insights(sample_activities)
    time_productivity = insights["time_productivity"]

    # Morning should be most productive (coding)
    assert time_productivity["morning"] > time_productivity["evening"]

    # Evening should be least productive (entertainment)
    # Use round to handle floating-point comparison
    evening_productivity = round(time_productivity["evening"], 3)
    min_productivity = round(min(time_productivity.values()), 3)
    assert evening_productivity <= min_productivity
