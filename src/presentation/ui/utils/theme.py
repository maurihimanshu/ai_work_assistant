"""Theme utilities for modern solid-color UI styling."""


def get_stylesheet() -> str:
    # Solid, modern theme with dark side panel and light content
    return """
    QMainWindow {
        background-color: #f3f4f6;
    }
    #sidePanel {
        background-color: #111827;
        border: none;
    }
    QLabel#appTitleLabel {
        color: #111827;
        font-size: 18px;
        font-weight: 600;
    }
    QLabel#subtitleLabel {
        color: #6b7280;
        font-size: 12px;
    }
    QFrame#headerBar {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 8px 12px;
    }

    /* Primary buttons (content area) */
    QPushButton {
        background-color: #2563eb;
        color: #ffffff;
        border: 1px solid #1d4ed8;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #1d4ed8;
    }
    QPushButton:disabled {
        background-color: #93c5fd;
        color: #f3f4f6;
        border-color: #93c5fd;
    }

    /* Side panel nav buttons (override primary) */
    #sidePanel QPushButton {
        color: #e5e7eb;
        background-color: transparent;
        border: none;
        text-align: left;
        padding: 10px 16px;
        font-size: 14px;
        border-radius: 6px;
    }
    #sidePanel QPushButton:hover {
        background-color: #1f2937;
    }
    #sidePanel QPushButton:checked {
        background-color: #2563eb;
        color: #ffffff;
        border-left: 4px solid #1d4ed8;
    }

    QComboBox {
        background-color: #0b1220;
        color: #e5e7eb;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 6px 8px;
    }
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    QStackedWidget {
        background-color: transparent;
    }
    /* Card-like frame styling */
    QFrame#card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
    }
    """


def apply_theme(app) -> None:
    app.setStyleSheet(get_stylesheet())
