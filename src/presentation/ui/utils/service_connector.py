"""Service connector for UI-service integration."""

import logging
from datetime import timedelta
from typing import Dict, Any, Optional, List

from .data_access import DataAccessManager

logger = logging.getLogger(__name__)


class ServiceConnector:
    """Handles interaction between UI and core services."""

    def __init__(self, analytics_service, session_service, suggestion_service):
        """Initialize service connector.

        Args:
            analytics_service: Analytics service instance
            session_service: Session service instance
            suggestion_service: Task suggestion service instance
        """
        self.data_manager = DataAccessManager(
            analytics_service=analytics_service,
            session_service=session_service,
            suggestion_service=suggestion_service,
        )

    def get_dashboard_data(self, time_window: timedelta) -> Dict[str, Any]:
        """Get all data needed for dashboard display.

        Args:
            time_window: Time window for data

        Returns:
            Dictionary containing all dashboard data
        """
        try:
            return self.data_manager.get_dashboard_data(time_window)
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}", exc_info=True)
            return {
                "activities": [],
                "productivity": {"metrics": {}, "trends": [], "categories": {}},
                "suggestions": [],
            }

    def start_session(self) -> Optional[str]:
        """Start a new work session.

        Returns:
            Session ID if successful, None otherwise
        """
        try:
            return self.data_manager.session_service.start_session()
        except Exception as e:
            logger.error(f"Error starting session: {e}", exc_info=True)
            return None

    def end_session(self) -> bool:
        """End current work session.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.data_manager.session_service.end_session()
            return True
        except Exception as e:
            logger.error(f"Error ending session: {e}", exc_info=True)
            return False

    # Workspace controls
    def workspace_save(self):
        try:
            snap_id = self.data_manager.workspace_save()
            return True, f"Saved workspace: {snap_id}"
        except Exception as e:
            logger.error(f"Workspace save failed: {e}")
            return False, "Failed to save workspace"

    def workspace_restore(self):
        try:
            count = self.data_manager.workspace_restore()
            return True, f"Restored {count} apps"
        except Exception as e:
            logger.error(f"Workspace restore failed: {e}")
            return False, "Failed to restore workspace"

    def workspace_close(self):
        try:
            count = self.data_manager.workspace_close()
            return True, f"Closed {count} apps"
        except Exception as e:
            logger.error(f"Workspace close failed: {e}")
            return False, "Failed to close workspace"

    # Detailed variants for table rendering
    def workspace_save_details(self):
        try:
            return True, self.data_manager.workspace_save_details()
        except Exception as e:
            logger.error(f"Workspace save details failed: {e}")
            return False, {"snapshot_id": None, "apps": []}

    def workspace_restore_details(self):
        try:
            return True, self.data_manager.workspace_restore_details()
        except Exception as e:
            logger.error(f"Workspace restore details failed: {e}")
            return False, {"snapshot_id": None, "apps": []}

    def workspace_close_details(self):
        try:
            return True, self.data_manager.workspace_close_details()
        except Exception as e:
            logger.error(f"Workspace close details failed: {e}")
            return False, {"apps": []}

    # Named workspaces (presentation layer)
    def named_workspace_list(self) -> List[Dict[str, Any]]:
        try:
            return self.data_manager.list_named_workspaces()
        except Exception as e:
            logger.error(f"List named workspaces failed: {e}")
            return []

    def named_workspace_save_current(
        self, name: str, as_template: bool = False
    ) -> Optional[Dict[str, Any]]:
        try:
            return self.data_manager.save_current_as_workspace(
                name=name, as_template=as_template
            )
        except Exception as e:
            logger.error(f"Save named workspace failed: {e}")
            return None

    def named_workspace_delete(self, workspace_id: str) -> bool:
        try:
            return self.data_manager.delete_workspace(workspace_id)
        except Exception as e:
            logger.error(f"Delete named workspace failed: {e}")
            return False

    def named_workspace_duplicate(
        self, workspace_id: str, new_name: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return self.data_manager.duplicate_workspace(workspace_id, new_name)
        except Exception as e:
            logger.error(f"Duplicate named workspace failed: {e}")
            return None

    def named_workspace_rename(self, workspace_id: str, new_name: str) -> bool:
        try:
            return self.data_manager.rename_workspace(workspace_id, new_name)
        except Exception as e:
            logger.error(f"Rename named workspace failed: {e}")
            return False

    def named_workspace_restore(self, workspace_id: str) -> Dict[str, Any]:
        try:
            return self.data_manager.restore_named_workspace(workspace_id)
        except Exception as e:
            logger.error(f"Restore named workspace failed: {e}")
            return {"apps": [], "restored": 0}

    # Favorites/Templates toggles
    def named_workspace_set_favorite(self, workspace_id: str, favorite: bool) -> bool:
        try:
            return self.data_manager.set_workspace_favorite(workspace_id, favorite)
        except Exception as e:
            logger.error(f"Set favorite failed: {e}")
            return False

    def named_workspace_set_template(self, workspace_id: str, template: bool) -> bool:
        try:
            return self.data_manager.set_workspace_template(workspace_id, template)
        except Exception as e:
            logger.error(f"Set template failed: {e}")
            return False

    # Export/Import
    def export_workspaces(self, file_path: str) -> int:
        try:
            return self.data_manager.export_workspaces(file_path)
        except Exception as e:
            logger.error(f"Export workspaces failed: {e}")
            return 0

    def import_workspaces(self, file_path: str, merge: bool = True) -> int:
        try:
            return self.data_manager.import_workspaces(file_path, merge=merge)
        except Exception as e:
            logger.error(f"Import workspaces failed: {e}")
            return 0
