; Inno Setup script for Apipos (Windows installer).
; Build with:  iscc installer-windows.iss   (after build-windows.bat created dist\Apipos.exe)
; Download Inno Setup: https://jrsoftware.org/isdl.php

; Defaults — overridable from build-windows.bat via:  iscc /DAppName=... /DAppVersion=... /DAppPublisher=...
#ifndef AppName
  #define AppName "Apipos"
#endif
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef AppPublisher
  #define AppPublisher "Tecsom"
#endif
#define AppExe AppName + ".exe"

[Setup]
AppId={{B8E7B0C2-1A4D-4E6F-9C3A-7D2E5F018A4B}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename={#AppName}-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "startup"; Description: "Iniciar {#AppName} al encender Windows"; GroupDescription: "Inicio automático:"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"

[Registry]
; Start with Windows (only if the "startup" task is selected)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExe}"""; \
  Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Ejecutar {#AppName} ahora"; \
  Flags: nowait postinstall skipifsilent
