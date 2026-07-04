import os
import sys
import win32com.client

def main():
    root_dir = r"E:\Apps\Voky"
    logo_ico = os.path.join(root_dir, "src", "mouthfull", "assets", "logo.ico")
    
    # Try multiple Desktop paths
    desktop_paths = [
        os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop"),
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ["PUBLIC"], "Desktop")
    ]
    
    desktop = None
    for d in desktop_paths:
        if os.path.exists(d):
            desktop = d
            break
            
    if not desktop:
        print("Desktop folder not found!")
        sys.exit(1)
        
    shortcut_path = os.path.join(desktop, "MouthFull.lnk")
    
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = os.path.join(root_dir, "dist", "Release", "MouthFull", "MouthFull.exe")
    shortcut.WorkingDirectory = os.path.join(root_dir, "dist", "Release", "MouthFull")
    shortcut.IconLocation = logo_ico
    shortcut.save()
    
    print(f"Shortcut created/updated successfully at {shortcut_path}!")

if __name__ == "__main__":
    main()
