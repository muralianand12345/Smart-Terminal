"""
Tests for the context module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from smart_terminal.context import ContextGenerator


class TestContextGenerator:
    """Tests for the ContextGenerator class."""

    def test_get_directory_info(self):
        """Test getting information about the current directory."""
        # Mock the directory entries
        mock_entry1 = MagicMock()
        mock_entry1.name = "file1.txt"
        mock_entry1.is_file.return_value = True
        mock_entry1.is_dir.return_value = False
        mock_entry1.stat.return_value.st_size = 1024
        mock_entry1.stat.return_value.st_mtime = 1609459200  # 2021-01-01

        mock_entry2 = MagicMock()
        mock_entry2.name = "dir1"
        mock_entry2.is_file.return_value = False
        mock_entry2.is_dir.return_value = True

        with (
            patch("os.scandir") as mock_scandir,
            patch("os.getcwd") as mock_getcwd,
            patch("pathlib.Path.__str__", return_value="/test"),
        ):
            mock_scandir.return_value = [mock_entry1, mock_entry2]
            mock_getcwd.return_value = "/test/dir"

            info = ContextGenerator.get_directory_info()

            assert "current_dir" in info
            assert info["current_dir"] == "/test/dir"
            assert "parent_dir" in info
            assert info["parent_dir"] == "/test"

            # Check file entry
            assert "entries" in info
            assert len(info["entries"]) == 2
            file_entry = next(e for e in info["entries"] if e["name"] == "file1.txt")
            assert file_entry["type"] == "file"
            assert file_entry["size"] == 1024
            assert file_entry["extension"] == "txt"

            # Check directory entry
            dir_entry = next(e for e in info["entries"] if e["name"] == "dir1")
            assert dir_entry["type"] == "directory"

    def test_get_directory_info_error(self):
        """Test error handling when getting directory info."""
        with patch("os.scandir", side_effect=PermissionError("Permission denied")):
            info = ContextGenerator.get_directory_info()
            assert "error" in info
            assert "Permission denied" in info["error"]

    def test_get_directory_info_max_entries(self):
        """Test that max_entries limit is respected."""
        # Create more than max_entries mock entries
        mock_entries = []
        for i in range(10):
            entry = MagicMock()
            entry.name = f"file{i}.txt"
            entry.is_file.return_value = True
            mock_entries.append(entry)

        with (
            patch("os.scandir") as mock_scandir,
            patch("os.getcwd"),
            patch("pathlib.Path.__str__", return_value="/test"),
        ):
            mock_scandir.return_value = mock_entries

            # Get directory info with max_entries=5
            info = ContextGenerator.get_directory_info(max_entries=5)

            assert "entries" in info
            assert len(info["entries"]) == 5
            assert info["entry_count"] == 5
            assert info["truncated"] is True

    def test_get_system_info(self):
        """Test getting system information."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.release", return_value="5.10.0"),
            patch("platform.platform", return_value="Linux-5.10.0-generic"),
            patch("platform.node", return_value="testhost"),
            patch("os.environ", {"USER": "testuser"}),
        ):
            info = ContextGenerator.get_system_info()

            assert info["platform"] == "Linux"
            assert info["platform_release"] == "5.10.0"
            assert info["system"] == "Linux-5.10.0-generic"
            assert info["hostname"] == "testhost"
            assert info["username"] == "testuser"

    def test_get_system_info_error(self):
        """Test error handling when getting system info."""
        with patch("platform.system", side_effect=Exception("System error")):
            info = ContextGenerator.get_system_info()
            assert "error" in info
            assert "System error" in info["error"]

    def test_get_git_info_in_repo(self):
        """Test getting git info when in a git repository."""
        with patch("subprocess.run") as mock_run:
            # Mock subprocess responses
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="true"),  # is-inside-work-tree
                MagicMock(returncode=0, stdout="/path/to/repo"),  # show-toplevel
                MagicMock(returncode=0, stdout="main"),  # current branch
            ]

            info = ContextGenerator.get_git_info()

            assert info["is_git_repo"] is True
            assert info["repo_root"] == "/path/to/repo"
            assert info["branch"] == "main"

    def test_get_git_info_not_in_repo(self):
        """Test getting git info when not in a git repository."""
        with patch("subprocess.run") as mock_run:
            # Mock git command failure
            mock_run.side_effect = [
                MagicMock(returncode=128, stdout="")  # is-inside-work-tree
            ]

            info = ContextGenerator.get_git_info()

            assert info == {}

    def test_get_git_info_exception(self):
        """Test error handling when getting git info."""
        with patch("subprocess.run", side_effect=Exception("Git error")):
            info = ContextGenerator.get_git_info()
            assert info == {}

    def test_get_pattern_matches(self):
        """Test getting files matching specific patterns."""
        with patch("glob.glob") as mock_glob:
            # Setup mock glob responses
            mock_glob.side_effect = lambda pattern, **kwargs: {
                "*.py": ["file1.py", "file2.py"],
                "*.js": ["script.js"],
                "*.ts": [],
                "Dockerfile": ["Dockerfile"],
            }.get(pattern, [])

            patterns = ["*.py", "*.js", "*.ts", "Dockerfile", "nonexistent.*"]
            matches = ContextGenerator.get_pattern_matches(patterns)

            assert len(matches) == 3  # Only patterns with matches should be included
            assert matches["*.py"] == ["file1.py", "file2.py"]
            assert matches["*.js"] == ["script.js"]
            assert matches["Dockerfile"] == ["Dockerfile"]
            assert "*.ts" not in matches
            assert "nonexistent.*" not in matches

    def test_get_pattern_matches_limit(self):
        """Test that pattern matches are limited to 10 per pattern."""
        with patch("glob.glob") as mock_glob:
            # Return more than 10 matches
            mock_glob.return_value = [f"file{i}.py" for i in range(15)]

            matches = ContextGenerator.get_pattern_matches(["*.py"])

            assert len(matches["*.py"]) == 10

    def test_get_pattern_matches_error(self):
        """Test error handling when getting pattern matches."""
        with patch("glob.glob", side_effect=Exception("Glob error")):
            matches = ContextGenerator.get_pattern_matches(["*.py"])
            assert matches == {}

    def test_generate_context(self):
        """Test generating comprehensive context information."""
        with (
            patch.object(ContextGenerator, "get_directory_info") as mock_dir_info,
            patch.object(ContextGenerator, "get_system_info") as mock_sys_info,
            patch.object(ContextGenerator, "get_git_info") as mock_git_info,
            patch.object(ContextGenerator, "get_pattern_matches") as mock_patterns,
        ):
            # Setup mock responses
            mock_dir_info.return_value = {"current_dir": "/test/dir"}
            mock_sys_info.return_value = {"platform": "Linux"}
            mock_git_info.return_value = {"is_git_repo": True}
            mock_patterns.return_value = {"*.py": ["file.py"]}

            context = ContextGenerator.generate_context()

            assert context["directory"] == {"current_dir": "/test/dir"}
            assert context["system"] == {"platform": "Linux"}
            assert context["git"] == {"is_git_repo": True}
            assert context["project_files"] == {"*.py": ["file.py"]}

    def test_generate_context_no_git(self):
        """Test generating context when not in a git repository."""
        with (
            patch.object(ContextGenerator, "get_directory_info"),
            patch.object(ContextGenerator, "get_system_info"),
            patch.object(ContextGenerator, "get_git_info") as mock_git_info,
            patch.object(ContextGenerator, "get_pattern_matches"),
        ):
            # No git repo
            mock_git_info.return_value = {}

            context = ContextGenerator.generate_context()

            assert "git" not in context

    def test_generate_context_no_project_files(self):
        """Test generating context with no project files found."""
        with (
            patch.object(ContextGenerator, "get_directory_info"),
            patch.object(ContextGenerator, "get_system_info"),
            patch.object(ContextGenerator, "get_git_info"),
            patch.object(ContextGenerator, "get_pattern_matches") as mock_patterns,
        ):
            # No pattern matches
            mock_patterns.return_value = {}

            context = ContextGenerator.generate_context()

            assert "project_files" not in context

    def test_get_context_prompt(self):
        """Test generating a context prompt for the AI model."""
        with patch.object(ContextGenerator, "generate_context") as mock_generate:
            # Setup mock context data
            mock_generate.return_value = {
                "system": {
                    "platform": "Linux",
                    "platform_release": "5.10.0",
                    "username": "testuser",
                },
                "directory": {
                    "current_dir": "/home/testuser/project",
                    "parent_dir": "/home/testuser",
                    "entries": [
                        {"name": "file1.py", "type": "file"},
                        {"name": "file2.py", "type": "file"},
                        {"name": "dir1", "type": "directory"},
                    ],
                },
                "git": {"repo_root": "/home/testuser/project", "branch": "main"},
            }

            prompt = ContextGenerator.get_context_prompt()

            # Check that the prompt contains all expected information
            assert "System: Linux 5.10.0" in prompt
            assert "User: testuser" in prompt
            assert "Current Directory: /home/testuser/project" in prompt
            assert "Parent Directory: /home/testuser" in prompt
            assert "Files in current directory:" in prompt
            assert "file1.py" in prompt
            assert "file2.py" in prompt
            assert "Directories in current directory:" in prompt
            assert "dir1" in prompt
            assert "Git Repository: /home/testuser/project" in prompt
            assert "Git Branch: main" in prompt
