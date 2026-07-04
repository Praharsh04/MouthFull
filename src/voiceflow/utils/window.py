"""Window utility functions for getting active window information."""

import os
from typing import Optional
from PIL import Image

try:
    import win32gui
    import win32process
    import win32ui
    import win32con
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

def get_active_window_info() -> tuple[Optional[str], Optional[Image.Image]]:
    """Get the active window's process name and its icon as a PIL Image.
    
    Returns:
        tuple: (process_name, pil_image)
    """
    if not HAS_WIN32:
        return None, None

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None, None

    # Get process name
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        process_name = process.name()
        exe_path = process.exe()
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return None, None

    # Get Icon
    icon_img = None
    try:
        # Try to get the large icon from the window first
        hicon = win32gui.SendMessage(hwnd, win32con.WM_GETICON, win32con.ICON_BIG, 0)
        
        # Fallback to small icon
        if hicon == 0:
            hicon = win32gui.SendMessage(hwnd, win32con.WM_GETICON, win32con.ICON_SMALL, 0)
            
        # Fallback to class icon
        if hicon == 0:
            hicon = win32gui.GetClassLong(hwnd, win32con.GCL_HICON)

        if hicon == 0 and exe_path and os.path.exists(exe_path):
            # Extract from executable
            import win32api
            large, small = win32gui.ExtractIconEx(exe_path, 0)
            if large:
                hicon = large[0]
            elif small:
                hicon = small[0]

        if hicon != 0:
            # Convert HICON to PIL Image
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, 32, 32)
            hdc = hdc.CreateCompatibleDC()
            hdc.SelectObject(hbmp)
            
            # Draw icon into bitmap
            win32gui.DrawIconEx(hdc.GetSafeHdc(), 0, 0, hicon, 32, 32, 0, None, win32con.DI_NORMAL)
            
            # Convert to PIL
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            icon_img = Image.frombuffer(
                'RGBA',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRA', 0, 1
            )
            
            try:
                win32gui.DestroyIcon(hicon)
            except Exception:
                pass
            
    except Exception as e:
        import traceback
        traceback.print_exc()

    return process_name, icon_img
