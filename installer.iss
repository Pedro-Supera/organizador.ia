; Script do Inno Setup para Organizador Inteligente
; Gerado em: 30/08/2026
; Requer: Inno Setup 6 ou superior

[Setup]
AppName=Organizador Inteligente
AppVersion=1.0.0
AppPublisher=Pedro Supera
AppPublisherURL=https://github.com/Pedro-Supera/organizador.ia
AppSupportURL=https://github.com/Pedro-Supera/organizador.ia/issues
AppComments=Organizador de arquivos com IA
AppGUID={{12345678-1234-1234-1234-1234567890AB}
DefaultDirName={pf}\OrganizadorInteligente
DefaultGroupName=OrganizadorInteligente
CreateNoIconInProgramGroup=False
OutputDir=dist
OutputBaseName=OrganizadorInteligente_Setup
Compression=best
LZMAUseSolidImage=True
PrivilegesRequired=user
Uninstallable=True
Languages=portuguese
Architecture=amd64
VersionInfoVersion=1.0.0
VersionInfoCompany=Pedro Supera
VersionInfoProductName=Organizador Inteligente

[Files]
Source: "dist\OrganizadorInteligente.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "*.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "contexto.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\\OrganizadorInteligente"; ValueName: "Installed"; ValueData: "1"; Flags: none

[Run]
Filename: "{app}\OrganizadorInteligente.exe"; Description: {cm:LaunchApp,Organizador Inteligente}; Flags: postinstall skipifdoesntexist

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*"
