#!/usr/bin/env python3
"""
Run script for AI Work Assistant.

This script provides a convenient way to start the AI Work Assistant
from the command line with proper Python path setup.
"""

import os
import sys
from pathlib import Path


def setup_environment():
    """Set up the Python path to include the src directory."""
    # Add src directory to Python path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path.absolute()))

    # Set current working directory to project root
    os.chdir(Path(__file__).parent)


if __name__ == "__main__":
    setup_environment()

    from main import main

    main()
