"""Main entry point for the AI Work Assistant application."""

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from core.events.event_dispatcher import EventDispatcher
from core.ml.activity_categorizer import ActivityCategorizer
from core.ml.continuous_learner import ContinuousLearner
from core.services.activity_monitor import ActivityMonitor
from core.services.analytics_service import AnalyticsService
from core.services.prediction_service import PredictionService
from core.services.session_service import SessionService
from core.services.task_suggestion_service import TaskSuggestionService
from infrastructure.os.platform_monitor import PlatformMonitor
from infrastructure.storage.encrypted_json_storage import EncryptedJsonStorage
from presentation.ui.dashboard import Dashboard
from presentation.ui.system_tray import SystemTrayApp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)

def setup_data_directories():
    """Create necessary data directories if they don't exist."""
    directories = [
        "data",
        "data/activities",
        "data/models",
        "data/sessions",
        "logs",
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def initialize_services():
    """Initialize all application services.

    Returns:
        tuple: Initialized service instances
    """
    try:
        # Initialize event system
        logger.info("Initializing event system...")
        event_dispatcher = EventDispatcher()

        # Initialize data storage
        logger.info("Initializing data storage...")
        activity_storage = EncryptedJsonStorage(
            "data/activities/activities.json",
            encryption_key_file="data/activities/key.key",
        )

        # Initialize ML components
        logger.info("Initializing ML components...")
        logger.info("Initializing continuous learner...")
        learner = ContinuousLearner(
            model_dir="data/models",
            event_dispatcher=event_dispatcher
        )

        # Initialize activity categorizer
        categorizer = ActivityCategorizer()

        # Initialize platform monitor
        platform_monitor = PlatformMonitor()

        # Initialize activity monitor
        logger.info("Initializing activity monitor...")
        activity_monitor = ActivityMonitor(
            platform_monitor=platform_monitor,
            activity_storage=activity_storage,
            event_dispatcher=event_dispatcher,
        )

        # Initialize analytics service
        logger.info("Initializing analytics service...")
        analytics_service = AnalyticsService(
            repository=activity_storage,
            event_dispatcher=event_dispatcher,
            categorizer=categorizer,
        )

        # Initialize session service
        logger.info("Initializing session service...")
        session_service = SessionService(
            activity_monitor=activity_monitor,
            event_dispatcher=event_dispatcher,
            session_dir="data/sessions",
        )

        # Initialize prediction service
        prediction_service = PredictionService(
            repository=activity_storage,
            learner=learner,
            categorizer=categorizer,
        )

        # Initialize suggestion service
        logger.info("Initializing suggestion service...")
        suggestion_service = TaskSuggestionService(
            repository=activity_storage,
            event_dispatcher=event_dispatcher,
            categorizer=categorizer,
            learner=learner,
        )

        return (
            event_dispatcher,
            activity_storage,
            activity_monitor,
            analytics_service,
            session_service,
            prediction_service,
            suggestion_service,
        )

    except Exception as e:
        logger.error(f"Error initializing services: {e}", exc_info=True)
        raise

def main():
    """Main entry point."""
    try:
        logger.info("Starting AI Work Assistant...")

        # Create data directories
        setup_data_directories()

        # Initialize Qt application
        logger.info("Initializing Qt application...")
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # Initialize services
        logger.info("Initializing services...")
        (
            event_dispatcher,
            activity_storage,
            activity_monitor,
            analytics_service,
            session_service,
            prediction_service,
            suggestion_service,
        ) = initialize_services()

        # Create system tray application
        logger.info("Creating system tray application...")
        system_tray = SystemTrayApp(
            activity_monitor=activity_monitor,
            session_service=session_service,
            analytics_service=analytics_service,
            suggestion_service=suggestion_service,
            event_dispatcher=event_dispatcher,
        )

        # Create and show dashboard
        logger.info("Opening dashboard...")
        dashboard = Dashboard(
            analytics_service=analytics_service,
            suggestion_service=suggestion_service,
            session_service=session_service,
        )
        dashboard.show()

        # Start activity monitoring
        logger.info("Starting activity monitoring...")
        activity_monitor.start_monitoring()

        logger.info("AI Work Assistant started successfully")
        logger.info("Starting Qt event loop...")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start AI Work Assistant: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
