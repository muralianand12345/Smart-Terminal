"""
Context generation module for SmartTerminal.

This module gathers contextual information about the current environment,
such as directory structure, file types, and recent commands.
"""

import os
import glob
import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from smart_terminal.core.base import ContextProvider

try:
    from smart_terminal.models.context import (
        ContextData,
        DirectoryContext,
        SystemInfo,
        GitInfo,
        FileSystemEntry,
        CommandHistory,
        PatternMatches,
    )

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)


class ContextGenerator(ContextProvider):
    """
    Generates context information for SmartTerminal.

    This class gathers information about the current environment to provide
    better context to the AI when generating commands.
    """

    def __init__(self, max_history: int = 5):
        """
        Initialize context generator.

        Args:
            max_history: Maximum number of recent commands to track
        """
        self.max_history = max_history
        self.recent_commands = []
        self.recent_outputs = []

    def get_directory_info(self, max_entries: int = 50) -> Dict[str, Any]:
        """
        Get information about the current directory structure.

        Args:
            max_entries: Maximum number of entries to include

        Returns:
            Dict with directory information
        """
        try:
            current_dir = os.getcwd()

            # Get entries in the current directory
            entries = []
            for entry in os.scandir(current_dir):
                if len(entries) >= max_entries:
                    break

                try:
                    # Basic information
                    info = {
                        "name": entry.name,
                        "type": "file" if entry.is_file() else "directory",
                    }

                    # Add size and modification time for files
                    if entry.is_file():
                        stat = entry.stat()
                        info["size"] = stat.st_size
                        info["modified"] = stat.st_mtime

                        # Try to determine file type
                        if "." in entry.name:
                            info["extension"] = entry.name.split(".")[-1].lower()

                    entries.append(info)
                except Exception as e:
                    logger.debug(f"Error processing entry {entry.name}: {e}")

            # Get parent directory name
            parent_dir = str(Path(current_dir).parent)

            return {
                "current_dir": current_dir,
                "parent_dir": parent_dir,
                "entries": entries,
                "entry_count": len(entries),
                "truncated": len(entries) >= max_entries,
            }
        except Exception as e:
            logger.error(f"Error getting directory info: {e}")
            return {"error": str(e)}

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get basic system information.

        Returns:
            Dict with system information
        """
        try:
            return {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "system": platform.platform(),
                "hostname": platform.node(),
                "username": os.environ.get("USER") or os.environ.get("USERNAME"),
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}

    def get_git_info(self) -> Dict[str, Any]:
        """
        Get git repository information if available.

        Returns:
            Dict with git information or empty dict if not in a git repo
        """
        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return {}

            # Get the repository root
            root_result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Get current branch
            branch_result = subprocess.run(
                ["git", "symbolic-ref", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Check if there are changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            )

            return {
                "is_git_repo": True,
                "repo_root": root_result.stdout.strip(),
                "branch": branch_result.stdout.strip()
                if branch_result.returncode == 0
                else "unknown",
                "has_changes": bool(status_result.stdout.strip()),
            }
        except Exception as e:
            logger.debug(f"Error getting git info (probably not a git repo): {e}")
            return {}

    def get_pattern_matches(self, patterns: List[str]) -> Dict[str, List[str]]:
        """
        Get files matching specific patterns.

        Args:
            patterns: List of glob patterns to match

        Returns:
            Dict mapping patterns to matching files
        """
        result = {}
        for pattern in patterns:
            try:
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    result[pattern] = matches[:10]  # Limit to 10 matches per pattern
            except Exception as e:
                logger.debug(f"Error matching pattern {pattern}: {e}")

        return result

    def update_context(self, command: str, output: str) -> None:
        """
        Update context with a recently executed command.

        Args:
            command: Executed command
            output: Command output
        """
        # Add command to recent commands
        self.recent_commands.append(command)

        # Add output to recent outputs
        self.recent_outputs.append(output)

        # Limit history to max_history
        if len(self.recent_commands) > self.max_history:
            self.recent_commands.pop(0)

        if len(self.recent_outputs) > self.max_history:
            self.recent_outputs.pop(0)

    def generate_context(self) -> Dict[str, Any]:
        """
        Generate comprehensive context information.

        Returns:
            Dict with all context information
        """
        context = {
            "directory": self.get_directory_info(),
            "system": self.get_system_info(),
        }

        # Add git info if available
        git_info = self.get_git_info()
        if git_info:
            context["git"] = git_info

        # Look for common project files
        common_patterns = [
            "*.py",
            "*.js",
            "*.ts",
            "*.html",
            "*.css",
            "*.json",
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            "CMakeLists.txt",
        ]

        pattern_matches = self.get_pattern_matches(common_patterns)
        if pattern_matches:
            context["project_files"] = pattern_matches

        # Add command history if available
        if self.recent_commands:
            context["history"] = {
                "recent_commands": self.recent_commands,
                "recent_outputs": self.recent_outputs,
            }

        # If models are available, convert to model objects
        if MODELS_AVAILABLE:
            return self._to_context_model(context).model_dump()

        return context

    def _to_context_model(self, context: Dict[str, Any]) -> "ContextData":
        """
        Convert context dictionary to ContextData model.

        Args:
            context: Context dictionary

        Returns:
            ContextData model
        """
        if not MODELS_AVAILABLE:
            raise ImportError("Models not available")

        # Create DirectoryContext
        dir_info = context["directory"]

        # Convert entries to FileSystemEntry objects
        entries = []
        for entry in dir_info.get("entries", []):
            entries.append(FileSystemEntry(**entry))

        directory = DirectoryContext(
            current_dir=dir_info["current_dir"],
            parent_dir=dir_info["parent_dir"],
            entries=entries,
            entry_count=dir_info["entry_count"],
            truncated=dir_info["truncated"],
        )

        # Create SystemInfo
        system_info = context["system"]
        system = SystemInfo(**system_info)

        # Create GitInfo if available
        git = None
        if "git" in context:
            git = GitInfo(**context["git"])

        # Create PatternMatches if available
        project_files = None
        if "project_files" in context:
            project_files = PatternMatches(patterns=context["project_files"])

        # Create CommandHistory if available
        history = None
        if "history" in context:
            history = CommandHistory(**context["history"])

        # Create ContextData
        return ContextData(
            directory=directory,
            system=system,
            git=git,
            project_files=project_files,
            history=history,
        )

    def get_context_prompt(self) -> str:
        """
        Generate a context prompt for the AI model.

        Returns:
            Context prompt for the AI model
        """
        context = self.generate_context()

        # Build a context prompt for the AI
        prompt_parts = []

        # Add system info
        system_info = context.get("system", {})
        if system_info:
            prompt_parts.append(
                f"System: {system_info.get('platform')} {system_info.get('platform_release')}"
            )
            prompt_parts.append(f"User: {system_info.get('username')}")

        # Add directory info
        dir_info = context.get("directory", {})
        if dir_info:
            prompt_parts.append(f"Current Directory: {dir_info.get('current_dir')}")
            prompt_parts.append(f"Parent Directory: {dir_info.get('parent_dir')}")

            entries = dir_info.get("entries", [])
            if entries:
                files = [e["name"] for e in entries if e.get("type") == "file"]
                dirs = [e["name"] for e in entries if e.get("type") == "directory"]

                prompt_parts.append("Files in current directory:")
                for file in files[:15]:  # Limit to 15 files
                    prompt_parts.append(f"  - {file}")

                if len(files) > 15:
                    prompt_parts.append(f"  - ... and {len(files) - 15} more files")

                prompt_parts.append("Directories in current directory:")
                for directory in dirs[:10]:  # Limit to 10 directories
                    prompt_parts.append(f"  - {directory}")

                if len(dirs) > 10:
                    prompt_parts.append(
                        f"  - ... and {len(dirs) - 10} more directories"
                    )

        # Add git info
        git_info = context.get("git", {})
        if git_info:
            prompt_parts.append(f"Git Repository: {git_info.get('repo_root')}")
            prompt_parts.append(f"Git Branch: {git_info.get('branch')}")

            if git_info.get("has_changes") is not None:
                status = (
                    "has uncommitted changes"
                    if git_info.get("has_changes")
                    else "is clean"
                )
                prompt_parts.append(f"Git Status: Repository {status}")

        # Add recent commands
        history = context.get("history", {})
        if history:
            recent_commands = history.get("recent_commands", [])
            if recent_commands:
                prompt_parts.append("Recent commands:")
                for cmd in recent_commands:
                    prompt_parts.append(f"  $ {cmd}")

        return "\n".join(prompt_parts)
