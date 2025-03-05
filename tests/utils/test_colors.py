from smart_terminal.utils.colors import Colors, ColoredOutput


def test_colors():
    Colors.enable()  # Ensure colors are enabled for the test
    if Colors.is_enabled():
        assert Colors.colorize("text", Colors.RED) == f"{Colors.RED}text{Colors.RESET}"
        assert Colors.error("error") == f"{Colors.BRIGHT_RED}error{Colors.RESET}"
        assert (
            Colors.success("success") == f"{Colors.BRIGHT_GREEN}success{Colors.RESET}"
        )
        assert (
            Colors.warning("warning") == f"{Colors.BRIGHT_YELLOW}warning{Colors.RESET}"
        )
        assert Colors.info("info") == f"{Colors.BRIGHT_BLUE}info{Colors.RESET}"
    else:
        assert Colors.colorize("text", Colors.RED) == "text"
        assert Colors.error("error") == "error"
        assert Colors.success("success") == "success"
        assert Colors.warning("warning") == "warning"
        assert Colors.info("info") == "info"


def test_colored_output(capsys):
    Colors.enable()  # Ensure colors are enabled for the test
    output = ColoredOutput()
    output.error("Error message")
    captured = capsys.readouterr()
    assert "Error message" in captured.out

    output.success("Success message")
    captured = capsys.readouterr()
    assert "Success message" in captured.out

    output.warning("Warning message")
    captured = capsys.readouterr()
    assert "Warning message" in captured.out

    output.info("Info message")
    captured = capsys.readouterr()
    assert "Info message" in captured.out

    output.cmd("Command")
    captured = capsys.readouterr()
    assert "Command" in captured.out

    output.highlight("Highlight")
    captured = capsys.readouterr()
    assert "Highlight" in captured.out

    output.dim("Dim")
    captured = capsys.readouterr()
    assert "Dim" in captured.out
