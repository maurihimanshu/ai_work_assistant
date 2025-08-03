#!/usr/bin/env python3
"""
Build script for AI Work Assistant.

This script automates various development tasks including:
- Cleaning build artifacts
- Running tests
- Running linters
- Building Python package
- Creating standalone executable
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

def clean():
    """Clean build artifacts and temporary files."""
    print("Cleaning build artifacts...")

    # Directories to clean
    clean_paths = [
        "build",
        "dist",
        "*.egg-info",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "__pycache__",
        ".mypy_cache",
        "logs/*.log"
    ]

    for pattern in clean_paths:
        for path in PROJECT_ROOT.glob("**/" + pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    print("Clean completed!")

def run_tests(coverage=True):
    """Run test suite with optional coverage report.

    Args:
        coverage: Whether to generate coverage report
    """
    print("Running tests...")

    # Base test command
    cmd = ["pytest", "-v"]

    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])

    # Run tests
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print("Tests failed!")
        sys.exit(result.returncode)

    print("Tests completed successfully!")

def run_linters():
    """Run code quality checks."""
    print("Running linters...")

    linter_commands = [
        ["black", "--check", "src", "tests"],
        ["isort", "--check-only", "src", "tests"],
        ["mypy", "src"],
        ["flake8", "src", "tests"]
    ]

    for cmd in linter_commands:
        print(f"\nRunning {cmd[0]}...")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"{cmd[0]} check failed!")
            sys.exit(result.returncode)

    print("\nAll linter checks passed!")

def build_package():
    """Build Python package using setuptools."""
    print("Building Python package...")

    # Clean previous builds
    clean()

    # Build package
    subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=PROJECT_ROOT,
        check=True
    )

    print("Package build completed!")

def build_executable():
    """Create standalone executable using PyInstaller."""
    print("Creating standalone executable...")

    # PyInstaller configuration
    pyinstaller_args = [
        "pyinstaller",
        "--name=ai-work-assistant",
        "--windowed",  # No console window in Windows
        "--icon=resources/icons/app.ico",
        "--add-data=resources/icons/*.ico;resources/icons",
        "--hidden-import=PyQt6",
        "--hidden-import=numpy",
        "--hidden-import=pandas",
        "--hidden-import=scikit-learn",
        "src/main.py"
    ]

    # Run PyInstaller
    result = subprocess.run(pyinstaller_args, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print("Failed to create executable!")
        sys.exit(result.returncode)

    print("Executable created successfully!")

def setup_dev_environment():
    """Set up development environment."""
    print("Setting up development environment...")

    # Install dependencies
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        cwd=PROJECT_ROOT,
        check=True
    )

    # Install pre-commit hooks
    subprocess.run(
        ["pre-commit", "install"],
        cwd=PROJECT_ROOT,
        check=True
    )

    print("Development environment setup completed!")

def main():
    """Main entry point for build script."""
    parser = argparse.ArgumentParser(
        description="Build script for AI Work Assistant"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test suite"
    )

    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Run tests without coverage report"
    )

    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linter checks"
    )

    parser.add_argument(
        "--package",
        action="store_true",
        help="Build Python package"
    )

    parser.add_argument(
        "--exe",
        action="store_true",
        help="Create standalone executable"
    )

    parser.add_argument(
        "--dev-setup",
        action="store_true",
        help="Set up development environment"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all build steps"
    )

    args = parser.parse_args()

    try:
        # Handle all flag
        if args.all:
            clean()
            run_linters()
            run_tests(coverage=True)
            build_package()
            build_executable()
            return

        # Handle individual flags
        if args.clean:
            clean()

        if args.lint:
            run_linters()

        if args.test:
            run_tests(coverage=not args.no_coverage)

        if args.package:
            build_package()

        if args.exe:
            build_executable()

        if args.dev_setup:
            setup_dev_environment()

        # If no flags provided, show help
        if not any(vars(args).values()):
            parser.print_help()

    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()