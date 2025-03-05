smart_terminal/
│
├── __init__.py                      # Package initialization with version info
│
├── core/                            # Core functionality
│   ├── __init__.py                  # Exports core components
│   ├── base.py                      # Abstract base classes and core interfaces
│   ├── terminal.py                  # Main SmartTerminal implementation
│   ├── commands.py                  # Command generation and execution
│   ├── ai.py                        # AI client and integration
│   ├── context.py                   # Context generation
│   └── shell_integration.py         # Shell integration functionality
│
├── models/                          # Data models and schemas
│   ├── __init__.py                  # Exports model classes
│   ├── command.py                   # Command and tool call models
│   ├── config.py                    # Configuration models
│   ├── context.py                   # Context models
│   └── message.py                   # Chat message models
│
├── utils/                           # Utility modules
│   ├── __init__.py                  # Exports utility functions
│   ├── colors.py                    # Terminal coloring utilities
│   ├── logging.py                   # Logging setup and configuration
│   └── helpers.py                   # General helper functions
│
├── config/                          # Configuration handling
│   ├── __init__.py                  # Exports configuration components
│   ├── manager.py                   # Configuration management
│   └── defaults.py                  # Default configuration values
│
├── cli/                             # Command line interface
│   ├── __init__.py                  # CLI package initialization
│   ├── main.py                      # Main CLI entry point
│   ├── arguments.py                 # Argument parsing
│   └── interactive.py               # Interactive mode functionality
│
├── adapters/                        # Adapters for external services/APIs
│   ├── __init__.py                  # Adapter package initialization
│   └── ai_provider.py               # Adapters for different AI providers
│
└── exceptions/                      # Custom exceptions
    ├── __init__.py                  # Exception package initialization
    └── errors.py                    # Custom error definitions