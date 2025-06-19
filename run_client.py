import sys
import asyncio
import logging
from PyQt5.QtWidgets import QApplication
from client.gui import ClientGUI
from client.main import USBRedirectorClient
from common.translator import Translator
import qasync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to run the client"""
    try:
        # Initialize Qt application
        app = QApplication(sys.argv)
        
        # Initialize translator
        translator = Translator()
        
        # Initialize GUI
        gui = ClientGUI(translator)
        gui.show()
        
        # Initialize client
        client = USBRedirectorClient(gui)
        gui.set_client(client)
        
        # Run Qt event loop
        await qasync.QEventLoop(app).run_forever()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Error running client: {e}")
        sys.exit(1) 