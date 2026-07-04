Write-Host "Installing requirements..."
pip install -r requirements.txt
pip install pyinstaller

Write-Host "Running build script..."
python scripts/build.py --config Release

Write-Host "Build complete."
