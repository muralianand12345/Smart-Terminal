#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import argparse
import subprocess
from pathlib import Path
import readline  # For command history
from openai import AsyncOpenAI, OpenAI
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from typing import List, Iterable, Any, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict

# Configuration
CONFIG_DIR = Path.home() / ".smartterminal"
HISTORY_FILE = CONFIG_DIR / "history.json"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "api_key": "",  # You'll need to set this
    "base_url": "https://api.groq.com/openai/v1",
    "model_name": "llama-3.3-70b-versatile",
    "default_os": "macos",
    "history_limit": 20,
}


# Initialize configuration
def init_config():
    """Initialize configuration directories and files"""
    CONFIG_DIR.mkdir(exist_ok=True)

    # Create config file if it doesn't exist
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"Created default config at {CONFIG_FILE}. Please set your API key.")
        sys.exit(1)

    # Create history file if it doesn't exist
    if not HISTORY_FILE.exists():
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)


# Load configuration
def load_config():
    """Load configuration from file"""
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


# Save configuration
def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# Load chat history
def load_history():
    """Load chat history from file"""
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


# Save chat history
def save_history(history):
    """Save chat history to file"""
    config = load_config()
    # Limit history to configured size
    if len(history) > config["history_limit"]:
        history = history[-config["history_limit"] :]

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


class Message(BaseModel):
    role: str = Field(..., description="The role of the message")
    content: str = Field(..., description="The content of the message")
    model_config = ConfigDict(protected_namespaces=())


class Tools(BaseModel):
    tools: List[str] = Field(..., description="The tools to use")
    model_config = ConfigDict(protected_namespaces=())


class BaseSmartTerminal(BaseModel):
    client: Optional[Any] = None
    aclient: Optional[Any] = None
    model_name: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

    @staticmethod
    def load_tool(name: str, description: str, fields: dict, **kwargs):
        pass

    async def atool_invoke(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        pass

    def tool_invoke(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        pass


class SmartTerminalError(Exception):
    pass


class SmartTerminal(BaseSmartTerminal):
    base_url: str = Field(default="https://api.groq.com/openai/v1")
    model_config = ConfigDict(protected_namespaces=())

    def __init__(self, api_key=None, **data):
        super().__init__(**data)
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)
        self.aclient = AsyncOpenAI(api_key=api_key, base_url=self.base_url)

        # If model_name wasn't provided, use configuration
        if not self.model_name:
            config = load_config()
            self.model_name = config.get("model_name", "llama-3.3-70b-versatile")

    def __str__(self):
        return f"SmartTerminal(model={self.model_name})"

    @staticmethod
    def load_tool(name: str, description: str, fields: dict, **kwargs):
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": fields,
                "strict": True,
            },
        }

    async def atool_invoke(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        try:
            tools_response = await self.aclient.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                temperature=0.0,
                tool_choice="auto",
                **kwargs,
            )

            return tools_response.choices[0].message.tool_calls

        except Exception as e:
            raise SmartTerminalError(f"Error invoking tool: {e}")

    def tool_invoke(
        self,
        tools: Iterable[ChatCompletionToolParam],
        messages: Iterable[ChatCompletionMessageParam],
        **kwargs,
    ) -> Any:
        try:
            tools_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                temperature=0.0,
                tool_choice="auto",
                **kwargs,
            )

            return tools_response.choices[0].message.tool_calls

        except Exception as e:
            raise SmartTerminalError(f"Error invoking tool: {e}")


def create_command_tool():
    return {
        "type": "function",
        "function": {
            "name": "get_command",
            "description": "Get a single terminal command to execute. For tasks requiring multiple commands, this tool should be called multiple times in sequence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "A single terminal command with placeholders for user inputs enclosed in angle brackets (e.g., 'mkdir <folder_name>')",
                    },
                    "user_inputs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of input values that the user needs to provide to execute the command. These correspond to the placeholders in the command string.",
                    },
                    "os": {
                        "type": "string",
                        "enum": ["macos", "linux", "windows"],
                        "description": "The operating system for which this command is intended",
                        "default": "macos",
                    },
                    "requires_admin": {
                        "type": "boolean",
                        "description": "Whether this command requires administrator or root privileges",
                        "default": False,
                    },
                    "description": {
                        "type": "string",
                        "description": "A brief description of what this command does",
                    },
                },
                "required": ["command", "user_inputs"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }


def get_system_prompt():
    """Get the system prompt for the model"""
    config = load_config()
    default_os = config.get("default_os", "macos")

    return f"""You are an expert terminal command assistant. 
    
When users request tasks:
1. Break complex tasks into individual terminal commands
2. For each command, specify:
   - The exact command with placeholders (like <folder_name>) for user inputs
   - List all required user inputs that correspond to placeholders
   - Specify the OS (default: {default_os})
   - Indicate if admin/root privileges are needed
   - Include a brief description of what the command does

Important rules:
- Generate ONE command per tool call
- If a task requires multiple commands, make multiple separate tool calls in sequence
- Use placeholders with angle brackets for any user input values
- Make sure the user_inputs field contains strings matching EXACTLY to the placeholders in the command (without the < >)
- Include "sudo" in user_inputs list if the command requires admin privileges
- Make commands as specific and accurate as possible
- Default to {default_os} commands unless specified otherwise
"""


async def get_commands(user_query: str, chat_history=None):
    """
    Process a user request and return a sequence of commands needed to complete the task.
    """
    config = load_config()
    processor = SmartTerminal(api_key=config.get("api_key"))

    # Create our enhanced tool
    command_tool = create_command_tool()
    tools = [command_tool]

    # System message
    system_message = {"role": "system", "content": get_system_prompt()}

    # Initialize messages with history if provided
    if chat_history and len(chat_history) > 0:
        messages = (
            [system_message] + chat_history + [{"role": "user", "content": user_query}]
        )
    else:
        messages = [system_message, {"role": "user", "content": user_query}]

    try:
        # Get the first command
        response = await processor.atool_invoke(tools=tools, messages=messages)

        if not response:
            return []

        # Store the initial response
        all_commands = [response]

        # Continue the conversation to get any additional commands needed
        updated_messages = messages.copy()

        # Add the assistant's response with the first tool call
        updated_messages.append(
            {"role": "assistant", "content": None, "tool_calls": response}
        )

        # Add feedback that we need any subsequent commands
        updated_messages.append(
            {
                "role": "user",
                "content": "What other commands are needed to complete this task? If no more commands are needed, please respond with 'No more commands needed.'",
            }
        )

        # Keep getting additional commands until the model indicates it's done
        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            next_response = await processor.atool_invoke(
                tools=tools, messages=updated_messages
            )

            # Check if we're done (no more tool calls or empty response)
            if not next_response:
                break

            # Add this command to our list
            all_commands.append(next_response)

            # Update messages for the next iteration
            updated_messages.append(
                {"role": "assistant", "content": None, "tool_calls": next_response}
            )

            updated_messages.append(
                {
                    "role": "user",
                    "content": "Are there any more commands needed? If not, please respond with 'No more commands needed.'",
                }
            )

        return all_commands

    except SmartTerminalError as e:
        print(f"Error occurred: {e}")
        return []


def execute_command(command_str, requires_admin=False):
    """Execute a shell command and return the output"""
    try:
        if requires_admin and sys.platform != "win32":
            command_str = f"sudo {command_str}"

        result = subprocess.run(command_str, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def prompt_for_input(input_name):
    """Prompt the user for input"""
    if input_name.lower() == "sudo":
        return "sudo"  # Just return the sudo command itself

    value = input(f"Enter value for {input_name}: ")
    return value


def replace_placeholders(command, user_inputs):
    """Replace placeholders in the command with actual user inputs"""
    # Create a copy of the original command
    final_command = command

    # Create a dictionary to store user-provided values
    for input_name in user_inputs:
        if input_name.lower() == "sudo":
            # Skip sudo as we handle it separately
            continue

        value = prompt_for_input(input_name)
        placeholder = f"<{input_name}>"

        # Replace the placeholder with the actual value
        final_command = final_command.replace(placeholder, value)

    # Check if any placeholders remain in the command (might happen if user_inputs doesn't match all placeholders)
    while "<" in final_command and ">" in final_command:
        start_idx = final_command.find("<")
        end_idx = final_command.find(">", start_idx)

        if start_idx != -1 and end_idx != -1:
            placeholder = final_command[start_idx : end_idx + 1]
            placeholder_name = placeholder[1:-1]  # Remove < and >

            # Ask for value for this placeholder
            value = prompt_for_input(placeholder_name)

            # Replace the placeholder
            final_command = final_command.replace(placeholder, value)
        else:
            # No more valid placeholders found, break the loop
            break

    return final_command


async def process_input(user_query, chat_history=None):
    """Process user input, get and execute commands"""
    print(f"Processing: {user_query}")

    # Get commands
    command_sets = await get_commands(user_query, chat_history)

    # Update chat history with this interaction
    if chat_history is None:
        chat_history = []

    # Add user query to history
    chat_history.append({"role": "user", "content": user_query})

    # No commands returned
    if not command_sets or len(command_sets) == 0:
        print("Sorry, I couldn't determine the commands needed.")
        return chat_history

    # Extract the commands
    commands = []
    for command_set in command_sets:
        for cmd in command_set:
            try:
                args = json.loads(cmd.function.arguments)
                commands.append(args)
            except:
                print(f"Error parsing command: {cmd}")

    # If no valid commands found
    if len(commands) == 0:
        print("Sorry, I couldn't generate valid commands.")
        return chat_history

    # Execute each command
    for i, cmd in enumerate(commands):
        command = cmd.get("command", "")
        user_inputs = cmd.get("user_inputs", [])
        requires_admin = cmd.get("requires_admin", False) or "sudo" in user_inputs
        description = cmd.get("description", "")

        print(f"\nCommand {i + 1}: {command}")
        print(f"Description: {description}")

        # Check if user wants to execute this command
        confirmation = input("Execute this command? (y/n): ").lower()
        if confirmation != "y":
            print("Command skipped.")
            continue

        # Replace placeholders and execute
        final_command = replace_placeholders(command, user_inputs)
        print(f"Executing: {final_command}")

        success, output = execute_command(final_command, requires_admin)

        if success:
            print("Command executed successfully:")
            print(output)
        else:
            print("Command failed:")
            print(output)

    # Update chat history with executed commands
    assistant_content = "I executed the following commands:\n"
    for cmd in commands:
        assistant_content += f"- {cmd.get('command', '')}\n"

    chat_history.append({"role": "assistant", "content": assistant_content})

    # Trim history if needed
    config = load_config()
    history_limit = config.get("history_limit", 20)
    if len(chat_history) > history_limit:
        chat_history = chat_history[-history_limit:]

    return chat_history


def setup_command():
    """Setup the SmartTerminal configuration"""
    print("SmartTerminal Setup")
    print("==================")

    config = load_config()

    # Get API key
    api_key = input(f"Enter your API key [{config.get('api_key', '')}]: ")
    if api_key:
        config["api_key"] = api_key

    # Get base URL
    base_url = input(
        f"Enter API base URL [{config.get('base_url', 'https://api.groq.com/openai/v1')}]: "
    )
    if base_url:
        config["base_url"] = base_url

    # Get model name
    model_name = input(
        f"Enter model name [{config.get('model_name', 'llama-3.3-70b-versatile')}]: "
    )
    if model_name:
        config["model_name"] = model_name

    # Get default OS
    default_os = input(
        f"Enter default OS (macos, linux, windows) [{config.get('default_os', 'macos')}]: "
    )
    if default_os and default_os in ["macos", "linux", "windows"]:
        config["default_os"] = default_os

    # Get history limit
    history_limit_str = input(
        f"Enter history limit [{config.get('history_limit', 20)}]: "
    )
    if history_limit_str:
        try:
            history_limit = int(history_limit_str)
            config["history_limit"] = history_limit
        except ValueError:
            print("Invalid history limit. Using previous value.")

    # Save configuration
    save_config(config)
    print("Configuration saved.")


def main():
    """Main function to run the SmartTerminal CLI"""
    # Initialize configuration
    init_config()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="SmartTerminal - Natural language to terminal commands"
    )
    parser.add_argument(
        "command", nargs="?", help="Natural language command to execute"
    )
    parser.add_argument(
        "--setup", action="store_true", help="Setup SmartTerminal configuration"
    )
    parser.add_argument(
        "--clear-history", action="store_true", help="Clear command history"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )

    args = parser.parse_args()

    # Setup command
    if args.setup:
        setup_command()
        return

    # Clear history
    if args.clear_history:
        save_history([])
        print("Command history cleared.")
        return

    # Check if API key is set
    config = load_config()
    if not config.get("api_key"):
        print("API key not set. Please run 'st --setup' to configure.")
        return

    # Load chat history
    chat_history = load_history()

    # Interactive mode
    if args.interactive:
        print("SmartTerminal Interactive Mode")
        print("Type 'exit' or 'quit' to exit")
        print("==============================")

        while True:
            try:
                user_input = input("\nst> ")
                if user_input.lower() in ["exit", "quit"]:
                    break

                if not user_input:
                    continue

                # Process the input
                chat_history = asyncio.run(process_input(user_input, chat_history))

                # Save updated history
                save_history(chat_history)

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

        return

    # Process a single command
    if args.command:
        chat_history = asyncio.run(process_input(args.command, chat_history))
        save_history(chat_history)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
