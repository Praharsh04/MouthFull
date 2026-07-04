"""
main.py
-------
Entry point for the VoiceFlow AI desktop UI.

Run:
    python main.py

This launches the fully-wired frontend (System Tray, Dashboard, Floating AI
Orb, Settings, Speech Models, LLM Providers, Setup Wizard, Notifications,
Log Viewer, Performance Dashboard) with realistic placeholder data. No
backend logic is included — see ui/app.py's module docstring for the
integration contract.
"""
from ui.app import main

if __name__ == "__main__":
    main()
