"""Detect the currently focused application window on Windows.

Used by the Prompt Processor to select application-specific prompt templates.
"""
from __future__ import annotations

from typing import Tuple, Optional
from mouthfull.utils.logger import logger


import os
import functools

@functools.lru_cache(maxsize=32)
def _get_display_name(exe_path: str, process_name: str) -> str:
    # Some known cleanups for common apps
    pn_lower = process_name.lower()
    if pn_lower == "code.exe":
        return "VS Code"
    elif pn_lower == "chrome.exe":
        return "Google Chrome"
    elif pn_lower == "msedge.exe":
        return "Microsoft Edge"
    elif pn_lower == "explorer.exe":
        return "File Explorer"

    try:
        import win32api
        
        # Attempt to get FileDescription from version info
        language, codepage = win32api.GetFileVersionInfo(exe_path, '\\VarFileInfo\\Translation')[0]
        string_file_info = u'\\StringFileInfo\\%04X%04X\\%s' % (language, codepage, "FileDescription")
        file_desc = win32api.GetFileVersionInfo(exe_path, string_file_info)
        return file_desc if file_desc else os.path.splitext(process_name)[0].capitalize()
    except Exception:
        return os.path.splitext(process_name)[0].capitalize()

def get_active_app_info() -> Tuple[Optional[str], Optional[str]]:
    """Return the process name and human-readable title of the currently focused window.

    Returns:
        Tuple[str, str]: (process_identifier, display_name)
                         e.g., ("Code.exe", "VS Code")
                         Returns (None, None) if detection fails.
    """
    try:
        import ctypes
        from ctypes import wintypes
        import os

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()

        if not hwnd:
            return None, None

        # Get process ID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        import psutil
        try:
            process = psutil.Process(pid.value)
            process_name = process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = None

        if not process_name:
            return None, None
            
        # Get process executable path for better human-readable name extraction
        try:
            exe_path = process.exe()
            display_name = _get_display_name(exe_path, process_name)
        except Exception:
            display_name = os.path.splitext(process_name)[0].capitalize()
            
        return process_name, display_name

    except Exception as e:
        logger.debug("Failed to detect active app info: {}", e)
        return None, None
