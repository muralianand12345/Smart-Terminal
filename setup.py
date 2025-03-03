#!/usr/bin/env python3
"""
Setup script for SmartTerminal.
This will install the SmartTerminal CLI tool and create the necessary configuration.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Configuration
HOME_DIR = Path.home()
CONFIG_DIR = HOME_DIR / ".smartterminal"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
INSTALL_DIR = HOME_DIR / ".local" / "bin"

# The smart-terminal script filename
SCRIPT_NAME = "st"
SCRIPT_PATH = INSTALL_DIR / SCRIPT_NAME

# Default configuration
DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.groq.com/openai/v1",
    "model_name": "llama-3.3-70b-versatile",
    "default_os": "macos",
    "history_limit": 20,
}


def print_step(message):
    """Print a setup step message"""
    print(f"\n[SETUP] {message}")


def setup():
    """Setup SmartTerminal"""
    print_step("Setting up SmartTerminal CLI tool")

    # Create config directory
    print_step("Creating configuration directory")
    CONFIG_DIR.mkdir(exist_ok=True)

    # Create config file if it doesn't exist
    if not CONFIG_FILE.exists():
        print_step("Creating default configuration file")
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)

    # Create history file if it doesn't exist
    if not HISTORY_FILE.exists():
        print_step("Creating history file")
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)

    # Create installation directory if it doesn't exist
    print_step(f"Creating installation directory at {INSTALL_DIR}")
    INSTALL_DIR.mkdir(exist_ok=True, parents=True)

    # Copy script to installation directory
    print_step(f"Installing SmartTerminal CLI script as '{SCRIPT_NAME}'")

    # Get the path of the current script
    current_script = Path(__file__).resolve()

    # Check if we should copy smart-terminal.py or this setup script
    smart_terminal_script = current_script.parent / "smart-terminal.py"

    if smart_terminal_script.exists():
        source_script = smart_terminal_script
    else:
        print("Error: smart-terminal.py script not found.")
        return False

    # Copy the script
    try:
        shutil.copy2(source_script, SCRIPT_PATH)
        os.chmod(SCRIPT_PATH, 0o755)  # Make executable
    except Exception as e:
        print(f"Error installing script: {e}")
        return False

    # Add installation directory to PATH if not already there
    print_step("Updating PATH in shell configuration")

    # Determine shell configuration file
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        shell_config = HOME_DIR / ".zshrc"
    elif "bash" in shell:
        shell_config = HOME_DIR / ".bashrc"
    else:
        shell_config = HOME_DIR / ".profile"

    # Check if PATH already contains our directory
    path_line = f'export PATH="$PATH:{INSTALL_DIR}"'

    try:
        if shell_config.exists():
            with open(shell_config, "r") as f:
                content = f.read()

            if str(INSTALL_DIR) not in content and path_line not in content:
                with open(shell_config, "a") as f:
                    f.write(f"\n# Added by SmartTerminal setup\n{path_line}\n")
                    print(f"Added {INSTALL_DIR} to PATH in {shell_config}")
            else:
                print(f"PATH already contains {INSTALL_DIR}")
        else:
            with open(shell_config, "w") as f:
                f.write(f"# Created by SmartTerminal setup\n{path_line}\n")
                print(f"Created {shell_config} with PATH update")
    except Exception as e:
        print(f"Warning: Could not update shell configuration: {e}")
        print(f"Please manually add {INSTALL_DIR} to your PATH")

    # Install requirements if pip is available
    try:
        print_step("Installing Python dependencies")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "openai", "pydantic"], check=True
        )
    except Exception as e:
        print(f"Warning: Could not install dependencies: {e}")
        print(
            "Please manually install the required packages with: pip install openai pydantic"
        )

    print("\n===== SmartTerminal Setup Complete =====")
    print(f"SmartTerminal CLI tool has been installed as '{SCRIPT_NAME}'")
    print(f"Configuration directory: {CONFIG_DIR}")
    print("\nNext steps:")
    print(f"1. Run 'source {shell_config}' to update your current shell environment")
    print(f"2. Run '{SCRIPT_NAME} --setup' to configure your API key and preferences")
    print(f"3. Start using SmartTerminal with '{SCRIPT_NAME} \"your command here\"'")
    print(f"4. Or run in interactive mode with '{SCRIPT_NAME} -i'")

    return True


if __name__ == "__main__":
    setup()
