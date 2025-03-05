# Smart Terminal

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-2.0.0-orange)

Smart Terminal (`st`) is a powerful command-line interface that converts natural language instructions into executable terminal commands using AI. Say goodbye to forgetting command syntax or searching through documentation - just describe what you want to do in plain English.

## 🚀 Features

- **Natural Language Processing**: Convert plain English to terminal commands
- **Multi-step Tasks**: Handle complex operations with sequential commands
- **Multiple AI Providers**: Support for OpenAI, Groq, and Anthropic
- **Cross-platform Support**: Works across macOS, Linux, and Windows with dedicated shell adapters
- **Interactive Mode**: Continuous command generation for complex workflows
- **Command History**: Context-aware interactions for better suggestions
- **Admin Privilege Handling**: Proper sudo/admin permission management
- **Customizable**: Configure AI providers and other settings
- **Dry Run Mode**: Preview commands without execution
- **JSON Output**: Format results as JSON for scripting and automation

## ⚡ Quick Installation

```bash
pip install smart-terminal-cli
```

## 📖 Usage

### Basic Command Conversion

```bash
st "create a folder called projects and create a python file inside it"
```

This will generate and execute the appropriate commands to create the folder and file.

### Interactive Mode

```bash
st -i
```

Start an interactive session where you can continuously issue natural language commands.

### Setup and Configuration

```bash
st --setup
```

Configure API keys, default settings, and other options.

### Dry Run Mode

```bash
st --dry-run "create a file with the current date as filename"
```

Preview commands that would be executed without actually running them.

### JSON Output

```bash
st --json "find all python files in the current directory"
```

Output results in JSON format for scripting and automation.

### Other Commands

```bash
# Clear command history
st --clear-history

# Enable debug logging
st --debug

# View version information
st --version

# Set up shell integration
st --shell-setup

# Show configuration information
st --config-info
```

## 📋 Examples

Here are some examples of what you can do with Smart Terminal:

```bash
# File and directory operations
st "find all PDF files in the current directory and move them to a new folder called documents"

# System information
st "show me system information including CPU and memory usage"

# Package management
st "install numpy, pandas, and matplotlib for my python project"

# Git operations
st "initialize a git repository, add all files, and make an initial commit"

# Network operations
st "scan open ports on localhost"
```

## 🔧 Configuration

Smart Terminal stores its configuration in `~/.smartterminal/config.json`. You can modify this file directly or use the setup command:

```bash
st --setup
```

Key configuration options:

- **API Key**: Your AI service API key
- **Base URL**: API endpoint URL
- **Model Name**: AI model to use for command generation
- **Provider**: AI provider to use (openai, groq, anthropic)
- **Default OS**: Target operating system for commands
- **History Limit**: Number of previous commands to retain
- **Shell Integration**: Enable/disable shell integration for environment-changing commands

## Shell Integration

Smart Terminal can modify your shell environment (changing directories, setting environment variables) when you enable shell integration:

```bash
st --shell-setup
```

This adds a function to your shell configuration file that allows Smart Terminal to affect your shell environment.

## 🛠️ Development

### Prerequisites

- Python 3.10 or higher
- Poetry (for dependency management)

### Setting up development environment

```bash
# Clone the repository
git clone https://github.com/muralianand12345/Smart-Terminal.git
cd Smart-Terminal

# Install dependencies using Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Running tests

```bash
pytest
```

### Building from source

```bash
poetry build
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- OpenAI, Groq, and Anthropic for providing the AI capabilities
- All contributors and testers

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

Created by [Murali Anand](https://github.com/muralianand12345)