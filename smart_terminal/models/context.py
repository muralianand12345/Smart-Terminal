"""
Context models for SmartTerminal.

This module defines models for representing context information about
the user's environment, including directory structure, system info,
and other contextual data that helps in command generation.
"""

from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Information about a file in the filesystem."""

    name: str = Field(..., description="Filename")
    size: Optional[int] = Field(default=None, description="File size in bytes")
    modified: Optional[float] = Field(
        default=None, description="Modification timestamp"
    )
    extension: Optional[str] = Field(default=None, description="File extension")
    type: str = Field(default="file", description="Entry type (file)")


class DirectoryInfo(BaseModel):
    """Information about a directory in the filesystem."""

    name: str = Field(..., description="Directory name")
    modified: Optional[float] = Field(
        default=None, description="Modification timestamp"
    )
    type: str = Field(default="directory", description="Entry type (directory)")


class FileSystemEntry(BaseModel):
    """Union type for filesystem entries (files or directories)."""

    name: str = Field(..., description="Entry name")
    type: str = Field(..., description="Entry type (file or directory)")
    size: Optional[int] = Field(default=None, description="File size in bytes")
    modified: Optional[float] = Field(
        default=None, description="Modification timestamp"
    )
    extension: Optional[str] = Field(
        default=None, description="File extension if a file"
    )


class DirectoryContext(BaseModel):
    """Complete information about the current directory."""

    current_dir: str = Field(..., description="Absolute path to current directory")
    parent_dir: str = Field(..., description="Absolute path to parent directory")
    entries: List[FileSystemEntry] = Field(
        default_factory=list, description="Files and directories"
    )
    entry_count: int = Field(default=0, description="Total number of entries")
    truncated: bool = Field(
        default=False, description="Whether the entry list was truncated"
    )

    def get_files(self) -> List[FileSystemEntry]:
        """Get only the file entries."""
        return [entry for entry in self.entries if entry.type == "file"]

    def get_directories(self) -> List[FileSystemEntry]:
        """Get only the directory entries."""
        return [entry for entry in self.entries if entry.type == "directory"]

    def has_file(self, filename: str) -> bool:
        """Check if a specific file exists in the current directory."""
        return any(
            entry.name == filename and entry.type == "file" for entry in self.entries
        )

    def has_directory(self, dirname: str) -> bool:
        """Check if a specific subdirectory exists."""
        return any(
            entry.name == dirname and entry.type == "directory"
            for entry in self.entries
        )


class SystemInfo(BaseModel):
    """Information about the host system."""

    platform: str = Field(..., description="Operating system platform")
    platform_release: str = Field(..., description="Operating system release version")
    system: str = Field(..., description="Full system description")
    hostname: str = Field(..., description="Host name")
    username: Optional[str] = Field(default=None, description="Current username")


class GitInfo(BaseModel):
    """Information about git repository if present."""

    is_git_repo: bool = Field(
        default=False, description="Whether current directory is in a git repo"
    )
    repo_root: Optional[str] = Field(
        default=None, description="Absolute path to repository root"
    )
    branch: Optional[str] = Field(default=None, description="Current branch name")
    has_changes: Optional[bool] = Field(
        default=None, description="Whether there are uncommitted changes"
    )


class PatternMatches(BaseModel):
    """Information about files matching specific patterns."""

    patterns: Dict[str, List[str]] = Field(
        default_factory=dict, description="Map of patterns to matching files"
    )


class CommandHistory(BaseModel):
    """Information about recent commands executed."""

    recent_commands: List[str] = Field(
        default_factory=list, description="Recently executed commands"
    )

    recent_outputs: List[str] = Field(
        default_factory=list, description="Output from recent commands"
    )


class ContextData(BaseModel):
    """
    Complete context information about the current environment.

    This model aggregates all the different types of context information
    that can be used to improve command generation.
    """

    directory: DirectoryContext = Field(
        ..., description="Information about the current directory"
    )

    system: SystemInfo = Field(..., description="Information about the host system")

    git: Optional[GitInfo] = Field(
        default=None, description="Git repository information if available"
    )

    project_files: Optional[PatternMatches] = Field(
        default=None,
        description="Information about files matching common project patterns",
    )

    history: Optional[CommandHistory] = Field(
        default=None, description="Recent command history"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now, description="When this context was generated"
    )

    def format_for_prompt(self) -> str:
        """
        Format context data as a text string for inclusion in prompts.

        Returns:
            str: Formatted context information ready for prompts
        """
        prompt_parts = []

        # Add system info
        prompt_parts.append(
            f"System: {self.system.platform} {self.system.platform_release}"
        )
        prompt_parts.append(f"User: {self.system.username}")

        # Add directory info
        prompt_parts.append(f"Current Directory: {self.directory.current_dir}")
        prompt_parts.append(f"Parent Directory: {self.directory.parent_dir}")

        files = self.directory.get_files()
        if files:
            prompt_parts.append("Files in current directory:")
            for file in files[:15]:  # Limit to 15 files
                prompt_parts.append(f"  - {file.name}")

            if len(files) > 15:
                prompt_parts.append(f"  - ... and {len(files) - 15} more files")

        dirs = self.directory.get_directories()
        if dirs:
            prompt_parts.append("Directories in current directory:")
            for directory in dirs[:10]:  # Limit to 10 directories
                prompt_parts.append(f"  - {directory.name}")

            if len(dirs) > 10:
                prompt_parts.append(f"  - ... and {len(dirs) - 10} more directories")

        # Add git info if available
        if self.git and self.git.is_git_repo:
            prompt_parts.append(f"Git Repository: {self.git.repo_root}")
            prompt_parts.append(f"Git Branch: {self.git.branch}")

            if self.git.has_changes is not None:
                status = (
                    "has uncommitted changes" if self.git.has_changes else "is clean"
                )
                prompt_parts.append(f"Git Status: Repository {status}")

        # Add recent commands if available
        if self.history and self.history.recent_commands:
            prompt_parts.append("Recent commands:")
            for cmd in self.history.recent_commands[-5:]:  # Last 5 commands
                prompt_parts.append(f"  $ {cmd}")

        return "\n".join(prompt_parts)
