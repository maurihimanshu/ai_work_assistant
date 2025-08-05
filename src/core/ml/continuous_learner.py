"""Continuous learning system for adapting to user behavior."""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier

from ..entities.activity import Activity
from .feature_extractor import ActivityFeatureExtractor

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """Continuous learning model for activity prediction."""

    def __init__(self, model_dir: str = None, event_dispatcher=None):
        """Initialize continuous learner.

        Args:
            model_dir: Directory to save/load model
            event_dispatcher: Event dispatcher instance
        """
        self.model_dir = model_dir or "data/models"
        self.event_dispatcher = event_dispatcher
        self.feature_extractor = ActivityFeatureExtractor()
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.is_fitted = False
        self._load_model()

    def _load_model(self) -> None:
        """Load model from disk if available."""
        try:
            if not os.path.exists(self.model_dir):
                os.makedirs(self.model_dir)

            model_path = os.path.join(self.model_dir, "activity_model.joblib")
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                self.is_fitted = True
                logger.info("Loaded existing model")
            else:
                logger.info("No existing model found")

        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)

    def _save_model(self) -> None:
        """Save model to disk."""
        try:
            if not os.path.exists(self.model_dir):
                os.makedirs(self.model_dir)

            model_path = os.path.join(self.model_dir, "activity_model.joblib")
            joblib.dump(self.model, model_path)
            logger.info("Saved model to disk")

        except Exception as e:
            logger.error(f"Error saving model: {e}", exc_info=True)

    def fit(self, activities: List[Dict]) -> None:
        """Train model on activities.

        Args:
            activities: List of activity dictionaries
        """
        try:
            if not activities:
                logger.warning("No activities provided for training")
                return

            # Extract features and labels
            X = self.feature_extractor.extract_features(activities)
            y = self.feature_extractor.extract_labels(activities)

            if len(X) == 0 or len(y) == 0:
                logger.warning("No valid features/labels extracted")
                return

            # Train model
            self.model.fit(X, y)
            self.is_fitted = True
            logger.info(f"Model trained on {len(X)} samples")

            # Save model
            self._save_model()

        except Exception as e:
            logger.error(f"Error training model: {e}", exc_info=True)

    def predict_next(self, recent_activities: List[Dict]) -> List[Dict]:
        """Predict next likely activities.

        Args:
            recent_activities: List of recent activities

        Returns:
            list: Predicted activities with confidence scores
        """
        try:
            if not self.is_fitted:
                logger.warning("Model not trained yet")
                return []

            if not recent_activities:
                logger.warning("No recent activities provided")
                return []

            # Extract features
            X = self.feature_extractor.extract_features(recent_activities)
            if len(X) == 0:
                logger.warning("No valid features extracted")
                return []

            # Get predictions and probabilities
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)

            # Format predictions
            results = []
            for pred, probs in zip(predictions, probabilities):
                confidence = max(probs)
                if confidence > 0.3:  # Only include predictions with reasonable confidence
                    results.append({
                        "type": pred,
                        "confidence": confidence
                    })

            return sorted(results, key=lambda x: x["confidence"], reverse=True)[:5]  # Return top 5

        except Exception as e:
            logger.error(f"Error making prediction: {e}", exc_info=True)
            return []

    def update(self, new_activities: List[Dict]) -> None:
        """Update model with new activities.

        Args:
            new_activities: List of new activities
        """
        try:
            if not new_activities:
                return

            # If model not trained yet, do initial training
            if not self.is_fitted:
                self.fit(new_activities)
                return

            # Extract features and labels
            X_new = self.feature_extractor.extract_features(new_activities)
            y_new = self.feature_extractor.extract_labels(new_activities)

            if len(X_new) == 0 or len(y_new) == 0:
                return

            # Partial fit not available for RandomForest, so we retrain
            # In a production system, we might want to use a different model
            # that supports partial_fit, or maintain a buffer of recent data
            self.model.fit(X_new, y_new)
            self._save_model()

            logger.info(f"Model updated with {len(X_new)} new samples")

        except Exception as e:
            logger.error(f"Error updating model: {e}", exc_info=True)
