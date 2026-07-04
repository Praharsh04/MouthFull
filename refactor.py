import os
import shutil
import re

ROOT_DIR = r"E:\Apps\Voky"
SRC_DIR = os.path.join(ROOT_DIR, "src", "mouthfull")

def main():
    replacements = [
        (r'\bmouthfull\.audio\b', 'mouthfull.backend.audio'),
        (r'\bmouthfull\.injection\b', 'mouthfull.backend.injection'),
        (r'\bmouthfull\.input\b', 'mouthfull.backend.input'),
        (r'\bmouthfull\.llm\b', 'mouthfull.backend.llm'),
        (r'\bmouthfull\.stt\b', 'mouthfull.backend.stt'),
        
        (r'\bmouthfull\.core\.config\b', 'mouthfull.configs.config'),
        (r'\bmouthfull\.core\.logger\b', 'mouthfull.utils.logger'),
        (r'\bmouthfull\.core\.perf\b', 'mouthfull.utils.perf'),
        (r'\bmouthfull\.core\.exceptions\b', 'mouthfull.utils.exceptions'),
        (r'\bmouthfull\.core\.events\b', 'mouthfull.utils.events'),
        (r'\bmouthfull\.core\.download_manager\b', 'mouthfull.utils.download_manager'),
        
        (r'\bmouthfull\.ui\.assets\b', 'mouthfull.assets'),
    ]
    
    str_replacements = [
        ("assets/icons", "assets/icons"),
        ("mouthfull/assets", "mouthfull/assets"),
        ("ui\\\\assets\\\\icons", "assets\\\\icons"),
        ("assets\\icons", "assets\\icons"),
    ]

    py_files = []
    for root, _, files in os.walk(ROOT_DIR):
        if ".git" in root or "venv" in root or ".venv" in root or "build" in root or "dist" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py") or f.endswith(".pyw"):
                py_files.append(os.path.join(root, f))

    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            for old, new in replacements:
                content = re.sub(old, new, content)
            
            for old, new in str_replacements:
                content = content.replace(old, new)
            
            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated imports in {py_file}")
        except Exception as e:
            print(f"Error processing {py_file}: {e}")

if __name__ == "__main__":
    main()
