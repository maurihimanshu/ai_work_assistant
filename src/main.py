"""
AI Work Assistant - Main Entry Point

This module serves as the main entry point for the AI Work Assistant application.
It initializes all necessary components and starts the application.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from core.events.event_dispatcher import EventDispatcher
from core.services.activity_monitor import ActivityMonitor
from core.services.analytics_service import AnalyticsService
from core.services.session_service import SessionService
from core.services.task_suggestion_service import TaskSuggestionService
from infrastructure.database.repository import ActivityRepository
from infrastructure.ml.activity_categorizer import ActivityCategorizer
from infrastructure.ml.continuous_learner import ContinuousLearner
from presentation.ui.system_tray import SystemTrayApp


def setup_logging():
    """Configure logging for the application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"ai_assistant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def setup_data_directories():
    """Create necessary data directories."""
    directories = [
        "data",
        "data/activities",
        "data/sessions",
        "data/models",
        "config",
        "logs"
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def initialize_services():
    """Initialize all application services.

    Returns:
        tuple: Initialized services and components
    """
    # Initialize event system
    event_dispatcher = EventDispatcher()

    # Initialize data layer
    repository = ActivityRepository(
        data_dir="data/activities",
        event_dispatcher=event_dispatcher
    )

    # Initialize ML components
    categorizer = ActivityCategorizer(
        model_dir="data/models",
        event_dispatcher=event_dispatcher
    )

    learner = ContinuousLearner(
        model_dir="data/models",
        event_dispatcher=event_dispatcher
    )

    # Initialize core services
    activity_monitor = ActivityMonitor(
        repository=repository,
        event_dispatcher=event_dispatcher
    )

    analytics_service = AnalyticsService(
        repository=repository,
        event_dispatcher=event_dispatcher,
        categorizer=categorizer
    )

    session_service = SessionService(
        repository=repository,
        event_dispatcher=event_dispatcher,
        session_dir="data/sessions"
    )

    suggestion_service = TaskSuggestionService(
        repository=repository,
        event_dispatcher=event_dispatcher,
        categorizer=categorizer,
        learner=learner
    )

    return (
        event_dispatcher,
        repository,
        activity_monitor,
        analytics_service,
        session_service,
        suggestion_service
    )

def main():
    """Main entry point for the AI Work Assistant."""
    try:
        # Setup environment
        setup_logging()
        setup_data_directories()

        logger = logging.getLogger(__name__)
        logger.info("Starting AI Work Assistant...")

        # Initialize Qt application
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # Initialize services
        (
            event_dispatcher,
            repository,
            activity_monitor,
            analytics_service,
            session_service,
            suggestion_service
        ) = initialize_services()

        # Create system tray application
        tray_app = SystemTrayApp(
            session_service=session_service,
            analytics_service=analytics_service,
            suggestion_service=suggestion_service,
            event_dispatcher=event_dispatcher
        )
        tray_app.show()

        # Start monitoring
        activity_monitor.start()

        logger.info("AI Work Assistant started successfully")

        # Start Qt event loop
        sys.exit(app.exec())

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start AI Work Assistant: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()