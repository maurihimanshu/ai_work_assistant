"""Setup script for development installation."""

from setuptools import find_packages, setup

setup(
    name="ai_work_assistant",
    version="0.1.0",
    packages=find_packages(),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "PyQt6>=6.4.0",
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "psutil>=5.8.0",
        "cryptography>=3.4.0",
        "pytest>=7.0.0",
        "pytest-qt>=4.0.0",
        "pytest-benchmark>=4.0.0",
        "pytest-cov>=3.0.0",
    ],
)
