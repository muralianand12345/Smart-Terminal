# SmartTerminal: AI-Powered Terminal Commands

SmartTerminal (`st`) is a command-line interface that converts natural language instructions into executable terminal commands. It uses AI to understand your intentions and generates the appropriate commands with placeholders for user input.

## Features

- Convert natural language descriptions to terminal commands
- Handle multi-step tasks with sequential commands
- Request user input for command parameters
- Support for different operating systems (macOS, Linux, Windows)
- Interactive mode for continuous command generation
- Command history for context-aware interactions
- Sudo/administrative privilege handling

## Installation

### Quick Install

1. Download the repository:
```
git clone git@github.com:muralianand12345/Smart-Terminal.git
cd Smart-Terminal
```

2. Run the setup script:
```
python setup.py
```

3. Source your shell configuration to update your PATH:
```
source ~/.bashrc  # or ~/.zshrc
```

4. Configure your API key:
```
st --setup
```

### Manual Installation

1. Install the required Python packages:
```
pip install openai pydantic
```

2. Copy the `smart-terminal.py` script to a location in your PATH (e.g., `~/.local/bin/st`) and make it executable:
```
cp smart-terminal.py ~/.local/bin/st
chmod +x ~/.local/bin/st
```

3. Create the configuration directory:
```
mkdir -p ~/.Smart-Terminal
```

4. Configure your API key:
```
st --setup
```

## Usage

### Basic Command

```
st "create a new python virtual environment and install requests package"
```

### Interactive Mode

```
st -i
```

This starts an interactive session where you can continuously enter commands.

### Configuration

```
st --setup
```

This will guide you through setting up your API key and other preferences.

### Clear History

```
st --clear-history
```

## Examples

Here are some examples of what you can do with SmartTerminal:

```
st "create a folder called projects and create a python file inside it"
```

```
st "find all files modified in the last 7 days and copy them to a backup folder"
```

```
st "install docker and start a postgresql container with port 5432 exposed"
```

## Advanced Usage

### Using Context

SmartTerminal maintains a history of your commands to provide context for future requests. This means you can refer to previous actions:

```
st "create a Python file that prints hello world"
st "run that file and save the output to results.txt"
```

### Operating System Support

By default, SmartTerminal generates commands for your configured operating system (default: macOS). You can specify a different OS in your request:

```
st "show all network connections on windows"
```

## Troubleshooting

### API Key Issues

If you encounter API key errors, make sure:
1. You've configured your API key with `st --setup`
2. The API key is correctly entered
3. The base URL is correctly set for your API provider

### Command Errors

If commands fail to execute:
1. Check if you need sudo/administrator privileges
2. Verify that all required tools are installed on your system
3. Ensure you provided the correct input parameters when prompted

## License

This project is licensed under the MIT License - see the LICENSE file for details.