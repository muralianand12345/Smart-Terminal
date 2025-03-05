import unittest
from datetime import datetime
from smart_terminal.models.context import (
    FileInfo,
    DirectoryInfo,
    FileSystemEntry,
    DirectoryContext,
    SystemInfo,
    GitInfo,
    PatternMatches,
    CommandHistory,
    ContextData,
)


class TestContextModels(unittest.TestCase):
    def test_file_info(self):
        file_info = FileInfo(name="test.txt", size=100)
        self.assertEqual(file_info.name, "test.txt")
        self.assertEqual(file_info.size, 100)

    def test_directory_info(self):
        dir_info = DirectoryInfo(name="test_dir")
        self.assertEqual(dir_info.name, "test_dir")

    def test_directory_context(self):
        dir_context = DirectoryContext(
            current_dir="/home/user",
            parent_dir="/home",
            entries=[FileSystemEntry(name="test.txt", type="file")],
        )
        self.assertEqual(dir_context.current_dir, "/home/user")
        self.assertEqual(len(dir_context.entries), 1)

    def test_system_info(self):
        system_info = SystemInfo(
            platform="Linux",
            platform_release="5.4.0",
            system="Linux-5.4.0",
            hostname="localhost",
        )
        self.assertEqual(system_info.platform, "Linux")

    def test_git_info(self):
        git_info = GitInfo(is_git_repo=True, repo_root="/home/user/repo")
        self.assertTrue(git_info.is_git_repo)

    def test_context_data(self):
        context_data = ContextData(
            directory=DirectoryContext(current_dir="/home/user", parent_dir="/home"),
            system=SystemInfo(
                platform="Linux",
                platform_release="5.4.0",
                system="Linux-5.4.0",
                hostname="localhost",
            ),
            timestamp=datetime.now(),
        )
        self.assertEqual(context_data.directory.current_dir, "/home/user")
        self.assertEqual(context_data.system.platform, "Linux")


if __name__ == "__main__":
    unittest.main()
