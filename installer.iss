[Setup]
AppName=VoiceFlow Local
AppVersion=0.1.0
AppPublisher=VoiceFlow Contributors
AppPublisherURL=https://github.com/voiceflow/voiceflow-local
DefaultDirName={autopf}\VoiceFlowLocal
DefaultGroupName=VoiceFlow Local
UninstallDisplayIcon={app}\VoiceFlow.exe
Compression=lzma2
SolidCompression=yes
OutputDir=release
OutputBaseFilename=VoiceFlow_Local_Setup
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Release\VoiceFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VoiceFlow Local"; Filename: "{app}\VoiceFlow.exe"
Name: "{group}\{cm:UninstallProgram,VoiceFlow Local}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\VoiceFlow Local"; Filename: "{app}\VoiceFlow.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VoiceFlow.exe"; Description: "{cm:LaunchProgram,VoiceFlow Local}"; Flags: nowait postinstall skipifsilent
