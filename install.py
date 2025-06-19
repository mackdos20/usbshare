import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    directories = [
        "common",
        "client",
        "server",
        os.path.join(os.path.expanduser("~"), ".usb_redirector"),
        os.path.join(os.path.expanduser("~"), ".usb_redirector", "certificates"),
        os.path.join(os.path.expanduser("~"), ".usb_redirector", "keys"),
        os.path.join(os.path.expanduser("~"), ".usb_redirector", "logs")
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            sys.exit(1)

def generate_certificates():
    """Generate SSL certificates"""
    print("Generating SSL certificates...")
    cert_dir = os.path.join(os.path.expanduser("~"), ".usb_redirector", "certificates")
    
    try:
        # Generate private key
        subprocess.check_call([
            "openssl", "genrsa",
            "-out", os.path.join(cert_dir, "private.key"),
            "2048"
        ])
        
        # Generate CSR
        subprocess.check_call([
            "openssl", "req", "-new",
            "-key", os.path.join(cert_dir, "private.key"),
            "-out", os.path.join(cert_dir, "certificate.csr"),
            "-subj", "/CN=USB Redirector"
        ])
        
        # Generate self-signed certificate
        subprocess.check_call([
            "openssl", "x509", "-req",
            "-days", "365",
            "-in", os.path.join(cert_dir, "certificate.csr"),
            "-signkey", os.path.join(cert_dir, "private.key"),
            "-out", os.path.join(cert_dir, "certificate.crt")
        ])
        
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificates: {e}")
        sys.exit(1)

def create_shortcuts():
    """Create desktop shortcuts"""
    print("Creating shortcuts...")
    
    if platform.system() == "Windows":
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            
            # Client shortcut
            client_path = os.path.abspath("client/main.py")
            client_shortcut = os.path.join(desktop, "USB Redirector Client.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(client_shortcut)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{client_path}"'
            shortcut.WorkingDirectory = os.path.dirname(client_path)
            shortcut.save()
            
            # Server shortcut
            server_path = os.path.abspath("server/main.py")
            server_shortcut = os.path.join(desktop, "USB Redirector Server.lnk")
            
            shortcut = shell.CreateShortCut(server_shortcut)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{server_path}"'
            shortcut.WorkingDirectory = os.path.dirname(server_path)
            shortcut.save()
            
        except Exception as e:
            print(f"Error creating shortcuts: {e}")
            sys.exit(1)

def setup_service():
    """Setup Windows service"""
    if platform.system() == "Windows":
        print("Setting up Windows service...")
        try:
            import win32serviceutil
            import win32service
            import win32event
            import servicemanager
            
            # Create service
            win32serviceutil.CreateService(
                "USBRedirector",
                "USB Redirector Service",
                "USB Redirector Service",
                startType=win32service.SERVICE_AUTO_START,
                bInteractive=False,
                serviceType=win32service.SERVICE_WIN32_OWN_PROCESS
            )
            
        except Exception as e:
            print(f"Error setting up service: {e}")
            sys.exit(1)

def main():
    """Main installation function"""
    print("Starting USB Redirector installation...")
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_dependencies()
    
    # Create directories
    create_directories()
    
    # Generate certificates
    generate_certificates()
    
    # Create shortcuts
    create_shortcuts()
    
    # Setup service
    setup_service()
    
    print("Installation completed successfully!")

if __name__ == "__main__":
    main() 