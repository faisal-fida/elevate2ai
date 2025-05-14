#!/usr/bin/env python
"""
Elevate2AI development setup script.
This script helps new developers set up the project quickly.
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path


def print_step(message):
    """Print a formatted step message"""
    print(f"\n\033[1;34m>>> {message}\033[0m")


def run_command(command, cwd=None):
    """Run a shell command and capture output"""
    print(f"Running: {command}")
    result = subprocess.run(
        command, shell=True, cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True


def setup_env():
    """Set up the virtual environment"""
    print_step("Setting up Python virtual environment")

    # Create virtual environment
    if not Path(".venv").exists():
        run_command("python -m venv .venv")

    # Determine activation script path based on OS
    if platform.system() == "Windows":
        activate_path = ".venv\\Scripts\\activate"
    else:
        activate_path = ".venv/bin/activate"

    # Check if activate script exists
    if not Path(activate_path).exists():
        print(f"Error: Activation script not found at {activate_path}")
        return False

    print(f"Virtual environment created. Activate with:\nsource {activate_path}")
    return True


def install_dependencies():
    """Install project dependencies using uv"""
    print_step("Installing dependencies with uv")

    # Install uv if not already installed
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=False)
    except FileNotFoundError:
        print("uv not found, installing...")
        if platform.system() == "Windows":
            run_command("pip install uv")
        else:
            run_command("pip install uv")

    # Install dependencies with uv
    run_command("uv sync")

    return True


def create_env_file():
    """Create a template .env file if it doesn't exist"""
    print_step("Creating .env file template")

    if Path(".env").exists():
        print(".env file already exists, skipping")
        return True

    with open(".env.template", "w") as f:
        f.write("""# Core settings
PROJECT_NAME=Elevate2AI
PROJECT_DESCRIPTION=WhatsApp content generation service
ENVIRONMENT=dev
LOG_LEVEL=INFO

# Database
DATABASE_PATH=./app.db
SQL_ECHO=False

# Security
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
BACKEND_CORS_ORIGINS=http://localhost:3000
SECURE_COOKIES=False
TRUSTED_HOSTS=*

# External APIs - Replace with your API keys
PEXELS_API_KEY=your-pexels-key
UNSPLASH_API_KEY=your-unsplash-key
PIXABAY_API_KEY=your-pixabay-key
SWITCHBOARD_API_KEY=your-switchboard-key
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT=600.0
OPENAI_MAX_RETRIES=2

# WhatsApp - Replace with your WhatsApp credentials
WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_VERIFY_TOKEN=your-verify-token

# Admin - Replace with secure credentials
ADMIN_WHATSAPP_NUMBER=admin-whatsapp-number
ADMIN_PASSWORD=admin-password
""")

    shutil.copy(".env.template", ".env")
    print(
        "Created .env file template. Please update with your actual API keys and credentials."
    )
    return True


def create_media_dirs():
    """Create necessary media directories"""
    print_step("Creating media directories")

    media_path = Path("media")
    media_path.mkdir(exist_ok=True)
    (media_path / "images").mkdir(exist_ok=True)

    print("Media directories created")
    return True


def main():
    """Main setup function"""
    print("\n\033[1;32m=== Elevate2AI Development Setup ===\033[0m\n")

    steps = [
        setup_env,
        install_dependencies,
        create_env_file,
        create_media_dirs,
    ]

    success = True
    for step in steps:
        if not step():
            success = False
            break

    if success:
        print("\n\033[1;32m✅ Setup completed successfully!\033[0m")
        print("\nTo start the application:")
        if platform.system() == "Windows":
            print("1. .venv\\Scripts\\activate")
        else:
            print("1. source .venv/bin/activate")
        print("2. python run.py")
        print("\nThe API will be available at http://127.0.0.1:8000")
        print("API documentation at http://127.0.0.1:8000/docs")
    else:
        print(
            "\n\033[1;31m❌ Setup failed. Please resolve the issues and try again.\033[0m"
        )


if __name__ == "__main__":
    main()
