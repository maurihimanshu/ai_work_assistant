
# 🧠 AI Work Assistant

## Overview

The AI Work Assistant is a privacy-focused desktop application that helps users track their work activities, analyze productivity patterns, and receive intelligent task suggestions. Built with Python and PyQt6, it runs entirely offline and ensures complete user data privacy through local encrypted storage.

---

## 🔧 Features

### 1. Activity Monitoring
- Real-time tracking of applications, windows, and user input
- Privacy-focused monitoring with local data storage
- Cross-platform support (Windows, Linux, macOS)

### 2. Intelligent Analytics
- Activity categorization using machine learning
- Productivity pattern analysis
- Time-based activity heatmaps
- Detailed session analytics

### 3. Smart Task Suggestions
- ML-powered task recommendations
- Continuous learning from user behavior
- Context-aware suggestions

### 4. Privacy-First Design
- Fully offline operation
- Local encrypted storage
- No external data sharing
- Complete user control over data

### 5. System Integration
- System tray presence
- Native desktop notifications
- Cross-platform compatibility
- Low resource footprint

---

## 🧠 AI/ML Components

| Component | Implementation |
|-----------|---------------|
| Activity Categorizer | Classifies user activities using scikit-learn |
| Continuous Learner | Adapts to user patterns over time |
| Feature Extractor | Processes activity data for ML models |
| Model Manager | Handles model persistence and updates |
| Prediction Service | Generates activity predictions |

---

## 🛠️ Tech Stack

### Core Framework
- Python 3.x
- PyQt6 for GUI

### Machine Learning
- scikit-learn
- joblib for model persistence

### System Integration
- psutil for cross-platform monitoring
- pywin32 for Windows-specific features
- keyboard and mouse for input monitoring

### Storage
- TinyDB for document storage
- SQLAlchemy for structured data
- Cryptography for data encryption

### Development Tools
- pytest for testing
- black for formatting
- flake8 for linting
- mypy for type checking

---

## 📁 Project Structure

```
ai_work_assistant/
├── src/
│   ├── core/              # Core business logic
│   │   ├── entities/      # Business objects
│   │   ├── events/        # Event system
│   │   ├── interfaces/    # Abstract interfaces
│   │   ├── ml/           # Machine learning
│   │   └── services/      # Core services
│   ├── infrastructure/    # External implementations
│   │   ├── os/           # OS integration
│   │   └── storage/      # Data storage
│   ├── presentation/      # UI components
│   │   └── ui/           # User interface
├── tests/                 # Test suites
│   ├── core/             # Core tests
│   ├── e2e/              # End-to-end tests
│   └── performance/      # Performance tests
└── docs/                 # Documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8 or higher
- pip package manager
- Platform-specific dependencies:
  - Windows: Visual C++ build tools
  - Linux: X11 development libraries
  - macOS: Xcode command line tools

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/maurihimanshu/ai_work_assistant

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Application
```bash
python src/main.py
```

---

## 🔒 Privacy Features

- All data stored locally in encrypted format
- No external API calls or data sharing
- User-controlled data retention
- Secure storage of sensitive information
- Option to export or delete all data

---

## 🧩 Future Enhancements

- Advanced automation rules
- Natural language processing for commands
- Extended IDE integrations
- Custom activity categorization
- Enhanced visualization options
- Workflow optimization suggestions

---
