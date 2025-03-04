#!/usr/bin/env python3
"""
Setup script for SmartTerminal configuration.
This will create the necessary configuration directories and files.
"""

import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from contextlib import contextmanager

# ASCII spinner animation characters
SPINNER_CHARS = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]


# Terminal colors
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


# Configuration
HOME_DIR = Path.home()
CONFIG_DIR = HOME_DIR / ".smartterminal"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
INSTALL_DIR = HOME_DIR / ".local" / "bin"

# Default configuration settings
DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.groq.com/openai/v1",
    "model_name": "llama-3.3-70b-versatile",
    "default_os": "linux"
    if "linux" in sys.platform
    else "macos"
    if "darwin" in sys.platform
    else "windows",
    "history_limit": 20,
    "log_level": "INFO",
}

# The smart-terminal script filename
SCRIPT_NAME = "st"


# Loading animation class
class LoadingAnimation:
    def __init__(self, text="Loading..."):
        self.text = text
        self.is_running = False
        self.animation_thread = None

    def _animate(self):
        i = 0
        while self.is_running:
            sys.stdout.write(
                f"\r{Colors.CYAN}{self.text} {SPINNER_CHARS[i % len(SPINNER_CHARS)]}{Colors.ENDC}"
            )
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        # Clear the line after finishing
        sys.stdout.write("\r" + " " * (len(self.text) + 10) + "\r")
        sys.stdout.flush()

    def start(self):
        self.is_running = True
        self.animation_thread = threading.Thread(target=self._animate)
        self.animation_thread.daemon = True
        self.animation_thread.start()

    def stop(self):
        self.is_running = False
        if self.animation_thread:
            self.animation_thread.join()


@contextmanager
def loading_animation(text="Loading..."):
    """Context manager for loading animation"""
    loader = LoadingAnimation(text)
    loader.start()
    try:
        yield
    finally:
        loader.stop()


def print_step(message, status="", color=Colors.HEADER):
    """Print a setup step message with optional status"""
    if status:
        status_color = (
            Colors.GREEN
            if status.lower() in ["done", "complete", "success"]
            else Colors.FAIL
        )
        print(
            f"\n{color}[SETUP]{Colors.ENDC} {message} {status_color}[{status}]{Colors.ENDC}"
        )
    else:
        print(f"\n{color}[SETUP]{Colors.ENDC} {message}")


def print_banner():
    """Print a fancy banner for the setup script"""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════╗
║                                                  ║
║  {Colors.GREEN}SmartTerminal Setup{Colors.CYAN}                             ║
║  {Colors.BLUE}AI-Powered Terminal Commands{Colors.CYAN}                    ║
║                                                  ║
╚══════════════════════════════════════════════════╝{Colors.ENDC}
"""
    print(banner)


def create_config_directory():
    """Create configuration directories and default files"""
    try:
        print_step("Creating configuration directory")

        with loading_animation("Creating directory structure"):
            CONFIG_DIR.mkdir(exist_ok=True)

            # Create config file if it doesn't exist
            if not CONFIG_FILE.exists():
                with open(CONFIG_FILE, "w") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)

            # Create history file if it doesn't exist
            if not HISTORY_FILE.exists():
                with open(HISTORY_FILE, "w") as f:
                    json.dump([], f)

        print_step("Configuration directory created", "DONE", Colors.GREEN)
        return True
    except Exception as e:
        print_step("Failed to create configuration", "ERROR", Colors.FAIL)
        print(f"  {Colors.FAIL}✗ Error: {e}{Colors.ENDC}")
        return False


def update_path():
    """Add installation directory to PATH if not already there"""
    print_step("Updating PATH in shell configuration")

    # Determine shell configuration file
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        shell_config = HOME_DIR / ".zshrc"
        shell_name = "Zsh"
    elif "bash" in shell:
        shell_config = HOME_DIR / ".bashrc"
        shell_name = "Bash"
    else:
        shell_config = HOME_DIR / ".profile"
        shell_name = "Shell"

    # Check if PATH already contains our directory
    path_line = f'export PATH="$PATH:{INSTALL_DIR}"'

    try:
        with loading_animation(f"Updating {shell_name} configuration"):
            if shell_config.exists():
                with open(shell_config, "r") as f:
                    content = f.read()

                if str(INSTALL_DIR) not in content and path_line not in content:
                    with open(shell_config, "a") as f:
                        f.write(f"\n# Added by SmartTerminal setup\n{path_line}\n")
                    print_step(
                        f"PATH updated in {shell_config}", "SUCCESS", Colors.GREEN
                    )
                else:
                    print_step(
                        f"PATH already contains {INSTALL_DIR}", "INFO", Colors.BLUE
                    )
            else:
                with open(shell_config, "w") as f:
                    f.write(f"# Created by SmartTerminal setup\n{path_line}\n")
                print_step(
                    f"Created {shell_config} with PATH update", "SUCCESS", Colors.GREEN
                )
    except Exception as e:
        print_step("Shell configuration update failed", "WARNING", Colors.WARNING)
        print(f"  {Colors.WARNING}⚠ Warning: {e}{Colors.ENDC}")
        print(
            f"  {Colors.WARNING}⚠ Please manually add {INSTALL_DIR} to your PATH{Colors.ENDC}"
        )


def print_setup_complete():
    """Print setup completion message"""
    # Get shell config file
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        shell_config = HOME_DIR / ".zshrc"
    elif "bash" in shell:
        shell_config = HOME_DIR / ".bashrc"
    else:
        shell_config = HOME_DIR / ".profile"

    # Setup complete
    border = "═" * 60
    print(f"\n{Colors.GREEN}{border}")
    print("  SmartTerminal Configuration Complete!  ")
    print(f"{border}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}SmartTerminal configuration is ready{Colors.ENDC}")
    print(f"Configuration directory: {CONFIG_DIR}")

    print(f"\n{Colors.BOLD}Next steps:{Colors.ENDC}")
    print(
        f"  {Colors.GREEN}1.{Colors.ENDC} Make sure you have installed the package with 'poetry install'"
    )
    print(
        f"  {Colors.GREEN}2.{Colors.ENDC} Run '{Colors.BOLD}source {shell_config}{Colors.ENDC}' to update your current shell environment"
    )
    print(
        f"  {Colors.GREEN}3.{Colors.ENDC} Run '{Colors.BOLD}{SCRIPT_NAME} --setup{Colors.ENDC}' to configure your API key and preferences"
    )
    print(
        f"  {Colors.GREEN}4.{Colors.ENDC} Start using SmartTerminal with '{Colors.BOLD}{SCRIPT_NAME} \"your command here\"{Colors.ENDC}'"
    )
    print(
        f"  {Colors.GREEN}5.{Colors.ENDC} Or run in interactive mode with '{Colors.BOLD}{SCRIPT_NAME} -i{Colors.ENDC}'"
    )


def main():
    """Main setup function"""
    try:
        print_banner()

        # Create config directory
        if not create_config_directory():
            return 1

        # Update PATH if needed
        update_path()

        # Setup complete
        print_setup_complete()
        return 0

    except KeyboardInterrupt:
        print(
            f"\n\n{Colors.WARNING}Setup interrupted by user. Configuration may be incomplete.{Colors.ENDC}"
        )
        return 1
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Setup failed: {e}{Colors.ENDC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
