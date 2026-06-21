; Inno Setup script - "Asystent Spotkan Klastra" (offline installer)
;
; Produces a single Setup.exe that needs NO Python and NO PowerShell.
; It bundles: the packaged app (PyInstaller), the whisper.cpp engine, the
; Whisper model, and the offline WebView2 Runtime installer. The end user just
; double-clicks - no internet required.
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
; WebView2 Runtime (offline standalone installer) - only copied/run when missing.
Source: "{#Stage}\webview2\MicrosoftEdgeWebView2RuntimeInstaller.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedWebView2

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"; IconFilename: "{app}\klaster.ico"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; IconFilename: "{app}\klaster.ico"; Tasks: desktopicon

[Run]
; Offer to launch the app at the end (WebView2 is installed earlier, in [Code]).
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ Read the WebView2 Runtime version ('pv') for the Evergreen runtime GUID. }
function ReadWV2Version(RootKey: Integer; SubKey: String): String;
var
  V: String;
begin
  Result := '';
  if RegQueryStringValue(RootKey, SubKey, 'pv', V) then
    Result := V;
end;

{ True only when a real, non-empty runtime version is registered (an orphaned
  key left after an uninstall has an empty/'0.0.0.0' pv and must not count). }
function WebView2Installed: Boolean;
var
  Guid, V: String;
begin
  Guid := '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  V := ReadWV2Version(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + Guid);
  if V = '' then V := ReadWV2Version(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + Guid);
  if V = '' then V := ReadWV2Version(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + Guid);
  Result := (V <> '') and (V <> '0.0.0.0');
end;

function NeedWebView2: Boolean;
begin
  Result := not WebView2Installed;
end;

{ Install the bundled offline WebView2 Runtime if it is missing, and verify it
  actually succeeded instead of silently reporting success. }
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  ExePath: String;
begin
  if (CurStep = ssPostInstall) and NeedWebView2 then
  begin
    ExePath := ExpandConstant('{tmp}\MicrosoftEdgeWebView2RuntimeInstaller.exe');
    if FileExists(ExePath) then
    begin
      Exec(ExePath, '/silent /install', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
      if NeedWebView2 then
        MsgBox('Nie udało się zainstalować składnika Microsoft Edge WebView2 Runtime, '
          + 'który jest potrzebny do uruchomienia aplikacji. Uruchom instalator ponownie '
          + 'lub zainstaluj WebView2 ręcznie ze strony Microsoft.', mbError, MB_OK);
    end;
  end;
end;
