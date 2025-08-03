"""Encrypted JSON storage implementation."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from cryptography.fernet import Fernet

from ...core.entities.activity import Activity
from ...core.interfaces.activity_repository import ActivityRepository


class EncryptedJsonStorage(ActivityRepository):
    """Encrypted JSON storage implementation using Fernet encryption."""

    def __init__(self, storage_path: str):
        """Initialize the storage.

        Args:
            storage_path: Path to store the database file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate or load encryption key
        self.key_path = self.storage_path.parent / ".encryption_key"
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)

        # Initialize empty database if it doesn't exist
        if not self.storage_path.exists():
            self._save_data({"activities": {}})

    def _get_or_create_key(self) -> bytes:
        """Get existing or create new encryption key.

        Returns:
            bytes: Encryption key
        """
        if self.key_path.exists():
            return self.key_path.read_bytes()

        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        return key

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
        if not self.storage_path.exists():
            return {"activities": {}}

        encrypted_data = self.storage_path.read_bytes()
        decrypted_data = self._decrypt_data(encrypted_data)
        return json.loads(decrypted_data)

    def _save_data(self, data: Dict) -> None:
        """Encrypt and save data to storage.

        Args:
            data: Data to encrypt and save
        """
        json_data = json.dumps(data)
        encrypted_data = self._encrypt_data(json_data)
        self.storage_path.write_bytes(encrypted_data)

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
        if not activity.id:
            activity.id = str(uuid4())

        data = self._load_data()
        data["activities"][activity.id] = self._activity_to_dict(activity)
        self._save_data(data)
        return activity.id

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
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Activity]:
        """Retrieve activities within a time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of activities within the range
        """
        data = self._load_data()
        activities = []

        for activity_data in data["activities"].values():
            activity_start = datetime.fromisoformat(activity_data["start_time"])
            if start_time <= activity_start <= end_time:
                activities.append(self._dict_to_activity(activity_data))

        return activities

    def update(self, activity: Activity) -> bool:
        """Update an existing activity.

        Args:
            activity: Activity with updated data

        Returns:
            bool: True if update successful, False otherwise
        """
        if not activity.id:
            return False

        data = self._load_data()
        if activity.id not in data["activities"]:
            return False

        data["activities"][activity.id] = self._activity_to_dict(activity)
        self._save_data(data)
        return True

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