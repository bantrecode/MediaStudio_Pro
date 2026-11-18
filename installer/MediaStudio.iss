; Inno Setup Script for All-in-One Media Studio Pro
; Tương thích Inno Setup 6.x
; Cài đặt chế độ Non-Admin (%LOCALAPPDATA%\Programs\MediaStudio)

#define MyAppName "MediaStudio Pro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MediaStudio"
#define MyAppURL "https://github.com/MediaStudio/MediaStudio"
#define MyAppExeName "MediaStudio.exe"

[Setup]
; App GUID định danh duy nhất cho ứng dụng
AppId={{C782924F-D819-4876-92F0-27F47F3B90B2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\MediaStudio
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Không yêu cầu quyền Administrator - cài trực tiếp vào LocalAppData
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=MediaStudio_Setup
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "contextmenu"; Description: "Thêm ""Mở bằng MediaStudio Pro"" vào menu chuột phải cho video và audio"; GroupDescription: "Tùy chọn tích hợp hệ thống:"

[Files]
Source: "..\dist\MediaStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Tùy chọn menu ngữ cảnh chuột phải cho toàn bộ Video Files
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\video\shell\MediaStudio"; ValueType: string; ValueName: ""; ValueData: "Mở bằng MediaStudio Pro"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\video\shell\MediaStudio"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\video\shell\MediaStudio\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: contextmenu

; Tùy chọn menu ngữ cảnh chuột phải cho toàn bộ Audio Files
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\audio\shell\MediaStudio"; ValueType: string; ValueName: ""; ValueData: "Mở bằng MediaStudio Pro"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\audio\shell\MediaStudio"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\audio\shell\MediaStudio\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: contextmenu

; Đăng ký ứng dụng vào HKCU App Paths để gọi được MediaStudio.exe từ Run/cmd
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
