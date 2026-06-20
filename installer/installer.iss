; Inno Setup script - "Asystent Spotkan Klastra" (offline installer)
;
; Produces a single Setup.exe that needs NO Python and NO PowerShell.
; It bundles: the packaged app (PyInstaller), the whisper.cpp engine, the
; Whisper model, and the WebView2 bootstrapper. The end user just double-clicks.
;
; The build pipeline assembles a staging folder and passes its path + version:
;   ISCC.exe installer.iss /DStage="..\build" /DAppVersion="1.0.0"

#ifndef Stage
  #define Stage "..\build"
#endif
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define AppName "Asystent Spotkań Klastra"
#define ExeName "AsystentSpotkan.exe"
#define Publisher "Klaster Innowacji Społecznych"
#define PublisherURL "https://klaster1234.github.io/asystent-spotkan-klastra/"

[Setup]
AppId={{8B7C3D2E-4F1A-4C9B-9E2D-7A6F5C4B3A21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#PublisherURL}
AppSupportURL={#PublisherURL}
DefaultDirName={autopf}\Asystent Spotkan Klastra
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableReadyPage=no
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=AsystentSpotkanKlastra-Setup
SetupIconFile=..\assets\klaster.ico
UninstallDisplayIcon={app}\klaster.ico
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
PrivilegesRequired=admin
MinVersion=10.0

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Packaged application (PyInstaller one-folder output).
Source: "{#Stage}\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; whisper.cpp engine -> {app}\bin\Release\whisper-cli.exe (+ DLLs).
Source: "{#Stage}\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
; Whisper model.
Source: "{#Stage}\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
; Icon used by the shortcuts and Add/Remove Programs.
Source: "..\assets\klaster.ico"; DestDir: "{app}"; Flags: ignoreversion
; WebView2 bootstrapper - only copied/run when WebView2 is missing.
Source: "{#Stage}\webview2\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedWebView2

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"; IconFilename: "{app}\klaster.ico"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; IconFilename: "{app}\klaster.ico"; Tasks: desktopicon

[Run]
; Install Microsoft Edge WebView2 Runtime only if it is not present yet.
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Instaluję Microsoft Edge WebView2 Runtime..."; Check: NeedWebView2; Flags: waituntilterminated
; Offer to launch the app at the end.
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
function WebView2Installed: Boolean;
var
  Guid: String;
begin
  Guid := '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result :=
    RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + Guid) or
    RegKeyExists(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + Guid) or
    RegKeyExists(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + Guid);
end;

function NeedWebView2: Boolean;
begin
  Result := not WebView2Installed;
end;
