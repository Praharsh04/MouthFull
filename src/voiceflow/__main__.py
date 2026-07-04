"""Entry point for ``python -m voiceflow``."""

from __future__ import annotations

import argparse
import asyncio
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="voiceflow",
        description="VoiceFlow Local — A completely local AI dictation assistant.",
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = _parse_args()

    if args.version:
        from voiceflow import __version__
        print(f"VoiceFlow Local v{__version__}")
        sys.exit(0)

    from voiceflow.app import VoiceFlowApp
    from voiceflow.core.exceptions import ConfigError

    try:
        app = VoiceFlowApp(config_path=args.config)
        first_time = False
    except ConfigError:
        from voiceflow.core.config import AppConfig
        import tkinter as tk
        from tkinter import messagebox
        from voiceflow.ui.settings import SettingsWindow
        
        # First time setup
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Welcome to VoiceFlow Local", 
            "It looks like this is your first time running VoiceFlow.\n\nPlease configure your preferred Speech-to-Text and LLM providers.", 
            master=root
        )
        
        # Launch settings with default config
        default_config = AppConfig()
        win = SettingsWindow(default_config)
        win.show()
        
        # Try loading again
        try:
            app = VoiceFlowApp(config_path=args.config)
            first_time = True
        except ConfigError:
            messagebox.showerror("Error", "Configuration not saved. Exiting.", master=root)
            sys.exit(1)

    try:
        asyncio.run(app.run_forever())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
