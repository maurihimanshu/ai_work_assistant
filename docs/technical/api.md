# AI Work Assistant API Documentation

## Core Services

### ActivityMonitor

```python
class ActivityMonitor:
    """Service for monitoring user activities."""

    def __init__(self, repository: ActivityRepository, event_dispatcher: EventDispatcher)
    def start(self) -> None
    def stop(self) -> None
    def get_current_activity(self) -> Activity
```

### AnalyticsService

```python
class AnalyticsService:
    """Service for analyzing user activities and generating insights."""

    def __init__(self, repository: ActivityRepository, event_dispatcher: EventDispatcher, categorizer: ActivityCategorizer)
    def get_daily_report(self, date: datetime) -> Dict[str, Any]
    def get_productivity_score(self, timeframe: timedelta) -> float
    def get_activity_patterns(self, days: int) -> List[Dict[str, Any]]
```

### SessionService

```python
class SessionService:
    """Service for managing user sessions."""

    def __init__(self, repository: ActivityRepository, event_dispatcher: EventDispatcher, session_dir: str)
    def start_session(self) -> str
    def end_session(self, session_id: str) -> None
    def get_session_summary(self, session_id: str) -> Dict[str, Any]
```

### TaskSuggestionService

```python
class TaskSuggestionService:
    """Service for generating task suggestions."""

    def __init__(self, repository: ActivityRepository, event_dispatcher: EventDispatcher, 
                 categorizer: ActivityCategorizer, learner: ContinuousLearner)
    def get_suggestions(self) -> List[str]
    def feedback(self, suggestion_id: str, accepted: bool) -> None
```

## Machine Learning Components

### ActivityCategorizer

```python
class ActivityCategorizer:
    """Categorizes user activities using ML models."""

    def __init__(self, model_dir: str, event_dispatcher: EventDispatcher)
    def categorize(self, activity: Activity) -> str
    def train(self, activities: List[Activity]) -> None
    def evaluate(self, test_data: List[Activity]) -> Dict[str, float]
```

### ContinuousLearner

```python
class ContinuousLearner:
    """Continuously learns from user behavior."""

    def __init__(self, model_dir: str, event_dispatcher: EventDispatcher)
    def learn(self, activity: Activity) -> None
    def predict(self, context: Dict[str, Any]) -> List[str]
```

## Event System

### EventDispatcher

```python
class EventDispatcher:
    """Central event dispatching system."""

    def subscribe(self, event_type: str, handler: Callable) -> None
    def unsubscribe(self, event_type: str, handler: Callable) -> None
    def dispatch(self, event: Event) -> None
```

### Event Types

```python
class ActivityStartEvent(Event):
    """Triggered when a new activity starts."""
    activity: Activity
    timestamp: datetime

class ActivityEndEvent(Event):
    """Triggered when an activity ends."""
    activity: Activity
    duration: timedelta

class ProductivityAlertEvent(Event):
    """Triggered for productivity-related notifications."""
    alert_type: str
    message: str
    severity: int
```

## Data Models

### Activity

```python
class Activity:
    """Represents a user activity."""

    id: str
    type: str
    title: str
    application: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: timedelta
    category: Optional[str]
    metadata: Dict[str, Any]
```

## Storage

### ActivityRepository

```python
class ActivityRepository:
    """Interface for activity data storage."""

    def save(self, activity: Activity) -> None
    def get(self, activity_id: str) -> Activity
    def get_by_timeframe(self, start: datetime, end: datetime) -> List[Activity]
    def get_by_category(self, category: str) -> List[Activity]
```

## UI Components

### SystemTrayApp

```python
class SystemTrayApp(QSystemTrayIcon):
    """System tray interface."""

    def __init__(self, session_service: SessionService, analytics_service: AnalyticsService,
                 suggestion_service: TaskSuggestionService, event_dispatcher: EventDispatcher)
    def show_notification(self, title: str, message: str) -> None
    def show_menu(self) -> None
```

### Dashboard

```python
class Dashboard(QMainWindow):
    """Analytics dashboard window."""

    def __init__(self, analytics_service: AnalyticsService, 
                 suggestion_service: TaskSuggestionService,
                 session_service: SessionService)
    def update_data(self) -> None
    def show_productivity_chart(self) -> None
    def show_activity_heatmap(self) -> None
```

## Configuration

### Settings

```python
class Settings:
    """Application settings management."""

    def load(self) -> Dict[str, Any]
    def save(self, settings: Dict[str, Any]) -> None
    def get(self, key: str, default: Any = None) -> Any
    def set(self, key: str, value: Any) -> None
```

## Error Handling

```python
class AIAssistantError(Exception):
    """Base exception for AI Work Assistant."""
    pass

class ActivityError(AIAssistantError):
    """Activity-related errors."""
    pass

class StorageError(AIAssistantError):
    """Storage-related errors."""
    pass

class MLError(AIAssistantError):
    """Machine learning-related errors."""
    pass
```