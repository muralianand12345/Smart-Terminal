#For Debugging Dev
poetry remove smart-terminal-cli
pip uninstall smart-terminal-cli

rm -rf ~/.smartterminal
rm -f ~/.local/bin/st
rm -rf ~/.smartterminal/venv

export PATH="$PATH:$HOME/.local/bin"


echo "Uninstall complete"