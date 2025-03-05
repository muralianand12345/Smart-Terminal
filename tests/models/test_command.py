import unittest
from smart_terminal.models.command import Command, CommandResult, ToolCall, OsType


class TestCommandModels(unittest.TestCase):
    def test_command_creation(self):
        command = Command(command="ls -la", os=OsType.LINUX, requires_admin=False)
        self.assertEqual(command.command, "ls -la")
        self.assertEqual(command.os, OsType.LINUX)
        self.assertFalse(command.requires_admin)

    def test_command_result(self):
        result = CommandResult(success=True, output="total 0", command="ls -la")
        self.assertTrue(result.success)
        self.assertEqual(result.output, "total 0")
        self.assertEqual(result.command, "ls -la")

    def test_tool_call(self):
        tool_call = ToolCall(
            id="1",
            type="function",
            function_name="get_command",
            arguments={"command": "ls -la"},
        )
        self.assertEqual(tool_call.id, "1")
        self.assertEqual(tool_call.type, "function")
        self.assertEqual(tool_call.function_name, "get_command")
        self.assertEqual(tool_call.arguments["command"], "ls -la")

        command = tool_call.to_command()
        self.assertIsNotNone(command)
        self.assertEqual(command.command, "ls -la")


if __name__ == "__main__":
    unittest.main()
