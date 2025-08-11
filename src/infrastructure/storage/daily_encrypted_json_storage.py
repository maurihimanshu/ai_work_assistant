"""Daily encrypted JSON storage implementation (one file per day)."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from cryptography.fernet import Fernet

from core.entities.activity import Activity
from core.interfaces.activity_repository import ActivityRepository

logger = logging.getLogger(__name__)


class DailyEncryptedJsonStorage(ActivityRepository):
    """Encrypted JSON storage that partitions activities into daily files.

    File naming: YYYY-MM-DD.json.enc stored under base directory.
    A single encryption key is used for all files.
    """

    def __init__(self, base_dir: str, encryption_key_file: Optional[str] = None):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Set up encryption key path
        if encryption_key_file:
            self.key_path = Path(encryption_key_file)
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.key_path = self.base_path / ".encryption_key"

        self._initialize_encryption()

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _initialize_encryption(self) -> None:
        try:
            if self.key_path.exists():
                key = self.key_path.read_bytes()
                if key and len(key) == 44:
                    self.encryption_key = key
                    self.fernet = Fernet(key)
                    return
                else:
                    logger.warning("Invalid key format; generating a new key")
            # Generate and save new key
            self.encryption_key = Fernet.generate_key()
            self.fernet = Fernet(self.encryption_key)
            self.key_path.write_bytes(self.encryption_key)
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}", exc_info=True)
            raise

    def _file_for_date(self, date: datetime) -> Path:
        return self.base_path / f"{date.date().isoformat()}.json.enc"

    def _encrypt(self, plaintext: str) -> bytes:
        return self.fernet.encrypt(plaintext.encode("utf-8"))

    def _decrypt(self, ciphertext: bytes) -> str:
        return self.fernet.decrypt(ciphertext).decode("utf-8")

    def _load_day(self, date: datetime) -> Dict[str, Any]:
        path = self._file_for_date(date)
        if not path.exists():
            return {"activities": {}}
        try:
            encrypted = path.read_bytes()
            if not encrypted:
                return {"activities": {}}
            decrypted = self._decrypt(encrypted)
            return json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to load daily file {path.name}: {e}", exc_info=True)
            return {"activities": {}}

    def _save_day(self, date: datetime, data: Dict[str, Any]) -> None:
        path = self._file_for_date(date)
        try:
            json_text = json.dumps(data, indent=2)
            encrypted = self._encrypt(json_text)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(encrypted)
            # Simple verification
            if tmp.read_bytes() != encrypted:
                tmp.unlink(missing_ok=True)
                raise RuntimeError("Verification failed: data mismatch")
            if path.exists():
                path.unlink()
            tmp.rename(path)
        except Exception as e:
            logger.error(f"Failed to save daily file {path.name}: {e}", exc_info=True)
            raise

    def _activity_to_dict(self, activity: Activity) -> Dict[str, Any]:
        activity_dict = activity.to_dict()
        # Ensure datetime ISO strings
        for key in ["start_time", "end_time"]:
            value = activity_dict.get(key)
            if isinstance(value, datetime):
                activity_dict[key] = value.isoformat()
        return activity_dict

    def _dict_to_activity(self, data: Dict[str, Any]) -> Activity:
        # Convert times
        for key in ["start_time", "end_time"]:
            val = data.get(key)
            if isinstance(val, str) and val:
                data[key] = datetime.fromisoformat(val)
        return Activity(**data)

    # ----------------------------
    # ActivityRepository methods
    # ----------------------------
    def add(self, activity: Activity) -> str:
        try:
            if not activity.id:
                activity.id = str(uuid4())
            day_data = self._load_day(activity.start_time)
            day_data.setdefault("activities", {})
            day_data["activities"][activity.id] = self._activity_to_dict(activity)
            self._save_day(activity.start_time, day_data)
            return activity.id
        except Exception as e:
            logger.error(f"Error adding activity: {e}", exc_info=True)
            raise

    def get(self, activity_id: str) -> Optional[Activity]:
        try:
            # Scan recent 60 days first for efficiency
            today = datetime.now().date()
            for delta in range(0, 60):
                date = datetime.combine(
                    today - timedelta(days=delta), datetime.min.time()
                )
                data = self._load_day(date)
                act = data.get("activities", {}).get(activity_id)
                if act:
                    return self._dict_to_activity(act)
            # Fallback: scan all files under base path
            for path in self.base_path.glob("*.json.enc"):
                try:
                    decrypted = self._decrypt(path.read_bytes())
                    data = json.loads(decrypted)
                    act = data.get("activities", {}).get(activity_id)
                    if act:
                        return self._dict_to_activity(act)
                except Exception:
                    continue
            return None
        except Exception as e:
            logger.error(f"Error retrieving activity {activity_id}: {e}", exc_info=True)
            return None

    def get_by_timerange(
        self, start_time: datetime, end_time: datetime
    ) -> List[Activity]:
        try:
            if end_time < start_time:
                start_time, end_time = end_time, start_time
            activities: List[Activity] = []
            day = start_time.date()
            while day <= end_time.date():
                date_dt = datetime.combine(day, datetime.min.time())
                data = self._load_day(date_dt)
                for activity_data in data.get("activities", {}).values():
                    try:
                        a_start = (
                            datetime.fromisoformat(activity_data["start_time"])
                            if activity_data.get("start_time")
                            else None
                        )
                        a_end = (
                            datetime.fromisoformat(activity_data["end_time"])
                            if activity_data.get("end_time")
                            else datetime.now()
                        )
                        if a_start is None or a_end is None:
                            continue
                        # Overlap check
                        if a_start <= end_time and a_end >= start_time:
                            activities.append(
                                self._dict_to_activity(dict(activity_data))
                            )
                    except Exception as e:
                        logger.error(f"Error processing activity in {day}: {e}")
                        continue
                day = day + timedelta(days=1)
            
            return activities
        except Exception as e:
            logger.error(f"Error retrieving activities by range: {e}", exc_info=True)
            return []

    def update(self, activity: Activity) -> bool:
        try:
            # First try in the file matching start_time
            target_date = activity.start_time
            for attempt in range(2):
                data = self._load_day(target_date)
                if activity.id in data.get("activities", {}):
                    data["activities"][activity.id] = self._activity_to_dict(activity)
                    self._save_day(target_date, data)
                    return True
                # Second attempt: search recent window
                if attempt == 0:
                    today = datetime.now().date()
                    for delta in range(0, 60):
                        date = datetime.combine(
                            today - timedelta(days=delta), datetime.min.time()
                        )
                        data = self._load_day(date)
                        if activity.id in data.get("activities", {}):
                            data["activities"][activity.id] = self._activity_to_dict(
                                activity
                            )
                            self._save_day(date, data)
                            return True
            return False
        except Exception as e:
            logger.error(f"Error updating activity: {e}", exc_info=True)
            return False

    def delete(self, activity_id: str) -> bool:
        try:
            for path in self.base_path.glob("*.json.enc"):
                try:
                    data = self._load_day(datetime.fromisoformat(path.stem))
                except ValueError:
                    # Non-standard file name; try reading
                    try:
                        decrypted = self._decrypt(path.read_bytes())
                        data = json.loads(decrypted)
                    except Exception:
                        continue
                if activity_id in data.get("activities", {}):
                    del data["activities"][activity_id]
                    # If empty, delete file; otherwise save
                    if not data["activities"]:
                        path.unlink(missing_ok=True)
                    else:
                        # Save back using date from filename when possible
                        try:
                            date_dt = datetime.fromisoformat(path.stem)
                        except ValueError:
                            date_dt = datetime.now()
                        self._save_day(date_dt, data)
                    return True
            return False
        except Exception as e:
            logger.error(f"Error deleting activity {activity_id}: {e}", exc_info=True)
            return False

    def cleanup_old_activities(self, before_date: datetime) -> int:
        """Delete entire day files older than before_date's date."""
        try:
            cutoff = before_date.date()
            deleted = 0
            for path in list(self.base_path.glob("*.json.enc")):
                try:
                    file_date = datetime.fromisoformat(path.stem).date()
                except ValueError:
                    # Unknown file, skip
                    continue
                if file_date < cutoff:
                    path.unlink(missing_ok=True)
                    deleted += 1
            return deleted
        except Exception as e:
            logger.error(f"Error cleaning up old activities: {e}", exc_info=True)
            return 0
