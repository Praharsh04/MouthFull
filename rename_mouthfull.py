import os
import re

ROOT_DIR = r"E:\Apps\Voky"

def main():
    replacements = [
        ("Blab", "MouthFull"),
        ("blab", "mouthfull"),
        ("BLAB", "MOUTHFULL"),
    ]

    for root, _, files in os.walk(ROOT_DIR):
        if any(ignore in root for ignore in [".git", "venv", ".venv", "build", "dist", "__pycache__"]):
            continue
        
        for f in files:
            if f in ["rename_blab.py", "rename_mouthfull.py", "Group 91.svg", "Group 91.png", "voci_logo.png", "crash.log", "crash2.log"]:
                continue
                
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                original_content = content
                for old, new in replacements:
                    content = content.replace(old, new)
                    
                if content != original_content:
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(content)
                    print(f"Updated {filepath}")
            except UnicodeDecodeError:
                pass
            except Exception as e:
                print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    main()
