"""Entry point for ``python -m mouthfull``."""

from __future__ import annotations

import argparse
import asyncio
import sys
import threading
from PySide6.QtWidgets import QApplication
from mouthfull.utils.logger import logger

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mouthfull",
        description="MouthFull Local — A completely local AI dictation assistant.",
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

def run_backend(app_instance, loop):
    """Runs the asyncio event loop for the backend."""
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(app_instance.run_forever())
    except Exception as e:
        logger.exception(f"Backend thread crashed: {e}")
    finally:
        loop.close()

_instance_mutex = None

def main() -> None:
    """CLI entry point."""
    import os
    import ctypes
    
    global _instance_mutex
    mutex_name = "Global\\MouthFull_SingleInstance_Mutex"
    _instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183: # ERROR_ALREADY_EXISTS
        logger.warning("Another instance of MouthFull is already running. Exiting.")
        sys.exit(0)

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
        
    args = _parse_args()

    if args.version:
        from mouthfull import __version__
        print(f"MouthFull Local v{__version__}")
        sys.exit(0)

    # 1. Init Config
    from mouthfull.configs.config import load_config, save_config
    config = load_config(args.config)

    # 2. Start Qt Application
    app_qt = QApplication(sys.argv)
    app_qt.setQuitOnLastWindowClosed(False)
    
    from mouthfull.ui.theme import apply_theme
    apply_theme(config.ui.theme, app_qt)

    from PySide6.QtGui import QIcon
    import os
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    app_qt.setWindowIcon(QIcon(logo_path))

    from mouthfull.ui.app import MainWindow, run_setup_wizard_if_needed
    window = MainWindow()
    wizard = run_setup_wizard_if_needed(app_qt, window, config)
    
    if wizard:
        def on_hotkey(combo):
            config.hotkey.combination = combo
        def on_model(model_id):
            config.stt.model = model_id
        def on_permission(perm_id):
            from PySide6.QtWidgets import QMessageBox
            if perm_id == "microphone":
                QMessageBox.information(wizard, "Permission Request", "MouthFull AI requests access to your Microphone.\n\n(On Windows, ensure it is enabled in Privacy Settings).")
            elif perm_id == "accessibility":
                QMessageBox.information(wizard, "Permission Request", "MouthFull AI requests permission to inject text.\n\n(Required for typing text on your behalf).")
            wizard.set_permission_status(perm_id, True)

        wizard.on_hotkey_configured.connect(on_hotkey)
        wizard.on_model_chosen.connect(on_model)
        wizard.on_permission_requested.connect(on_permission)
        def on_wizard_done(*args):
            config.ui.first_run = False
            save_config(config)
        wizard.finished.connect(on_wizard_done)
        wizard.skipped_signal.connect(on_wizard_done)

    # 3. Init Backend
    # We create the asyncio loop manually for the background thread
    backend_loop = asyncio.new_event_loop()
    
    from mouthfull.app import MouthFullApp
    app = MouthFullApp(config=config)

    # 4. Create Bridge
    from mouthfull.ui.bridge import UIBridge
    bridge = UIBridge(window, app._bus, backend_loop, app)
    bridge.subscribe_to_backend()

    # Route logs to UI
    def ui_log_sink(msg):
        entry = {
            "time": msg.record["time"].strftime("%H:%M:%S"),
            "level": msg.record["level"].name,
            "source": msg.record["name"],
            "message": msg.record["message"]
        }
        bridge.log_entry_received.emit(entry)
    
    logger.add(ui_log_sink, level="DEBUG")
    bridge.log_entry_received.connect(window.logs_page.append_log)

    # 4. Start Backend Thread
    backend_thread = threading.Thread(target=run_backend, args=(app, backend_loop), daemon=True)
    backend_thread.start()

    # 5. Start Qt Event Loop
    sys.exit(app_qt.exec())

if __name__ == "__main__":
    main()
