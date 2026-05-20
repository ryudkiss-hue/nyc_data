; NYC DOT Sidewalk Toolkit — Inno Setup 6 script
; Build: powershell -File scripts\build_installer.ps1
; Requires: dist\nyc-dot-toolkit.exe (run scripts\build_exe.py first)

#define MyAppName "NYC DOT Sidewalk Toolkit"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "NYC Department of Transportation"
#define MyAppExeName "nyc-dot-toolkit.exe"
#define RepoRoot ".."

[Setup]
AppId={{A7B3E4F1-9C2D-4E8A-B5F6-1D0E3A9C7B42}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=NYC-DOT-Sidewalk-Toolkit-Setup
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=
InfoBeforeFile=INSTALL.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "runwizard"; Description: "Run setup wizard now (non-interactive; uses environment variables if set)"; GroupDescription: "Post-install:"; Flags: unchecked
Name: "scheduledtask"; Description: "Register weekly Analyst Pack in Task Scheduler (Sunday 11:00 PM)"; GroupDescription: "Post-install:"; Flags: unchecked
Name: "desktopicon"; Description: "Create a desktop shortcut to Getting Started"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Main executable (build with scripts\build_exe.py before compiling this script)
Source: "{#RepoRoot}\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Config templates — no secrets
Source: "{#RepoRoot}\config\analyst_profile.example.yaml"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "{#RepoRoot}\config\.env.example"; DestDir: "{app}\config"; DestName: ".env.example"; Flags: ignoreversion
Source: "{#RepoRoot}\config\budget_codes.yaml"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "{#RepoRoot}\config\role_profiles\*"; DestDir: "{app}\config\role_profiles"; Flags: ignoreversion recursesubdirs
Source: "{#RepoRoot}\config\inquiry_templates\*"; DestDir: "{app}\config\inquiry_templates"; Flags: ignoreversion recursesubdirs
Source: "{#RepoRoot}\config\templates\*"; DestDir: "{app}\config\templates"; Flags: ignoreversion recursesubdirs
; Documentation
Source: "{#RepoRoot}\docs\SIMPLE_START.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "{#RepoRoot}\docs\GETTING_STARTED.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "{#RepoRoot}\docs\USER_MANUAL.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "INSTALL.txt"; DestDir: "{app}"; Flags: ignoreversion
; Helper scripts
Source: "{#RepoRoot}\scripts\register_scheduled_task.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#RepoRoot}\scripts\launch_gui.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#RepoRoot}\scripts\launch_dashboard.bat"; DestDir: "{app}"; DestName: "launch_dashboard.bat"; Flags: ignoreversion

[Icons]
Name: "{group}\Simple Start"; Filename: "{app}\docs\SIMPLE_START.md"
Name: "{group}\Getting Started"; Filename: "{app}\docs\GETTING_STARTED.md"
Name: "{group}\{#MyAppName} Setup Wizard"; Filename: "{app}\{#MyAppExeName}"; Parameters: "wizard"; Comment: "Configure .env and analyst profile"
Name: "{group}\Run Analyst Pack"; Filename: "{app}\{#MyAppExeName}"; Parameters: "analyst run --profile ""{app}\config\analyst_profile.yaml"""; Comment: "Run weekly analyst autopilot once"
Name: "{group}\Open Dashboard"; Filename: "{app}\launch_dashboard.bat"; Comment: "Launch Dash GUI or open setup guide"
Name: "{group}\User Manual"; Filename: "{app}\docs\USER_MANUAL.md"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\docs\GETTING_STARTED.md"; Tasks: desktopicon

[Run]
Filename: "{app}\docs\SIMPLE_START.md"; Description: "Open Simple Start guide"; Flags: postinstall nowait skipifsilent shellexec
Filename: "{app}\{#MyAppExeName}"; Parameters: "wizard --non-interactive --skip-checks --root ""{app}"""; StatusMsg: "Running setup wizard (non-interactive)…"; Flags: postinstall nowait skipifsilent; Tasks: runwizard
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\register_scheduled_task.ps1"" -AppDir ""{app}"""; StatusMsg: "Registering scheduled task…"; Flags: postinstall runhidden; Tasks: scheduledtask

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\register_scheduled_task.ps1"" -AppDir ""{app}"" -Remove"; Flags: runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ExampleProfile, TargetProfile: String;
begin
  if CurStep = ssPostInstall then
  begin
    ExampleProfile := ExpandConstant('{app}\config\analyst_profile.example.yaml');
    TargetProfile := ExpandConstant('{app}\config\analyst_profile.yaml');
    if FileExists(ExampleProfile) and not FileExists(TargetProfile) then
      FileCopy(ExampleProfile, TargetProfile, False);
  end;
end;
