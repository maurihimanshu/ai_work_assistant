"""Management of machine learning models."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

from ..entities.activity import Activity
from .feature_extractor import ActivityFeatureExtractor

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages machine learning models for activity prediction."""

    def __init__(self, models_dir: str):
        """Initialize the model manager.

        Args:
            models_dir: Directory to store models and metadata
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.feature_extractor = ActivityFeatureExtractor()
        self.current_model: Optional[BaseEstimator] = None
        self.model_metadata: Dict[str, Any] = {}

    def _save_model(self, model: BaseEstimator, metadata: Dict[str, Any]) -> None:
        """Save model and its metadata.

        Args:
            model: Trained model to save
            metadata: Model metadata
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = self.models_dir / f"model_{timestamp}.joblib"
        meta_path = self.models_dir / f"metadata_{timestamp}.json"

        # Save model
        joblib.dump(model, model_path)

        # Save metadata
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        # Update current model and metadata
        self.current_model = model
        self.model_metadata = metadata

    def _load_latest_model(self) -> Tuple[Optional[BaseEstimator], Dict[str, Any]]:
        """Load the latest saved model and its metadata.

        Returns:
            tuple: (model, metadata) or (None, {}) if no model found
        """
        model_files = list(self.models_dir.glob("model_*.joblib"))
        if not model_files:
            return None, {}

        # Get latest model file
        latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
        latest_meta = latest_model.parent / f"metadata_{latest_model.stem[6:]}.json"

        if not latest_meta.exists():
            return None, {}

        # Load model and metadata
        model = joblib.load(latest_model)
        with open(latest_meta) as f:
            metadata = json.load(f)

        return model, metadata

    def _evaluate_model(
        self, model: BaseEstimator, X_test: np.ndarray, y_test: np.ndarray
    ) -> Dict[str, float]:
        """Evaluate model performance.

        Args:
            model: Model to evaluate
            X_test: Test features
            y_test: Test labels

        Returns:
            dict: Performance metrics
        """
        y_pred = model.predict(X_test)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="weighted"
        )

        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }

    def train_model(
        self, activities: List[Activity], test_size: float = 0.2, random_state: int = 42
    ) -> Dict[str, float]:
        """Train a new model on activity data.

        Args:
            activities: List of activities to train on
            test_size: Proportion of data to use for testing
            random_state: Random seed for reproducibility

        Returns:
            dict: Model performance metrics
        """
        # Extract features
        features_df = self.feature_extractor.extract_features(activities)
        if features_df.empty:
            raise ValueError("No features extracted from activities")

        # Prepare target variable (next app prediction)
        app_ids = features_df["app_id"].values
        y = np.roll(app_ids, -1)  # Shift app_ids by -1 to get next app
        y = y[:-1]  # Remove last row as we don't know the next app
        X = features_df.iloc[:-1].values  # Remove last row to match y

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=random_state)
        model.fit(X_train, y_train)

        # Evaluate model
        metrics = self._evaluate_model(model, X_test, y_test)

        # Save model and metadata
        metadata = {
            "trained_at": datetime.now(),
            "n_samples": len(X),
            "feature_names": self.feature_extractor.get_feature_names(),
            "metrics": metrics,
            "parameters": model.get_params(),
        }
        self._save_model(model, metadata)

        return metrics

    def predict_next_activity(
        self, current_activities: List[Activity]
    ) -> Optional[str]:
        """Predict the next application based on current activities.

        Args:
            current_activities: Recent activities to base prediction on

        Returns:
            str: Predicted next application name or None if prediction not possible
        """
        if not self.current_model:
            model, metadata = self._load_latest_model()
            if not model:
                return None
            self.current_model = model
            self.model_metadata = metadata

        # Extract features
        features_df = self.feature_extractor.extract_features(current_activities)
        if features_df.empty:
            return None

        # Make prediction
        try:
            X = features_df.iloc[-1:].values  # Use last activity's features
            app_id = self.current_model.predict(X)[0]
            return self.feature_extractor.app_encoder.inverse_transform([app_id])[0]
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.

        Returns:
            dict: Model information and metrics
        """
        if not self.current_model:
            model, metadata = self._load_latest_model()
            if not model:
                return {}
            self.current_model = model
            self.model_metadata = metadata

        return self.model_metadata
