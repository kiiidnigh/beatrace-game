[Setup]
; Grundlegende App-Informationen
AppName=Beatrace
AppVersion=1.2.0
AppPublisher=kiiidnigh
AppPublisherURL=https://github.com/kiiidnigh/beatrace-game
DefaultGroupName=Beatrace
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\Beatrace.exe

; Installation im User-Verzeichnis (keine Admin-Rechte nötig)
PrivilegesRequired=lowest
DefaultDirName={autopf}\Beatrace

; Output-Einstellungen
OutputDir=.\installer
OutputBaseFilename=Beatrace_Installer_v1.2.0

; Komprimierungseinstellungen
Compression=lzma2/max
SolidCompression=yes

; Sorgt für sauberes Überschreiben bei Updates
UpdateUninstallLogAppName=no

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Files]
; 1. Der gesamte Inhalt des PyInstaller Verzeichnisses (onedir Modus)
; WICHTIG: Hier wird das gesamte Verzeichnis genommen, da wir kein --onefile nutzen
Source: "dist\Beatrace\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 2. Der Assets-Ordner (wird separat neben die EXE gelegt)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Startmenü-Verknüpfung
Name: "{autoprograms}\Beatrace"; Filename: "{app}\Beatrace.exe"
; Desktop-Verknüpfung
Name: "{autodesktop}\Beatrace"; Filename: "{app}\Beatrace.exe"; Tasks: desktopicon

[Run]
; Option, die App nach der Installation direkt zu starten
Filename: "{app}\Beatrace.exe"; Description: "Beatrace jetzt starten"; Flags: nowait postinstall skipifsilent