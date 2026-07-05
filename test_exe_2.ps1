 = "E:\Apps\Voky\dist\Release\MouthFull\MouthFull.exe"
if (-Not (Test-Path )) {
    Write-Host "Executable not found!"
    exit 1
}

Write-Host "Starting MouthFull.exe..."
 = Start-Process -FilePath  -PassThru -NoNewWindow
Start-Sleep -Seconds 20

if (.HasExited) {
    Write-Host "Process crashed with exit code "
}

Write-Host "Checking logs for Whisper diagnostics..."
 = "C:\Users\asus\AppData\Roaming\MouthFullLocal\logs\mouthfull.log"
if (Test-Path ) {
     = Get-Content  -Tail 50
     | Select-String -Pattern "STT Initialization Diagnostics" -Context 0, 15 | Write-Host
}

Write-Host "Killing process..."
Stop-Process -Id .Id -Force
Write-Host "Test complete."
