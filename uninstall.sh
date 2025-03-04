#For Debugging Dev
poetry remove smart-terminal
pip uninstall smart-terminal

rm -rf ~/.smartterminal
rm -f ~/.local/bin/st
rm -rf ~/.smartterminal/venv

export PATH="$PATH:$HOME/.local/bin"


echo "Uninstall complete"