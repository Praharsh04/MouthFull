@echo off
echo Installing requirements...
pip install -r requirements.txt
pip install pyinstaller

echo Running build script...
python scripts/build.py --config Release

echo Build complete.
