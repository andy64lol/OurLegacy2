#!/usr/bin/env python3
"""
Virtual Environment Setup Script for Our Legacy GUI
Detects or creates a Python virtual environment and installs customtkinter and dependencies.
"""

import os
import sys
import subprocess
import platform


def get_venv_path():
    """Get the virtual environment path."""
    return os.path.join(os.path.dirname(__file__), 'venv')


def venv_exists():
    """Check if virtual environment already exists."""
    venv_path = get_venv_path()
    return os.path.isdir(venv_path)


def get_python_executable():
    """Get the Python executable path within the virtual environment."""
    venv_path = get_venv_path()
    if platform.system() == 'Windows':
        return os.path.join(venv_path, 'Scripts', 'python.exe')
    else:
        return os.path.join(venv_path, 'bin', 'python')


def get_pip_executable():
    """Get the pip executable path within the virtual environment."""
    venv_path = get_venv_path()
    if platform.system() == 'Windows':
        return os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        return os.path.join(venv_path, 'bin', 'pip')


def create_venv():
    """Create a virtual environment."""
    venv_path = get_venv_path()
    print(f"Creating virtual environment at {venv_path}...")

    try:
        subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
        print("✓ Virtual environment created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return False


def upgrade_pip():
    """Upgrade pip to the latest version."""
    pip_executable = get_pip_executable()
    print("Upgrading pip...")

    try:
        subprocess.run([pip_executable, 'install', '--upgrade', 'pip'],
                       check=True)
        print("✓ Pip upgraded successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to upgrade pip: {e}")
        return False


def install_dependencies():
    """Install required dependencies including customtkinter."""
    pip_executable = get_pip_executable()
    dependencies = [
        'customtkinter>=5.0.0',
        'pillow>=9.0.0',  # For image handling in GUI
        'requests>=2.28.0',  # For HTTP requests
    ]

    print("Installing dependencies...")

    for package in dependencies:
        print(f"  Installing {package}...")
        try:
            subprocess.run([pip_executable, 'install', package], check=True)
            print(f"  ✓ {package} installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to install {package}: {e}")
            return False

    print("✓ All dependencies installed successfully.")
    return True


def setup_venv():
    """Main setup routine."""
    print("=" * 60)
    print("Our Legacy - Virtual Environment Setup")
    print("=" * 60)

    if venv_exists():
        print(f"\n✓ Virtual environment already exists at {get_venv_path()}")
    else:
        print("\n✗ Virtual environment not found. Creating one...\n")
        if not create_venv():
            print("Setup failed. Please try again.")
            return False

    if not upgrade_pip():
        print("Setup failed. Please try again.")
        return False

    print()
    if not install_dependencies():
        print("Setup failed. Please try again.")
        return False

    print("\n" + "=" * 60)
    print("✓ Setup completed successfully!")
    print("=" * 60)

    if platform.system() == 'Windows':
        print("\nTo activate the virtual environment on Windows:")
        print(f"  {get_venv_path()}\\Scripts\\activate.bat")
    else:
        print("\nTo activate the virtual environment on Linux/macOS:")
        print(f"  source {get_venv_path()}/bin/activate")

    print("\nThen run the game with the GUI:")
    print("  python main.py")

    return True


if __name__ == '__main__':
    success = setup_venv()
    sys.exit(0 if success else 1)
