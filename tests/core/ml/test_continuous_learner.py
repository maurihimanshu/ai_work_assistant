"""Tests for the ContinuousLearner."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from src.core.entities.activity import Activity
from src.core.ml.continuous_learner import ContinuousLearner


@pytest.fixture
def sample_activities():
    """Create sample activities for testing."""
    now = datetime.now()
    activities = []

    # Create activities with a pattern (alternating between two apps)
    for i in range(100):
        activity = Activity(
            app_name=f"app_{i % 2}",  # Alternates between app_0 and app_1
            window_title=f"window_{i}",
            process_id=i,
            executable_path=f"/path/to/app_{i % 2}",
            start_time=now + timedelta(minutes=i*5)
        )
        activity.active_time = float(60)  # 1 minute active
        activity.idle_time = float(30)    # 30 seconds idle
        activity.end_time = activity.start_time + timedelta(
            seconds=activity.active_time + activity.idle_time
        )
        activities.append(activity)

    return activities


@pytest.fixture
def learner():
    """Create a continuous learner instance."""
    return ContinuousLearner(
        window_size=50,
        adaptation_rate=0.3,
        min_samples_adapt=10,
        performance_threshold=0.7
    )


def test_learner_initialization(learner):
    """Test learner initialization."""
    assert isinstance(learner.current_model, RandomForestClassifier)
    assert learner.window_size == 50
    assert learner.adaptation_rate == 0.3
    assert learner.min_samples_adapt == 10
    assert learner.performance_threshold == 0.7
    assert len(learner.activity_window) == 0
    assert len(learner.performance_history) == 0
    assert learner.last_adaptation is None


def test_update_window(learner, sample_activities):
    """Test updating activity window."""
    # Add activities up to window size
    for activity in sample_activities[:60]:
        learner._update_window(activity)

    assert len(learner.activity_window) == 50  # Window size limit
    assert learner.activity_window[-1] == sample_activities[59]  # Most recent
    assert learner.activity_window[0] == sample_activities[10]  # Oldest


def test_should_adapt_insufficient_samples(learner):
    """Test adaptation check with insufficient samples."""
    assert not learner._should_adapt()


def test_should_adapt_initial(learner, sample_activities):
    """Test adaptation check for initial adaptation."""
    for activity in sample_activities[:20]:
        learner._update_window(activity)

    assert learner._should_adapt()


def test_should_adapt_performance_degradation(learner):
    """Test adaptation check with degrading performance."""
    learner.performance_history = [0.9, 0.8]  # Decreasing performance
    learner.last_adaptation = datetime.now()

    # Create a sample activity
    activity = Activity(
        app_name="test_app",
        window_title="Test Window",
        process_id=1234,
        executable_path="/path/to/test",
        start_time=datetime.now()
    )

    for _ in range(20):
        learner.activity_window.append(activity)

    assert learner._should_adapt()


def test_prepare_adaptation_data(learner, sample_activities):
    """Test preparation of adaptation data."""
    for activity in sample_activities[:20]:
        learner._update_window(activity)

    X, y, unique_apps = learner._prepare_adaptation_data()

    assert isinstance(X, np.ndarray)
    assert isinstance(y, np.ndarray)
    assert isinstance(unique_apps, list)
    assert len(unique_apps) == 2  # app_0 and app_1
    assert X.shape[0] == len(learner.activity_window)
    assert len(y) == len(learner.activity_window)


def test_evaluate_adaptation(learner):
    """Test adaptation evaluation."""
    # Create simple test data
    X = np.random.rand(100, 5)
    y = np.random.randint(0, 2, 100)

    model = RandomForestClassifier(n_estimators=10)
    model.fit(X[:80], y[:80])  # Train on first 80%

    accuracy = learner._evaluate_adaptation(X, y, model)

    assert isinstance(accuracy, float)
    assert 0 <= accuracy <= 1


def test_adapt_model_success(learner, sample_activities):
    """Test successful model adaptation."""
    # Add enough activities for adaptation
    for activity in sample_activities[:30]:
        learner._update_window(activity)

    was_adapted, accuracy = learner.adapt_model()

    assert was_adapted
    assert isinstance(accuracy, float)
    assert accuracy >= learner.performance_threshold
    assert learner.last_adaptation is not None
    assert len(learner.performance_history) == 1


def test_adapt_model_insufficient_data(learner):
    """Test adaptation with insufficient data."""
    was_adapted, accuracy = learner.adapt_model()

    assert not was_adapted
    assert accuracy is None


def test_predict_next_success(learner, sample_activities):
    """Test successful prediction."""
    # Train the model first
    for activity in sample_activities[:30]:
        learner.update(activity)

    prediction = learner.predict_next(sample_activities[20:25])

    assert prediction in ['app_0', 'app_1']


def test_predict_next_no_data(learner):
    """Test prediction with no data."""
    prediction = learner.predict_next([])
    assert prediction is None


def test_get_performance_stats_empty(learner):
    """Test getting performance stats with no history."""
    stats = learner.get_performance_stats()
    assert stats == {}


def test_get_performance_stats(learner):
    """Test getting performance stats with history."""
    learner.performance_history = [0.8, 0.85, 0.9]

    stats = learner.get_performance_stats()

    assert 'current_accuracy' in stats
    assert 'average_accuracy' in stats
    assert 'min_accuracy' in stats
    assert 'max_accuracy' in stats
    assert 'adaptation_count' in stats
    assert stats['current_accuracy'] == 0.9
    assert stats['min_accuracy'] == 0.8
    assert stats['max_accuracy'] == 0.9
    assert stats['adaptation_count'] == 3


def test_continuous_learning_cycle(learner, sample_activities):
    """Test complete continuous learning cycle."""
    # Initial training
    for activity in sample_activities[:30]:
        learner.update(activity)

    assert len(learner.performance_history) > 0
    initial_performance = learner.performance_history[-1]

    # Continue learning
    for activity in sample_activities[30:60]:
        learner.update(activity)

    if len(learner.performance_history) > 1:
        final_performance = learner.performance_history[-1]
        assert final_performance >= learner.performance_threshold