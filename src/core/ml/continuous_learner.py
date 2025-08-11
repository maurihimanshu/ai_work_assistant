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
from sklearn.linear_model import SGDClassifier

from ..entities.activity import Activity
from .feature_extractor import ActivityFeatureExtractor

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """Continuous learning model for activity prediction."""

    def __init__(
        self, model_dir: str = None, event_dispatcher=None, use_online: bool = False
    ):
        """Initialize continuous learner.

        Args:
            model_dir: Directory to save/load model
            event_dispatcher: Event dispatcher instance
            use_online: If True, use an incremental model with partial_fit
        """
        self.model_dir = model_dir or "data/models"
        self.event_dispatcher = event_dispatcher
        self.feature_extractor = ActivityFeatureExtractor()
        self.use_online = use_online
        if use_online:
            # Linear classifier with hinge loss; supports partial_fit
            self.model = SGDClassifier(loss="log_loss", alpha=1e-4, random_state=42)
            self._known_classes = None
        else:
            self.model = RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42
            )
        self.is_fitted = False
        self._load_model()

    def _get_model_path(self) -> str:
        filename = (
            "activity_model_online.joblib"
            if self.use_online
            else "activity_model.joblib"
        )
        return os.path.join(self.model_dir, filename)

    def _load_model(self) -> None:
        """Load model from disk if available."""
        try:
            if not os.path.exists(self.model_dir):
                os.makedirs(self.model_dir)

            model_path = self._get_model_path()
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                self.is_fitted = True
                logger.info("Loaded existing model")
                # If in online mode but loaded model doesn't support partial_fit, reset to SGD
                if self.use_online and not hasattr(self.model, "partial_fit"):
                    logger.warning(
                        "Loaded model is not incremental; reinitializing SGDClassifier"
                    )
                    self.model = SGDClassifier(
                        loss="log_loss", alpha=1e-4, random_state=42
                    )
                    self.is_fitted = False
                    self._known_classes = None
                elif self.use_online:
                    # Recover known classes from the persisted estimator if available
                    self._known_classes = getattr(self.model, "classes_", None)
            else:
                logger.info("No existing model found")

        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)

    def _save_model(self) -> None:
        """Save model to disk."""
        try:
            if not os.path.exists(self.model_dir):
                os.makedirs(self.model_dir)

            model_path = self._get_model_path()
            joblib.dump(self.model, model_path)
            logger.info("Saved model to disk")

        except Exception as e:
            logger.error(f"Error saving model: {e}", exc_info=True)

    def _ensure_incremental_estimator(self) -> None:
        """Ensure the estimator supports partial_fit in online mode."""
        if not hasattr(self.model, "partial_fit"):
            self.model = SGDClassifier(loss="log_loss", alpha=1e-4, random_state=42)
            self.is_fitted = False
            self._known_classes = None

    def _reinitialize_with_classes(self, classes: np.ndarray) -> None:
        """Reinitialize incremental model with a new class set."""
        logger.warning(
            "Reinitializing incremental model with updated classes: %s", list(classes)
        )
        self.model = SGDClassifier(loss="log_loss", alpha=1e-4, random_state=42)
        self.is_fitted = False
        self._known_classes = np.array(sorted(np.unique(classes)))

    def _initial_partial_fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Perform the first partial_fit call establishing the class set."""
        self._ensure_incremental_estimator()
        if self._known_classes is None:
            self._known_classes = np.array(sorted(np.unique(y)))
        self.model.partial_fit(X, y, classes=self._known_classes)
        self.is_fitted = True

    def _incremental_partial_fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Perform subsequent partial_fit calls without changing class set."""
        # If classifier has classes_, use them; otherwise initialize
        model_classes = getattr(self.model, "classes_", None)
        if model_classes is None or not self.is_fitted:
            self._initial_partial_fit(X, y)
            return
        # If y contains unseen labels, we must reinitialize to expand class set
        unique_new = np.unique(y)
        unseen = [c for c in unique_new if c not in model_classes]
        if unseen:
            # Expand classes and reinit; first call must include full class set
            expanded = np.array(
                sorted(np.unique(np.concatenate([model_classes, unique_new])))
            )
            self._reinitialize_with_classes(expanded)
            self.model.partial_fit(X, y, classes=self._known_classes)
            self.is_fitted = True
            return
        # Safe to update without classes argument
        self.model.partial_fit(X, y)

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
            if self.use_online:
                self._ensure_incremental_estimator()
                if not self.is_fitted or getattr(self.model, "classes_", None) is None:
                    self._initial_partial_fit(X, y)
                else:
                    self._incremental_partial_fit(X, y)
            else:
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
                if (
                    confidence > 0.3
                ):  # Only include predictions with reasonable confidence
                    results.append({"type": pred, "confidence": confidence})

            return sorted(results, key=lambda x: x["confidence"], reverse=True)[
                :5
            ]  # Return top 5

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

            if self.use_online:
                self._ensure_incremental_estimator()
                self._incremental_partial_fit(X_new, y_new)
            else:
                # Retrain on new batch
                self.model.fit(X_new, y_new)
                self.is_fitted = True
            self._save_model()

            logger.info(f"Model updated with {len(X_new)} new samples")

        except Exception as e:
            logger.error(f"Error updating model: {e}", exc_info=True)
