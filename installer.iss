[Setup]
AppName=MouthFull Local
AppVersion=0.1.0
AppPublisher=MouthFull Contributors
AppPublisherURL=https://github.com/mouthfull/mouthfull-local
DefaultDirName={autopf}\MouthFullLocal
DefaultGroupName=MouthFull Local
UninstallDisplayIcon={app}\MouthFull.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=release
OutputBaseFilename=MouthFull_Local_Setup
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Release\MouthFull\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MouthFull Local"; Filename: "{app}\MouthFull.exe"
Name: "{group}\{cm:UninstallProgram,MouthFull Local}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MouthFull Local"; Filename: "{app}\MouthFull.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MouthFull.exe"; Description: "{cm:LaunchProgram,MouthFull Local}"; Flags: nowait postinstall skipifsilent
