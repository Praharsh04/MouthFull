 = "E:\Apps\Voky\dist\Release\MouthFull\MouthFull.exe"
if (-Not (Test-Path )) {
    Write-Host "Executable not found at "
    exit 1
}

Write-Host "Starting MouthFull.exe..."
 = Start-Process -FilePath  -PassThru -NoNewWindow

Write-Host "Waiting 15 seconds for startup..."
Start-Sleep -Seconds 15

if (.HasExited) {
    Write-Host "Process crashed with exit code "
    exit 1
}

Write-Host "Process is running. Checking logs..."
 = "C:\Users\asus\AppData\Roaming\MouthFullLocal\logs\mouthfull.log"
if (Test-Path ) {
     = Get-Content  -Tail 20
     = False
    foreach ( in ) {
        if ( -match "MouthFull Local is ready") {
             = True
        }
    }
    if () {
        Write-Host "Successfully found ready message in logs!"
    } else {
        Write-Host "Did not find ready message in recent logs. Logs:"
         | Out-String | Write-Host
    }
} else {
    Write-Host "Log file not found."
}

Write-Host "Killing process..."
Stop-Process -Id .Id -Force
Write-Host "Test complete."
