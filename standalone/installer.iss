; Inno Setup 6 script — Manhattan Mission Control Windows Installer
; Compile with:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

#define AppName       "Manhattan Mission Control"
#define AppVersion    "3.0"
#define AppPublisher  "Richard Yudkiss"
#define AppURL        "https://github.com/ryudkiss-hue/nyc_data"
#define AppExeName    "MissionControl.exe"
#define LauncherExe   "MissionControlLauncher.exe"

[Setup]
AppId={{B3A1C2D4-5E6F-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=ManhattanMissionControlSetup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64os

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Native desktop app (pywebview) — primary entry point
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Install / configuration wizard (tkinter) — for first-run setup
Source: "dist\{#LauncherExe}"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Application source files
Source: "..\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Primary shortcut → native desktop window
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
; Secondary shortcut → setup / configuration wizard
Name: "{group}\{#AppName} Setup"; Filename: "{app}\{#LauncherExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Run the configuration wizard first so the user can enter API keys, then it
; can launch the app. Falls back gracefully if the launcher isn't present.
Filename: "{app}\{#LauncherExe}"; Description: "Configure & launch {#AppName}"; Flags: nowait postinstall skipifsilent skipifdoesntexist

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
