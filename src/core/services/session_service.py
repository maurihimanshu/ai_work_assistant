"""Service for managing work sessions and state."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..entities.activity import Activity
from ..events.event_dispatcher import EventDispatcher
from ..events.event_types import SessionEvent
from ..interfaces.activity_repository import ActivityRepository

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing work sessions and their state."""

    def __init__(
        self,
        repository: ActivityRepository,
        event_dispatcher: EventDispatcher,
        session_dir: str = "./sessions",
        inactivity_threshold: timedelta = timedelta(minutes=30),
        auto_save_interval: timedelta = timedelta(minutes=5)
    ):
        """Initialize session service.

        Args:
            repository: Activity repository
            event_dispatcher: Event dispatcher
            session_dir: Directory for session files
            inactivity_threshold: Time before session is considered inactive
            auto_save_interval: How often to auto-save session state
        """
        self.repository = repository
        self.event_dispatcher = event_dispatcher
        self.session_dir = Path(session_dir)
        self.inactivity_threshold = inactivity_threshold
        self.auto_save_interval = auto_save_interval

        self.current_session_id: Optional[str] = None
        self.last_activity_time: Optional[datetime] = None
        self.last_save_time: Optional[datetime] = None
        self.active_apps: Set[str] = set()
        self.session_state: Dict = {
            'id': None,
            'start_time': None,
            'state': {}
        }

        # Create session directory if it doesn't exist
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self) -> str:
        """Start a new session.

        Returns:
            str: Session ID
        """
        current_time = datetime.now()
        # Include microseconds in session ID to ensure uniqueness
        session_id = current_time.strftime("%Y%m%d_%H%M%S_%f")

        self.current_session_id = session_id
        self.last_activity_time = current_time
        self.last_save_time = current_time
        self.active_apps.clear()
        self.session_state = {
            'id': session_id,
            'start_time': current_time.isoformat(),
            'state': {}
        }

        # Save initial state
        self._save_session_state()

        # Dispatch event
        self.event_dispatcher.dispatch(
            SessionEvent(
                session_id=session_id,
                event_type='session_start',
                timestamp=current_time
            )
        )

        return session_id

    def end_session(self) -> None:
        """End the current session."""
        if not self.current_session_id:
            return

        current_time = datetime.now()

        # Update session state
        self.session_state['end_time'] = current_time.isoformat()

        # Save final state
        self._save_session_state()

        # Dispatch event
        self.event_dispatcher.dispatch(
            SessionEvent(
                session_id=self.current_session_id,
                event_type='session_end',
                timestamp=current_time
            )
        )

        # Clear session data
        self.current_session_id = None
        self.last_activity_time = None
        self.last_save_time = None
        self.active_apps.clear()
        self.session_state = {}

    def update_session_state(self, app_name: str, state_data: Dict) -> None:
        """Update session state for an app.

        Args:
            app_name: Name of the app
            state_data: State data to store
        """
        if not self.current_session_id:
            return

        current_time = datetime.now()
        self.last_activity_time = current_time
        self.active_apps.add(app_name)

        # Update state
        if not isinstance(self.session_state, dict):
            self.session_state = {
                'id': self.current_session_id,
                'start_time': current_time.isoformat(),
                'state': {}
            }
        if 'state' not in self.session_state:
            self.session_state['state'] = {}
        self.session_state['state'][app_name] = state_data.copy()  # Make a copy to avoid reference issues

        # Auto-save if needed
        if (
            not self.last_save_time or
            current_time - self.last_save_time >= self.auto_save_interval
        ):
            self._save_session_state()
            self.last_save_time = current_time

    def remove_app_state(self, app_name: str) -> None:
        """Remove app state from session.

        Args:
            app_name: Name of the app
        """
        if not self.current_session_id:
            return

        if app_name in self.active_apps:
            self.active_apps.remove(app_name)

        if 'state' in self.session_state:
            self.session_state['state'].pop(app_name, None)
            self._save_session_state()

    def check_session_timeout(self) -> bool:
        """Check if session has timed out.

        Returns:
            bool: True if session has timed out
        """
        if not self.current_session_id or not self.last_activity_time:
            return False

        current_time = datetime.now()
        return (
            current_time - self.last_activity_time >= self.inactivity_threshold
        )

    def get_recent_sessions(self, limit: int = 5) -> List[Dict]:
        """Get recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            list: Recent sessions
        """
        try:
            all_sessions = []

            # Get all session files
            session_files = list(self.session_dir.glob("session_*.json"))

            # Process each file
            for file in session_files:
                try:
                    # Skip current session file if it's active
                    if (
                        self.current_session_id and
                        file.name == f"session_{self.current_session_id}.json"
                    ):
                        continue

                    # Use context manager to ensure proper file handling
                    with open(file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'id' in data and 'start_time' in data:
                            session = {
                                'id': data['id'],
                                'start_time': data['start_time'],
                                'end_time': data.get('end_time'),
                                'active_apps': list(data.get('state', {}).keys())
                            }
                            all_sessions.append(session)
                except Exception as e:
                    logger.error(f"Error reading session file {file}: {e}")
                    continue

            # Sort sessions by ID (which includes timestamp with microseconds) in reverse order
            all_sessions.sort(key=lambda x: x['id'], reverse=True)

            return all_sessions[:limit]

        except Exception as e:
            logger.error(f"Error getting recent sessions: {e}")
            return []

    def restore_session(self, session_id: str) -> Dict:
        """Restore a previous session.

        Args:
            session_id: Session ID to restore

        Returns:
            dict: Session state

        Raises:
            FileNotFoundError: If session file not found
        """
        session_file = self._get_session_file(session_id)
        if not session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")

        with open(session_file, 'r') as f:
            session_data = json.load(f)

            # Restore session state
            self.current_session_id = session_id
            self.last_activity_time = datetime.now()
            self.last_save_time = datetime.now()
            self.session_state = session_data
            self.active_apps = set(session_data.get('state', {}).keys())

            return session_data

    def cleanup_old_sessions(
        self,
        max_age: timedelta = timedelta(days=30)
    ) -> None:
        """Clean up old session files.

        Args:
            max_age: Maximum age of session files to keep
        """
        try:
            current_time = datetime.now()
            cutoff_time = current_time - max_age

            # Get all session files
            session_files = list(self.session_dir.glob("session_*.json"))

            # Process each file
            for file in session_files:
                # Skip current session file if it's active
                if (
                    self.current_session_id and
                    file.name == f"session_{self.current_session_id}.json"
                ):
                    continue

                try:
                    delete_file = False

                    # Read file data using context manager
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)

                            if not isinstance(data, dict) or 'start_time' not in data:
                                delete_file = True
                            else:
                                start_time = datetime.fromisoformat(data['start_time'])
                                delete_file = start_time < cutoff_time
                    except json.JSONDecodeError:
                        delete_file = True
                    except Exception as e:
                        logger.error(f"Error reading file {file}: {e}")
                        continue

                    # Delete file if needed
                    if delete_file:
                        try:
                            # Force handle cleanup
                            import gc
                            gc.collect()

                            # Use Windows-specific file deletion
                            if hasattr(file, 'unlink'):
                                file.unlink(missing_ok=True)
                            else:
                                import os
                                try:
                                    os.remove(str(file))
                                except FileNotFoundError:
                                    pass

                            logger.info(f"Deleted session file: {file}")
                        except Exception as e:
                            logger.error(f"Error deleting file {file}: {e}")

                except Exception as e:
                    logger.error(f"Error processing file {file}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")

    def get_session_activities(self, session_id: str) -> List[Activity]:
        """Get activities for a session.

        Args:
            session_id: Session ID

        Returns:
            list: Session activities
        """
        try:
            # Load session data
            session_file = self._get_session_file(session_id)
            with open(session_file, 'r') as f:
                session_data = json.load(f)

            # Get activities between start and end time
            start_time = datetime.fromisoformat(session_data['start_time'])
            end_time = (
                datetime.fromisoformat(session_data['end_time'])
                if 'end_time' in session_data
                else datetime.now()
            )

            return self.repository.get_by_timerange(start_time, end_time)

        except Exception as e:
            logger.error(f"Error getting session activities: {e}")
            return []

    def _save_session_state(self) -> None:
        """Save current session state to file."""
        if not self.current_session_id:
            return

        try:
            # Ensure state exists
            if 'state' not in self.session_state:
                self.session_state['state'] = {}

            # Create a copy to avoid modifying the original
            state_to_save = self.session_state.copy()

            # Save to file using context manager
            session_file = self._get_session_file(self.current_session_id)
            with open(session_file, 'w') as f:
                json.dump(state_to_save, f, indent=2)
                f.flush()  # Ensure data is written to disk

        except Exception as e:
            logger.error(f"Error saving session state: {e}")

    def _get_session_file(self, session_id: str) -> Path:
        """Get path to session file.

        Args:
            session_id: Session ID

        Returns:
            Path: Session file path
        """
        return self.session_dir / f"session_{session_id}.json"