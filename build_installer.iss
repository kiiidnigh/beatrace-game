[Setup]
; Grundlegende App-Informationen [cite: 1]
AppName=Beatrace
AppVersion=1.5.1
AppPublisher=kiiidnigh
AppPublisherURL=https://github.com/kiiidnigh/beatrace-game
SetupIconFile=assets\icon.ico

; Installation im AppData-Verzeichnis [cite: 2]
PrivilegesRequired=lowest
DefaultDirName={autopf}\Beatrace
OutputDir=.\installer
OutputBaseFilename=Beatrace_Installer_v1.5.1

; Komprimierung [cite: 3]
Compression=lzma2/max
SolidCompression=yes
UpdateUninstallLogAppName=no

[Tasks]
; Desktop-Icon Checkbox [cite: 4]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Files]
; WICHTIG: Nimmt ALLES aus dem dist\Beatrace Ordner (inklusive _internal)
Source: "dist\Beatrace\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Nimmt den Assets-Ordner [cite: 6]
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Startmenü [cite: 7]
Name: "{autoprograms}\Beatrace"; Filename: "{app}\Beatrace.exe"
; Desktop [cite: 8]
Name: "{autodesktop}\Beatrace"; Filename: "{app}\Beatrace.exe"; Tasks: desktopicon

[Run]
; Startoption nach Installation
Filename: "{app}\Beatrace.exe"; Description: "Beatrace starten"; Flags: nowait postinstall skipifsilent