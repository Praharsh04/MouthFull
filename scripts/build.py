import os
import sys
import shutil
import PyInstaller.__main__
from pathlib import Path

def build(config: str):
    """Build the application using PyInstaller."""
    print(f"--- Building {config} configuration ---")
    
    app_name = "MouthFull"
    if config == "Debug":
        app_name += "_Debug"
        
    build_dir = Path("build") / config
    dist_dir = Path("dist") / config
    
    # Base arguments
    args = [
        "src/mouthfull/__main__.py",
        f"--name={app_name}",
        "--onedir",          # Use onedir instead of onefile to avoid huge temp extraction
        "--noconfirm",
        f"--workpath={build_dir}",
        f"--distpath={dist_dir}",
        "--add-data=src/mouthfull/assets;mouthfull/assets",
        "--icon=src/mouthfull/assets/logo.ico",
        "--exclude-module=matplotlib",
        "--exclude-module=IPython",
        "--exclude-module=tkinter",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "--exclude-module=jupyter",
        "--exclude-module=PySide6.QtWebEngine",
        "--exclude-module=PySide6.QtWebEngineCore",
        "--exclude-module=PySide6.QtWebEngineWidgets",
        "--exclude-module=PySide6.QtQml",
        "--exclude-module=PySide6.QtBluetooth",
        "--exclude-module=torch.testing", "--collect-data=faster_whisper",
        # Ignore bulky unnecessary packages if any, PyInstaller handles imports
    ]
    
    if config == "Release":
        args.append("--noconsole")
        args.append("--windowed")
    
    PyInstaller.__main__.run(args)
    print(f"--- {config} build complete ---")
    print(f"Executable located in: {dist_dir / app_name}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build MouthFull Local")
    parser.add_argument("--config", choices=["Debug", "Release", "All"], default="All")
    args = parser.parse_args()
    
    if args.config in ["Debug", "All"]:
        build("Debug")
    if args.config in ["Release", "All"]:
        build("Release")
