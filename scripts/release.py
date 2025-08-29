#!/usr/bin/env python3
"""
Release script for spotify-imessage package.
Automates the release process with validation and version management.
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from datetime import datetime

def run_command(cmd, check=True, capture_output=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def get_current_version():
    """Get current version from __init__.py."""
    init_file = Path("src/spotify_imessage/__init__.py")
    with open(init_file) as f:
        content = f.read()
        match = re.search(r'__version__ = "([^"]+)"', content)
        if match:
            return match.group(1)
    raise ValueError("Could not find version in __init__.py")

def update_version(new_version):
    """Update version in __init__.py and pyproject.toml."""
    # Update __init__.py
    init_file = Path("src/spotify_imessage/__init__.py")
    content = init_file.read_text()
    content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
    init_file.write_text(content)
    
    # Update pyproject.toml
    pyproject_file = Path("pyproject.toml")
    content = pyproject_file.read_text()
    content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', content)
    pyproject_file.write_text(content)
    
    print(f"Updated version to {new_version}")

def clean_build():
    """Clean previous build artifacts."""
    print("Cleaning previous build artifacts...")
    run_command("rm -rf build/ dist/ src/*.egg-info/", check=False)

def run_tests():
    """Run the test suite."""
    print("Running tests...")
    run_command("python -m pytest tests/ -v")

def build_package():
    """Build the package."""
    print("Building package...")
    run_command("python -m build")

def check_package():
    """Check the built package."""
    print("Checking package...")
    run_command("twine check dist/*")

def upload_to_testpypi():
    """Upload to TestPyPI."""
    print("Uploading to TestPyPI...")
    run_command("twine upload --repository testpypi dist/*")

def upload_to_pypi():
    """Upload to PyPI."""
    print("Uploading to PyPI...")
    run_command("twine upload dist/*")

def create_git_tag(version):
    """Create and push git tag."""
    print(f"Creating git tag v{version}...")
    run_command(f'git add .')
    run_command(f'git commit -m "Release v{version}"')
    run_command(f'git tag v{version}')
    run_command(f'git push origin main --tags')

def main():
    """Main release process."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/release.py <new_version>")
        print("Example: python scripts/release.py 0.1.0")
        sys.exit(1)
    
    new_version = sys.argv[1]
    current_version = get_current_version()
    
    print(f"Current version: {current_version}")
    print(f"New version: {new_version}")
    print(f"Release date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Confirm release
    response = input("Proceed with release? (y/N): ")
    if response.lower() != 'y':
        print("Release cancelled.")
        sys.exit(0)
    
    try:
        # Clean previous builds
        clean_build()
        
        # Update version
        update_version(new_version)
        
        # Run tests
        run_tests()
        
        # Build package
        build_package()
        
        # Check package
        check_package()
        
        # Upload to TestPyPI
        response = input("Upload to TestPyPI? (y/N): ")
        if response.lower() == 'y':
            upload_to_testpypi()
        
        # Upload to PyPI
        response = input("Upload to PyPI? (y/N): ")
        if response.lower() == 'y':
            upload_to_pypi()
        
        # Create git tag
        response = input("Create git tag? (y/N): ")
        if response.lower() == 'y':
            create_git_tag(new_version)
        
        print(f"\n✅ Release v{new_version} completed successfully!")
        print(f"Package available at: https://pypi.org/project/spotify-imessage/{new_version}/")
        
    except Exception as e:
        print(f"\n❌ Release failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
