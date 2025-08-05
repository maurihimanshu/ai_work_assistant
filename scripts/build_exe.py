"""
Build script for creating Windows executable.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def clean_build_dirs():
    """Clean build and dist directories."""
    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
        print(f"Cleaned {dir_name} directory")


def run_pyinstaller():
    """Run PyInstaller to create the executable."""
    try:
        subprocess.run(["pyinstaller", "ai_work_assistant.spec"], check=True)
        print("Successfully created executable")
    except subprocess.CalledProcessError as e:
        print(f"Error creating executable: {e}")
        sys.exit(1)


def copy_additional_files():
    """Copy additional required files to dist directory."""
    dist_dir = Path("dist/AI Work Assistant")

    # Create necessary directories
    os.makedirs(dist_dir / "logs", exist_ok=True)
    os.makedirs(dist_dir / "data", exist_ok=True)

    # Copy configuration files
    if os.path.exists("config"):
        shutil.copytree("config", dist_dir / "config", dirs_exist_ok=True)

    print("Copied additional files")


def main():
    """Main build function."""
    print("Starting build process...")

    # Clean previous build
    clean_build_dirs()

    # Create executable
    run_pyinstaller()

    # Copy additional files
    copy_additional_files()

    print("\nBuild completed successfully!")
    print("Executable can be found in 'dist/AI Work Assistant' directory")


if __name__ == "__main__":
    main()
