"""Utility to enumerate installed applications on Windows."""
import os
import winreg
import functools
from typing import List, Dict

@functools.lru_cache(maxsize=1)
def get_installed_applications() -> List[Dict[str, str]]:
    """Enumerate installed applications from the Windows Registry."""
    apps = []
    seen_exes = set()
    
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    
    for hkey, path in registry_paths:
        try:
            with winreg.OpenKey(hkey, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            display_name = None
                            display_icon = None
                            
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            except FileNotFoundError:
                                continue
                                
                            try:
                                display_icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                            except FileNotFoundError:
                                pass
                                
                            if display_name and display_icon:
                                # Clean up icon path
                                icon_path = display_icon.split(",")[0].strip('"')
                                if icon_path.lower().endswith(".exe") and os.path.exists(icon_path):
                                    exe_name = os.path.basename(icon_path)
                                    if exe_name.lower() not in seen_exes and "uninstall" not in exe_name.lower():
                                        seen_exes.add(exe_name.lower())
                                        apps.append({
                                            "name": display_name,
                                            "executable": exe_name,
                                            "icon_path": icon_path
                                        })
                    except Exception:
                        continue
        except Exception:
            continue
            
    # Add some common ones that might not be in uninstall registry with their exe
    common_apps = [
        {"name": "Notepad", "executable": "notepad.exe", "icon_path": r"C:\Windows\System32\notepad.exe"},
        {"name": "Command Prompt", "executable": "cmd.exe", "icon_path": r"C:\Windows\System32\cmd.exe"},
        {"name": "File Explorer", "executable": "explorer.exe", "icon_path": r"C:\Windows\explorer.exe"},
    ]
    
    for app in common_apps:
        if app["executable"].lower() not in seen_exes:
            if os.path.exists(app["icon_path"]):
                apps.append(app)
                seen_exes.add(app["executable"].lower())
                
    # Sort alphabetically by name
    return sorted(apps, key=lambda x: x["name"].lower())
