[Setup]
; Grundlegende App-Informationen
AppName=Beatrace
AppVersion=1.1.1
AppPublisher=kiiidnigh
AppPublisherURL=https://github.com/kiiidnigh/beatrace-game
SetupIconFile=assets\icon.ico

; WICHTIG: Das hier sorgt dafür, dass keine Admin-Rechte (UAC) abgefragt werden!
; Das Programm wird lautlos im AppData-Verzeichnis des Nutzers installiert.
PrivilegesRequired=lowest
DefaultDirName={autopf}\Beatrace

; Wo der fertige Installer abgelegt werden soll
OutputDir=.\installer
OutputBaseFilename=Beatrace_Installer_v1.1.1

; Komprimierung (macht die Datei kleiner)
Compression=lzma
SolidCompression=yes

; Sorgt dafür, dass alte Versionen beim Auto-Update sauber überschrieben werden
UpdateUninstallLogAppName=no

[Tasks]
; Erstellt die Checkbox für das Desktop-Icon (Standardmäßig abgewählt)
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Files]
; 1. Nimm die generierte EXE aus dem dist-Ordner
Source: "dist\Beatrace.exe"; DestDir: "{app}"; Flags: ignoreversion
; 2. Nimm den Assets-Ordner (für das FL Studio Template)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Startmenü-Verknüpfung (Damit man es über die Windows-Suche findet)
Name: "{autoprograms}\Beatrace"; Filename: "{app}\Beatrace.exe"
; Desktop-Verknüpfung (Wenn der Nutzer das Häkchen setzt)
Name: "{autodesktop}\Beatrace"; Filename: "{app}\Beatrace.exe"; Tasks: desktopicon

[Run]
; Option am Ende der Installation: "Beatrace jetzt starten"
Filename: "{app}\Beatrace.exe"; Description: "Beatrace starten"; Flags: nowait postinstall skipifsilent