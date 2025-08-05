"""Encrypted JSON storage implementation."""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from cryptography.fernet import Fernet

# Add the parent directory to Python path to make the src package importable
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.entities.activity import Activity
from core.interfaces.activity_repository import ActivityRepository

logger = logging.getLogger(__name__)

class EncryptedJsonStorage(ActivityRepository):
    """Encrypted JSON storage implementation using Fernet encryption."""

    def __init__(self, storage_path: str, encryption_key_file: Optional[str] = None):
        """Initialize the storage.

        Args:
            storage_path: Path to store the database file
            encryption_key_file: Optional path to the encryption key file.
                               If not provided, will use '.encryption_key' in the same directory as storage_path.
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initializing encrypted storage at {storage_path}")

        # Set up encryption key path
        if encryption_key_file:
            self.key_path = Path(encryption_key_file)
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.key_path = self.storage_path.parent / ".encryption_key"

        # Initialize storage
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Initialize storage and encryption."""
        try:
            # Try to load existing key
            if self.key_path.exists():
                logger.debug("Using existing encryption key")
                key = self.key_path.read_bytes()
                if key and len(key) == 44:  # Base64 encoded Fernet key is always 44 bytes
                    self.encryption_key = key
                    self.fernet = Fernet(key)

                    # Try to load existing data
                    if self.storage_path.exists():
                        try:
                            data = self._load_data()
                            activity_count = len(data.get("activities", {}))
                            logger.info(f"Found {activity_count} existing activities")
                            return
                        except Exception as e:
                            logger.warning(f"Could not read storage with existing key: {e}")
                else:
                    logger.warning("Invalid key format")
            else:
                logger.info("No existing key found")

            # If we get here, we need to create a new key and storage
            logger.info("Generating new encryption key")
            self.encryption_key = Fernet.generate_key()
            self.fernet = Fernet(self.encryption_key)

            # Backup existing files if they exist
            if self.key_path.exists():
                backup_key = self.key_path.with_suffix(".key.bak")
                if backup_key.exists():
                    backup_key.unlink()
                self.key_path.rename(backup_key)
                logger.info(f"Backed up existing key to {backup_key}")

            if self.storage_path.exists():
                backup_storage = self.storage_path.with_suffix(".json.bak")
                if backup_storage.exists():
                    backup_storage.unlink()
                self.storage_path.rename(backup_storage)
                logger.info(f"Backed up existing storage to {backup_storage}")

            # Save new key
            self.key_path.write_bytes(self.encryption_key)
            logger.info("Saved new encryption key")

            # Create new empty storage
            self._save_data({"activities": {}})
            logger.info("Created new storage file")

        except Exception as e:
            logger.error(f"Error initializing storage: {e}", exc_info=True)
            raise

    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt JSON data.

        Args:
            data: JSON string to encrypt

        Returns:
            bytes: Encrypted data
        """
        return self.fernet.encrypt(data.encode())

    def _decrypt_data(self, data: bytes) -> str:
        """Decrypt JSON data.

        Args:
            data: Encrypted data to decrypt

        Returns:
            str: Decrypted JSON string
        """
        return self.fernet.decrypt(data).decode()

    def _load_data(self) -> Dict:
        """Load and decrypt data from storage.

        Returns:
            dict: Decrypted data
        """
        try:
            if not self.storage_path.exists():
                logger.info("Storage file not found, creating new")
                return {"activities": {}}

            encrypted_data = self.storage_path.read_bytes()
            if not encrypted_data:
                logger.warning("Storage file is empty")
                return {"activities": {}}

            decrypted_data = self._decrypt_data(encrypted_data)
            data = json.loads(decrypted_data)

            logger.debug(f"Loaded {len(data['activities'])} activities from storage")
            return data

        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            return {"activities": {}}

    def _save_data(self, data: Dict) -> None:
        """Encrypt and save data to storage.

        Args:
            data: Data to encrypt and save
        """
        try:
            json_data = json.dumps(data, indent=2)
            encrypted_data = self._encrypt_data(json_data)

            # Write to temporary file first
            temp_path = self.storage_path.with_suffix(".tmp")
            temp_path.write_bytes(encrypted_data)

            # Verify the temporary file
            try:
                with open(temp_path, "rb") as f:
                    test_data = f.read()
                    if test_data != encrypted_data:
                        raise ValueError("Verification failed: data mismatch")
            except Exception as e:
                logger.error(f"Error verifying temporary file: {e}")
                temp_path.unlink()
                raise

            # Rename temporary file to actual file
            if self.storage_path.exists():
                self.storage_path.unlink()
            temp_path.rename(self.storage_path)

            logger.debug(f"Saved {len(data['activities'])} activities to storage")

        except Exception as e:
            logger.error(f"Error saving data: {e}", exc_info=True)
            raise

    def _activity_to_dict(self, activity: Activity) -> Dict[str, Any]:
        """Convert Activity to dictionary.

        Args:
            activity: Activity to convert

        Returns:
            dict: Activity as dictionary
        """
        activity_dict = activity.to_dict()
        # Ensure datetime objects are serialized
        for key, value in activity_dict.items():
            if isinstance(value, datetime):
                activity_dict[key] = value.isoformat()
        return activity_dict

    def _dict_to_activity(self, data: Dict[str, Any]) -> Activity:
        """Convert dictionary to Activity.

        Args:
            data: Dictionary to convert

        Returns:
            Activity: Converted activity
        """
        # Convert ISO format strings back to datetime
        for key in ["start_time", "end_time"]:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return Activity(**data)

    def add(self, activity: Activity) -> str:
        """Add a new activity.

        Args:
            activity: Activity to store

        Returns:
            str: ID of the stored activity
        """
        try:
            if not activity.id:
                activity.id = str(uuid4())
                logger.debug(f"Generated new activity ID: {activity.id}")

            data = self._load_data()
            activity_dict = self._activity_to_dict(activity)

            logger.debug(
                f"Adding activity: {activity.id} ({activity.app_name} - {activity.window_title})"
                f"\n  Start: {activity.start_time}"
                f"\n  End: {activity.end_time}"
                f"\n  Active: {activity.active_time:.1f}s"
                f"\n  Idle: {activity.idle_time:.1f}s"
            )

            data["activities"][activity.id] = activity_dict
            self._save_data(data)

            # Verify save
            saved_data = self._load_data()
            if activity.id not in saved_data["activities"]:
                logger.error(f"Failed to verify saved activity: {activity.id}")
                raise RuntimeError("Activity save verification failed")

            return activity.id
        except Exception as e:
            logger.error(f"Error adding activity: {e}", exc_info=True)
            raise

    def get(self, activity_id: str) -> Optional[Activity]:
        """Retrieve an activity by ID.

        Args:
            activity_id: ID of the activity to retrieve

        Returns:
            Activity if found, None otherwise
        """
        data = self._load_data()
        activity_data = data["activities"].get(activity_id)
        return self._dict_to_activity(activity_data) if activity_data else None

    def get_by_timerange(
        self, start_time: datetime, end_time: datetime
    ) -> List[Activity]:
        """Retrieve activities within a time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of activities within the range
        """
        try:
            logger.debug(
                f"Retrieving activities between {start_time} and {end_time}"
            )

            data = self._load_data()
            activities = []

            for activity_id, activity_data in data["activities"].items():
                try:
                    activity_start = datetime.fromisoformat(activity_data["start_time"])
                    activity_end = (
                        datetime.fromisoformat(activity_data["end_time"])
                        if activity_data.get("end_time")
                        else datetime.now()
                    )

                    # Include activities that overlap with the time range
                    if (
                        activity_start <= end_time and
                        activity_end >= start_time
                    ):
                        activity = self._dict_to_activity(activity_data)
                        activities.append(activity)
                        logger.debug(
                            f"Found activity: {activity_id}"
                            f"\n  App: {activity.app_name}"
                            f"\n  Window: {activity.window_title}"
                            f"\n  Start: {activity.start_time}"
                            f"\n  End: {activity.end_time}"
                            f"\n  Active: {activity.active_time:.1f}s"
                            f"\n  Idle: {activity.idle_time:.1f}s"
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing activity {activity_id}: {e}",
                        exc_info=True
                    )

            logger.info(f"Found {len(activities)} activities in time range")
            return activities

        except Exception as e:
            logger.error(f"Error retrieving activities: {e}", exc_info=True)
            return []

    def update(self, activity: Activity) -> bool:
        """Update an existing activity.

        Args:
            activity: Activity with updated data

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if not activity.id:
                logger.warning("Attempted to update activity without ID")
                return False

            data = self._load_data()
            if activity.id not in data["activities"]:
                logger.warning(f"Activity {activity.id} not found for update")
                return False

            activity_dict = self._activity_to_dict(activity)
            logger.debug(
                f"Updating activity: {activity.id}"
                f"\n  App: {activity.app_name}"
                f"\n  Window: {activity.window_title}"
                f"\n  Start: {activity.start_time}"
                f"\n  End: {activity.end_time}"
                f"\n  Active: {activity.active_time:.1f}s"
                f"\n  Idle: {activity.idle_time:.1f}s"
            )

            data["activities"][activity.id] = activity_dict
            self._save_data(data)

            # Verify update
            updated_data = self._load_data()
            if activity.id not in updated_data["activities"]:
                logger.error(f"Failed to verify updated activity: {activity.id}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error updating activity: {e}", exc_info=True)
            return False

    def delete(self, activity_id: str) -> bool:
        """Delete an activity.

        Args:
            activity_id: ID of the activity to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        data = self._load_data()
        if activity_id not in data["activities"]:
            return False

        del data["activities"][activity_id]
        self._save_data(data)
        return True

    def cleanup_old_activities(self, before_date: datetime) -> int:
        """Delete activities older than the specified date.

        Args:
            before_date: Delete activities before this date

        Returns:
            int: Number of activities deleted
        """
        data = self._load_data()
        initial_count = len(data["activities"])

        data["activities"] = {
            id: activity_data
            for id, activity_data in data["activities"].items()
            if datetime.fromisoformat(activity_data["start_time"]) > before_date
        }

        self._save_data(data)
        return initial_count - len(data["activities"])
