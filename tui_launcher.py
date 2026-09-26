#!/usr/bin/env python3
"""
tui_launcher.py
Entry point for the CLLM-SenteTruth Replication TUI.

Usage:
    python tui_launcher.py

Press Ctrl+Q or Escape to navigate / quit.
"""
import os
import sys

# Ensure UTF-8 I/O encoding in Windows consoles
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

from tui.app import TUILauncherApp


def main() -> None:
    app = TUILauncherApp()
    app.run()


if __name__ == "__main__":
    main()
