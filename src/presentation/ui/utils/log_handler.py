"""Qt logging handler for system log layout."""

import logging
from typing import Optional
from PySide6.QtCore import QObject, Signal


class QtSignalEmitter(QObject):
    """Separate class for Qt signal emission."""

    log_message = Signal(str, int)  # Signal for log messages (message, level)


class QtLogHandler(logging.Handler):
    """Custom logging handler that emits Qt signals."""

    def __init__(self):
        """Initialize the handler."""
        super().__init__()
        # Create separate signal emitter removing - %(name)s
        self.signal_emitter = QtSignalEmitter()
        self.setFormatter(
            logging.Formatter("%(asctime)s- %(levelname)s  - %(message)s")
        )

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record as a Qt signal.

        Args:
            record: The logging record to emit
        """
        try:
            # Format the message
            msg = self.format(record)
            # Emit the signal through the emitter
            self.signal_emitter.log_message.emit(msg, record.levelno)
        except Exception as e:
            # Avoid recursion in error handling
            try:
                print(f"Error in QtLogHandler.emit: {e}")
            except:
                pass
            self.handleError(record)

    def connect_to_widget(self, slot) -> None:
        """Connect the log handler to a widget's slot.

        Args:
            slot: The slot function to connect to
        """
        try:
            self.signal_emitter.log_message.connect(slot)
        except Exception as e:
            print(f"Error connecting log handler: {e}")

    def disconnect_from_widget(self, slot) -> None:
        """Disconnect the log handler from a widget's slot.

        Args:
            slot: The slot function to disconnect from
        """
        try:
            self.signal_emitter.log_message.disconnect(slot)
        except Exception as e:
            print(f"Error disconnecting log handler: {e}")
