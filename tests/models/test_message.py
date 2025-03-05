import unittest
from smart_terminal.models.message import (
    Message,
    UserMessage,
    SystemMessage,
    AIMessage,
    ToolCallInfo,
    ChatHistory,
)


class TestMessageModels(unittest.TestCase):
    def test_user_message_creation(self):
        msg = UserMessage.create(content="Hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")

    def test_system_message_creation(self):
        msg = SystemMessage.create(content="Set behavior")
        self.assertEqual(msg.role, "system")
        self.assertEqual(msg.content, "Set behavior")

    def test_ai_message_creation(self):
        msg = AIMessage.create(content="Response")
        self.assertEqual(msg.role, "assistant")
        self.assertEqual(msg.content, "Response")

    def test_tool_call_info(self):
        tool_call = ToolCallInfo(id="1", type="function", function={"name": "test"})
        self.assertEqual(tool_call.id, "1")
        self.assertEqual(tool_call.type, "function")
        self.assertEqual(tool_call.function, {"name": "test"})

    def test_chat_history(self):
        history = ChatHistory()
        user_msg = UserMessage.create(content="Hello")
        history.add_message(user_msg)
        self.assertEqual(len(history.messages), 1)
        self.assertEqual(history.messages[0].content, "Hello")


if __name__ == "__main__":
    unittest.main()
