#ifndef BundleDir
  #error BundleDir is required
#endif
#ifndef AppVersion
  #define AppVersion "0.5.2"
#endif
[Setup]
AppId={{89085F56-E9D2-49CC-91D5-728F0E658334}
AppName=GAM3T3CH 3D Benchmark
AppVersion={#AppVersion}
AppPublisher=GAM3T3CH
AppPublisherURL=https://github.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench
DefaultDirName={localappdata}\Programs\GAM3T3CH
DefaultGroupName=GAM3T3CH 3D Benchmark
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=GAM3T3CH-{#AppVersion}-windows-x86_64-setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\GAM3T3CH.exe
DisableProgramGroupPage=yes
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
[Icons]
Name: "{group}\GAM3T3CH 3D Benchmark"; Filename: "{app}\GAM3T3CH.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall GAM3T3CH 3D Benchmark"; Filename: "{uninstallexe}"
Name: "{userdesktop}\GAM3T3CH 3D Benchmark"; Filename: "{app}\GAM3T3CH.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\GAM3T3CH.exe"; Description: "Open GAM3T3CH 3D Benchmark"; Flags: nowait postinstall skipifsilent
