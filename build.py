import os
import sys
import shutil
import subprocess
import json
from pathlib import Path

def install_requirements():
    """Install required packages for building"""
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def create_executable():
    """Create executable using PyInstaller"""
    # Create spec file for client
    client_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PyQt5.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Mack-DDoS Share',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)
    """
    
    # Write spec file
    with open('mack_ddos_share.spec', 'w') as f:
        f.write(client_spec)
    
    # Build executable
    subprocess.run([
        'pyinstaller',
        '--clean',
        '--noconfirm',
        '--windowed',
        '--icon=icon.ico',
        '--name=Mack-DDoS Share',
        '--add-data=common;common',
        '--add-data=client;client',
        '--add-data=server;server',
        'main.py'
    ])

def copy_activation_keys():
    """Copy activation keys to dist folder"""
    if os.path.exists('activation_keys.json'):
        shutil.copy('activation_keys.json', 'dist/Mack-DDoS Share/')

def create_installer():
    """Create installer using NSIS"""
    # Create NSIS script
    nsis_script = """
!include "MUI2.nsh"

Name "Mack-DDoS Share"
OutFile "Mack-DDoS Share Setup.exe"
InstallDir "$PROGRAMFILES\\Mack-DDoS Share"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    File /r "dist\\Mack-DDoS Share\\*.*"
    
    CreateDirectory "$SMPROGRAMS\\Mack-DDoS Share"
    CreateShortcut "$SMPROGRAMS\\Mack-DDoS Share\\Mack-DDoS Share.lnk" "$INSTDIR\\Mack-DDoS Share.exe"
    CreateShortcut "$DESKTOP\\Mack-DDoS Share.lnk" "$INSTDIR\\Mack-DDoS Share.exe"
    
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Mack-DDoS Share" \
                     "DisplayName" "Mack-DDoS Share"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Mack-DDoS Share" \
                     "UninstallString" "$INSTDIR\\uninstall.exe"
SectionEnd

Section "Uninstall"
    RMDir /r "$SMPROGRAMS\\Mack-DDoS Share"
    Delete "$DESKTOP\\Mack-DDoS Share.lnk"
    RMDir /r "$INSTDIR"
    
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Mack-DDoS Share"
SectionEnd
    """
    
    # Write NSIS script
    with open('installer.nsi', 'w') as f:
        f.write(nsis_script)
    
    # Build installer
    subprocess.run(['makensis', 'installer.nsi'])

def main():
    """Main build process"""
    print("Installing requirements...")
    install_requirements()
    
    print("Creating executable...")
    create_executable()
    
    print("Copying activation keys...")
    copy_activation_keys()
    
    print("Creating installer...")
    create_installer()
    
    print("Build completed successfully!")

if __name__ == '__main__':
    main() 