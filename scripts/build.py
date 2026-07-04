import os
import sys
import shutil
import PyInstaller.__main__
from pathlib import Path

def build(config: str):
    """Build the application using PyInstaller."""
    print(f"--- Building {config} configuration ---")
    
    app_name = "VoiceFlow"
    if config == "Debug":
        app_name += "_Debug"
        
    build_dir = Path("build") / config
    dist_dir = Path("dist") / config
    
    # Base arguments
    args = [
        "src/voiceflow/__main__.py",
        f"--name={app_name}",
        "--onedir",          # Use onedir instead of onefile to avoid huge temp extraction
        "--clean",
        "--noconfirm",
        f"--workpath={build_dir}",
        f"--distpath={dist_dir}",
        "--add-data=src/voiceflow/ui/assets;voiceflow/ui/assets",
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
    parser = argparse.ArgumentParser(description="Build VoiceFlow Local")
    parser.add_argument("--config", choices=["Debug", "Release", "All"], default="All")
    args = parser.parse_args()
    
    if args.config in ["Debug", "All"]:
        build("Debug")
    if args.config in ["Release", "All"]:
        build("Release")
