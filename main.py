import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QMessageBox, QDialog,
    QLineEdit, QFormLayout, QProgressBar, QComboBox,
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QFont
import json
import logging
from common.activation_manager import ActivationManager
from common.translations import Translator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.activation_manager = ActivationManager()
        self.translator = Translator()
        self._init_ui()
        self._load_settings()

    def _load_settings(self):
        """Load application settings"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                    if 'language' in settings:
                        self.translator.set_language(settings['language'])
                        self._update_ui_language()
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def _save_settings(self):
        """Save application settings"""
        try:
            settings = {
                'language': self.translator.language
            }
            with open('settings.json', 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(self.translator.get('app_title'))
        self.setMinimumSize(400, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Language selection
        lang_layout = QHBoxLayout()
        lang_label = QLabel(self.translator.get('language'))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(self.translator.get('arabic'), 'ar')
        self.lang_combo.addItem(self.translator.get('english'), 'en')
        self.lang_combo.currentIndexChanged.connect(self._handle_language_change)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # Title
        title_label = QLabel(self.translator.get('app_title'))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title_label)

        # User type selection
        client_btn = QPushButton(self.translator.get('client'))
        client_btn.clicked.connect(lambda: self._handle_user_type("client"))
        client_btn.setStyleSheet("font-size: 16px; padding: 10px; margin: 10px;")
        layout.addWidget(client_btn)

        technician_btn = QPushButton(self.translator.get('technician'))
        technician_btn.clicked.connect(lambda: self._handle_user_type("technician"))
        technician_btn.setStyleSheet("font-size: 16px; padding: 10px; margin: 10px;")
        layout.addWidget(technician_btn)

        # Add some spacing
        layout.addStretch()

    def _handle_language_change(self, index):
        """Handle language change"""
        language = self.lang_combo.itemData(index)
        if self.translator.set_language(language):
            self._update_ui_language()
            self._save_settings()

    def _update_ui_language(self):
        """Update UI elements with current language"""
        self.setWindowTitle(self.translator.get('app_title'))
        self.lang_combo.setItemText(0, self.translator.get('arabic'))
        self.lang_combo.setItemText(1, self.translator.get('english'))
        # Update other UI elements...

    def _handle_user_type(self, user_type):
        """Handle user type selection"""
        if user_type == "technician":
            # During testing phase, bypass activation
            self._start_technician_mode()
        else:
            # For clients, start client mode directly
            self._start_client_mode()

    def _start_client_mode(self):
        """Start client mode"""
        try:
            from client.gui import ClientGUI
            self.client_window = ClientGUI(self.translator)
            self.client_window.show()
            self.close()
        except Exception as e:
            logger.error(f"Error starting client mode: {e}")
            QMessageBox.critical(self, self.translator.get('error'), 
                               self.translator.get('client_start_failed'))

    def _start_technician_mode(self):
        """Start technician mode"""
        try:
            from server.gui import ServerGUI
            self.server_window = ServerGUI(self.translator)
            self.server_window.show()
            self.close()
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            QMessageBox.critical(self, self.translator.get('error'),
                               f"Missing required dependencies: {str(e)}\nPlease install all requirements using: pip install -r requirements.txt")
        except Exception as e:
            logger.error(f"Error starting technician mode: {e}")
            QMessageBox.critical(self, self.translator.get('error'), 
                               self.translator.get('server_start_failed'))

class ActivationDialog(QDialog):
    def __init__(self, activation_manager, translator, parent=None):
        super().__init__(parent)
        self.activation_manager = activation_manager
        self.translator = translator
        self.setWindowTitle(self.translator.get('activation'))
        self.setMinimumWidth(400)
        self._init_ui()
        self._start_timer()

    def _init_ui(self):
        """Initialize the user interface"""
        layout = QFormLayout(self)

        # Activation key input
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(self.translator.get('enter_key'))
        layout.addRow(self.translator.get('activation_key') + ":", self.key_input)

        # Remaining days
        self.remaining_days_label = QLabel(self.translator.get('remaining_days') + ": --")
        layout.addRow("", self.remaining_days_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 30)
        self.progress_bar.setValue(0)
        layout.addRow("", self.progress_bar)

        # Buttons
        button_layout = QVBoxLayout()
        
        activate_btn = QPushButton(self.translator.get('activate'))
        activate_btn.clicked.connect(self._handle_activation)
        button_layout.addWidget(activate_btn)
        
        cancel_btn = QPushButton(self.translator.get('cancel'))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow("", button_layout)

    def _start_timer(self):
        """Start timer to update remaining days"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_remaining_days)
        self.timer.start(60000)  # Update every minute
        self._update_remaining_days()

    def _update_remaining_days(self):
        """Update remaining days display"""
        key = self.key_input.text().strip()
        if key:
            remaining_days = self.activation_manager.get_remaining_days(key)
            self.remaining_days_label.setText(
                f"{self.translator.get('remaining_days')}: {remaining_days}")
            self.progress_bar.setValue(30 - remaining_days)
        else:
            self.remaining_days_label.setText(
                f"{self.translator.get('remaining_days')}: --")
            self.progress_bar.setValue(0)

    def _handle_activation(self):
        """Handle activation"""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, self.translator.get('error'),
                              self.translator.get('invalid_key'))
            return

        # Verify and activate key
        is_valid, message = self.activation_manager.verify_key(key)
        if not is_valid:
            QMessageBox.warning(self, self.translator.get('error'), message)
            return

        # Activate key
        success, message = self.activation_manager.activate_key(key)
        if success:
            QMessageBox.information(self, self.translator.get('success'),
                                  self.translator.get('activation_success'))
            self.accept()
        else:
            QMessageBox.warning(self, self.translator.get('error'), message)

    def closeEvent(self, event):
        """Handle dialog close event"""
        self.timer.stop()
        super().closeEvent(event)

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 