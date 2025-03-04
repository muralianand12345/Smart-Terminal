#!/usr/bin/env python3
"""
Setup script for SmartTerminal.
This will install the SmartTerminal CLI tool and create the necessary configuration.
"""

import os
import sys
import json
import shutil
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

# The smart-terminal script filename
SCRIPT_NAME = "st"
SCRIPT_PATH = INSTALL_DIR / SCRIPT_NAME

# Default configuration
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
}


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


def check_requirements():
    """Check if all requirements are met before installation"""
    requirements_met = True

    # Check Python version
    python_version = sys.version_info
    min_version = (3, 7)

    if python_version < min_version:
        print_step("Python version check", "FAILED", Colors.FAIL)
        print(
            f"  {Colors.FAIL}✗ Python {min_version[0]}.{min_version[1]} or higher required. Found {python_version[0]}.{python_version[1]}{Colors.ENDC}"
        )
        requirements_met = False
    else:
        print_step("Python version check", "OK", Colors.GREEN)
        print(
            f"  {Colors.GREEN}✓ Python {python_version[0]}.{python_version[1]}.{python_version[2]}{Colors.ENDC}"
        )

    # Check if pip is available
    try:
        with loading_animation("Checking pip installation"):
            subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        print_step("Pip availability check", "OK", Colors.GREEN)
        print(f"  {Colors.GREEN}✓ Pip is available{Colors.ENDC}")
    except (subprocess.SubprocessError, FileNotFoundError):
        print_step("Pip availability check", "WARNING", Colors.WARNING)
        print(
            f"  {Colors.WARNING}⚠ Pip not found or not working. You'll need to install packages manually.{Colors.ENDC}"
        )

    return requirements_met


def create_virtual_env():
    """Create a virtual environment for SmartTerminal if needed"""
    venv_dir = CONFIG_DIR / "venv"

    # Check if system is using externally managed environment
    try:
        with loading_animation("Checking Python environment"):
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--dry-run", "openai"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        # Check if the error message contains externally-managed-environment
        if "externally-managed-environment" in result.stderr:
            print_step(
                "Detected externally managed Python environment", "INFO", Colors.BLUE
            )
            print(
                f"  {Colors.BLUE}ℹ Will create a dedicated virtual environment{Colors.ENDC}"
            )

            # Create virtual environment
            print_step("Creating virtual environment")
            try:
                with loading_animation("Setting up virtual environment"):
                    subprocess.run(
                        [sys.executable, "-m", "venv", str(venv_dir)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )

                print_step("Virtual environment created", "SUCCESS", Colors.GREEN)
                return str(venv_dir / "bin" / "python")
            except subprocess.SubprocessError as e:
                print_step("Failed to create virtual environment", "ERROR", Colors.FAIL)
                print(f"  {Colors.FAIL}✗ Error: {e}{Colors.ENDC}")
                print(
                    f"  {Colors.WARNING}⚠ Will continue with system Python, but package installation may fail{Colors.ENDC}"
                )
    except Exception:
        # If any error occurs, continue with system Python
        pass

    return sys.executable


def setup():
    """Setup SmartTerminal"""
    print_banner()

    # Check requirements
    check_requirements()

    # Create virtual environment if needed
    python_executable = create_virtual_env()
    use_venv = python_executable != sys.executable

    # Create config directory
    print_step("Creating configuration directory")
    with loading_animation("Creating directory structure"):
        CONFIG_DIR.mkdir(exist_ok=True)
    print_step("Configuration directory created", "DONE", Colors.GREEN)

    # Create config file if it doesn't exist
    if not CONFIG_FILE.exists():
        print_step("Creating default configuration file")
        with loading_animation("Writing configuration"):
            with open(CONFIG_FILE, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        print_step("Configuration file created", "DONE", Colors.GREEN)

    # Create history file if it doesn't exist
    if not HISTORY_FILE.exists():
        print_step("Creating history file")
        with loading_animation("Setting up history"):
            with open(HISTORY_FILE, "w") as f:
                json.dump([], f)
        print_step("History file created", "DONE", Colors.GREEN)

    # Create installation directory if it doesn't exist
    print_step(f"Creating installation directory at {INSTALL_DIR}")
    with loading_animation("Setting up directories"):
        INSTALL_DIR.mkdir(exist_ok=True, parents=True)
    print_step("Installation directory created", "DONE", Colors.GREEN)

    # Copy script to installation directory
    print_step(f"Installing SmartTerminal CLI script as '{SCRIPT_NAME}'")

    # Get the path of the current script
    current_script = Path(__file__).resolve()

    # Check if we should copy smart-terminal.py or this setup script
    smart_terminal_script = current_script.parent / "smart-terminal.py"

    if smart_terminal_script.exists():
        source_script = smart_terminal_script
        with loading_animation("Copying script files"):
            # Copy the script
            try:
                shutil.copy2(source_script, SCRIPT_PATH)
                os.chmod(SCRIPT_PATH, 0o755)  # Make executable

                # If using venv, update the shebang line
                if use_venv:
                    with open(SCRIPT_PATH, "r") as f:
                        content = f.read()

                    content = content.replace(
                        "#!/usr/bin/env python3", f"#!{python_executable}"
                    )

                    with open(SCRIPT_PATH, "w") as f:
                        f.write(content)

                print_step("SmartTerminal script installed", "SUCCESS", Colors.GREEN)
            except Exception as e:
                print_step("Script installation failed", "ERROR", Colors.FAIL)
                print(f"  {Colors.FAIL}✗ Error: {e}{Colors.ENDC}")
                return False
    else:
        print_step("Script installation failed", "ERROR", Colors.FAIL)
        print(
            f"  {Colors.FAIL}✗ Error: smart-terminal.py script not found{Colors.ENDC}"
        )
        return False

    # Add installation directory to PATH if not already there
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

    # Install requirements
    print_step("Installing Python dependencies")

    try:
        pip_executable = (
            f"{python_executable} -m pip" if use_venv else f"{sys.executable} -m pip"
        )

        with loading_animation("Installing required packages"):
            # Install each package separately for better error handling
            for package in ["openai", "pydantic"]:
                subprocess.run(
                    f"{pip_executable} install {package}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=True,
                )

        print_step("Dependencies installed", "SUCCESS", Colors.GREEN)
    except subprocess.SubprocessError as e:
        print_step("Dependency installation failed", "WARNING", Colors.WARNING)
        print(f"  {Colors.WARNING}⚠ Warning: {e}{Colors.ENDC}")
        print(
            f"  {Colors.WARNING}⚠ Please manually install the required packages with: {pip_executable} install openai pydantic{Colors.ENDC}"
        )

        # If using system Python and got an error, suggest virtual environment
        if not use_venv:
            print(
                f"\n  {Colors.CYAN}ℹ Tip: If you're getting 'externally-managed-environment' errors, try:{Colors.ENDC}"
            )
            print(
                f"     {Colors.CYAN}1. python3 -m venv ~/.smartterminal/venv{Colors.ENDC}"
            )
            print(
                f"     {Colors.CYAN}2. source ~/.smartterminal/venv/bin/activate{Colors.ENDC}"
            )
            print(f"     {Colors.CYAN}3. pip install openai pydantic{Colors.ENDC}")

    # Setup complete
    border = "═" * 60
    print(f"\n{Colors.GREEN}{border}")
    print("  SmartTerminal Setup Complete!  ")
    print(f"{border}{Colors.ENDC}")

    print(
        f"\n{Colors.BOLD}SmartTerminal CLI tool has been installed as '{SCRIPT_NAME}'{Colors.ENDC}"
    )
    print(f"Configuration directory: {CONFIG_DIR}")

    if use_venv:
        print(
            f"\n{Colors.CYAN}Using virtual environment at: {CONFIG_DIR / 'venv'}{Colors.ENDC}"
        )

    print(f"\n{Colors.BOLD}Next steps:{Colors.ENDC}")
    print(
        f"  {Colors.GREEN}1.{Colors.ENDC} Run '{Colors.BOLD}source {shell_config}{Colors.ENDC}' to update your current shell environment"
    )
    print(
        f"  {Colors.GREEN}2.{Colors.ENDC} Run '{Colors.BOLD}{SCRIPT_NAME} --setup{Colors.ENDC}' to configure your API key and preferences"
    )
    print(
        f"  {Colors.GREEN}3.{Colors.ENDC} Start using SmartTerminal with '{Colors.BOLD}{SCRIPT_NAME} \"your command here\"{Colors.ENDC}'"
    )
    print(
        f"  {Colors.GREEN}4.{Colors.ENDC} Or run in interactive mode with '{Colors.BOLD}{SCRIPT_NAME} -i{Colors.ENDC}'"
    )

    return True


if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print(
            f"\n\n{Colors.WARNING}Setup interrupted by user. Installation may be incomplete.{Colors.ENDC}"
        )
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Setup failed: {e}{Colors.ENDC}")
        sys.exit(1)
