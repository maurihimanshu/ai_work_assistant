"""Tests for the ActivityFeatureExtractor."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.core.entities.activity import Activity
from src.core.ml.feature_extractor import ActivityFeatureExtractor


@pytest.fixture
def sample_activities():
    """Create sample activities for testing."""
    now = datetime.now()
    activities = []

    for i in range(3):
        activity = Activity(
            app_name=f"app_{i}",
            window_title=f"window_{i}",
            process_id=i,
            executable_path=f"/path/to/app_{i}",
            start_time=now + timedelta(minutes=i*5)
        )
        activity.active_time = float(60 * (i + 1))  # i+1 minutes active
        activity.idle_time = float(30 * (i + 1))    # (i+1)/2 minutes idle
        activity.end_time = activity.start_time + timedelta(
            seconds=activity.active_time + activity.idle_time
        )
        activities.append(activity)

    return activities


def test_feature_extractor_initialization():
    """Test feature extractor initialization."""
    extractor = ActivityFeatureExtractor()
    assert not extractor.is_fitted
    assert extractor.app_encoder is not None


def test_time_features_extraction():
    """Test extraction of time-based features."""
    extractor = ActivityFeatureExtractor()
    now = datetime.now()

    features = extractor._extract_time_features(now)

    assert 'hour' in features
    assert 'day_of_week' in features
    assert 'is_weekend' in features
    assert 'is_work_hours' in features
    assert 'time_period' in features

    assert 0 <= features['hour'] <= 23
    assert 0 <= features['day_of_week'] <= 6
    assert features['is_weekend'] in [0, 1]
    assert features['is_work_hours'] in [0, 1]
    assert 0 <= features['time_period'] <= 5


def test_duration_features_extraction(sample_activities):
    """Test extraction of duration-based features."""
    extractor = ActivityFeatureExtractor()

    # Test without previous activity
    features = extractor._extract_duration_features(sample_activities[0])
    assert features['active_time'] == 60.0
    assert features['idle_time'] == 30.0
    assert features['total_time'] == 90.0
    assert features['transition_time'] == 0

    # Test with previous activity
    features = extractor._extract_duration_features(
        sample_activities[1],
        sample_activities[0]
    )
    assert features['active_time'] == 120.0
    assert features['idle_time'] == 60.0
    assert features['total_time'] == 180.0
    assert features['transition_time'] > 0


def test_app_features_extraction(sample_activities):
    """Test extraction of application-based features."""
    extractor = ActivityFeatureExtractor()

    features = extractor._extract_app_features(sample_activities)

    assert 'app_id' in features
    assert 'app_switch' in features
    assert len(features['app_id']) == len(sample_activities)
    assert len(features['app_switch']) == len(sample_activities)
    assert features['app_switch'][0] == 0  # First activity
    assert features['app_switch'][1] == 1  # App switch


def test_window_features_extraction(sample_activities):
    """Test extraction of window-based features."""
    extractor = ActivityFeatureExtractor()

    features = extractor._extract_window_features(sample_activities, window_size=2)

    assert 'active_time_mean' in features
    assert 'idle_time_mean' in features
    assert 'activity_rate' in features
    assert len(features['active_time_mean']) == len(sample_activities)
    assert len(features['idle_time_mean']) == len(sample_activities)
    assert len(features['activity_rate']) == len(sample_activities)
    assert all(0 <= rate <= 1 for rate in features['activity_rate'])


def test_full_feature_extraction(sample_activities):
    """Test complete feature extraction pipeline."""
    extractor = ActivityFeatureExtractor()

    features_df = extractor.extract_features(sample_activities)

    assert isinstance(features_df, pd.DataFrame)
    assert len(features_df) == len(sample_activities)
    assert all(name in features_df.columns for name in extractor.get_feature_names())


def test_empty_activities_handling():
    """Test handling of empty activity list."""
    extractor = ActivityFeatureExtractor()

    features_df = extractor.extract_features([])
    assert isinstance(features_df, pd.DataFrame)
    assert features_df.empty


def test_feature_names():
    """Test getting feature names."""
    extractor = ActivityFeatureExtractor()
    names = extractor.get_feature_names()

    assert isinstance(names, list)
    assert len(names) > 0
    assert all(isinstance(name, str) for name in names)