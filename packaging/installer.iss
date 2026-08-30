; Inno Setup script for RPG Lifer.
; Builds a friendly Windows installer (Start-menu shortcut, optional desktop
; shortcut, and an uninstall entry) around the PyInstaller-built RPGLifer.exe.
; Build on Windows after PyInstaller with:
;   ISCC.exe packaging\installer.iss
; (CI installs Inno Setup and runs this automatically — see the workflow.)

#define MyAppName "RPG Lifer"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "PainHog"
#define MyAppExeName "RPGLifer.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-47A8-9B0C-1D2E3F405162}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\RPG Lifer
DefaultGroupName=RPG Lifer
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\installer
OutputBaseFilename=RPGLifer-Setup
SetupIconFile=rpglifer.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\RPG Lifer"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall RPG Lifer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\RPG Lifer"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch RPG Lifer"; Flags: nowait postinstall skipifsilent
