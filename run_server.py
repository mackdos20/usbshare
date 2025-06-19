import sys
import asyncio
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import qRegisterMetaType
from PyQt5.QtGui import QTextCursor
from server.gui import ServerGUI
from server.main import USBRedirectorServer
from common.translator import Translator
import qasync
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Register QTextCursor type
qRegisterMetaType('QTextCursor')

async def start_server(server):
    await server.start()

async def main():
    """Main function to run the server"""
    try:
        print("[DEBUG] Starting server initialization...")
        
        # Initialize Qt application
        print("[DEBUG] Initializing Qt application...")
        app = QApplication(sys.argv)
        
        # Initialize translator
        print("[DEBUG] Initializing translator...")
        translator = Translator()
        
        # Initialize GUI
        print("[DEBUG] Initializing GUI...")
        gui = ServerGUI(translator)
        gui.show()
        
        # Initialize server
        print("[DEBUG] Initializing server...")
        server = USBRedirectorServer(gui, translator)
        server.set_gui(gui)
        
        # Start server in a separate thread
        print("[DEBUG] Starting server...")
        server_thread = threading.Thread(target=lambda: asyncio.run(start_server(server)))
        server_thread.daemon = True
        server_thread.start()
        
        # Run Qt event loop
        print("[DEBUG] Starting Qt event loop...")
        await qasync.QEventLoop(app).run_forever()
        
    except Exception as e:
        print(f"[ERROR] Error in main: {e}")
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        print("[DEBUG] Starting main...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[INFO] Server stopped by user")
        logger.info("Server stopped by user")
    except Exception as e:
        print(f"[ERROR] Error running server: {e}")
        logger.error(f"Error running server: {e}")
        sys.exit(1) 