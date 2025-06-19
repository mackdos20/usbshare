import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QListWidget,
    QStatusBar, QSystemTrayIcon, QMenu, QAction,
    QMessageBox, QDialog, QLineEdit, QCheckBox,
    QGroupBox, QSpinBox, QStyle, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QClipboard, QColor
import logging
import asyncio
import threading
from common.translator import Translator
from client.main import USBRedirectorClient
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from client.main import USBRedirectorClient

logger = logging.getLogger('USB_Redirector_Client_GUI')

class ConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.translator = Translator()
        self.setWindowTitle(self.translator.translate('connect_to_server'))
        self.setModal(True)
        
        # Create layout
        layout = QVBoxLayout()
        
        # IP Address input
        ip_layout = QHBoxLayout()
        ip_label = QLabel(self.translator.translate('ip_address'))
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText('192.168.1.100')
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        layout.addLayout(ip_layout)
        
        # Port input
        port_layout = QHBoxLayout()
        port_label = QLabel(self.translator.translate('port'))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText('8765')
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)
        
        # Connect button
        self.connect_button = QPushButton(self.translator.translate('connect'))
        self.connect_button.clicked.connect(self.accept)
        layout.addWidget(self.connect_button)
        
        self.setLayout(layout)
        
    def get_connection_info(self):
        return self.ip_input.text(), self.port_input.text()

class ClientGUI(QMainWindow):
    def __init__(self, translator: Translator):
        super().__init__()
        self.translator = translator
        self.client = None
        self._init_ui()
        self._setup_tray()
        
        # Setup message handling
        self.message_queue = asyncio.Queue()
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self._process_messages)
        self.message_timer.start(100)  # Process messages every 100ms

    def _init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(self.translator.translate('app_title'))
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Connection status group
        status_group = QGroupBox(self.translator.translate('connection_status'))
        status_layout = QVBoxLayout()
        
        # Status indicator
        status_indicator_layout = QHBoxLayout()
        self.status_label = QLabel(self.translator.translate('status'))
        self.status_value = QLabel(self.translator.translate('disconnected'))
        self.status_value.setStyleSheet("color: red;")
        status_indicator_layout.addWidget(self.status_label)
        status_indicator_layout.addWidget(self.status_value)
        status_indicator_layout.addStretch()
        status_layout.addLayout(status_indicator_layout)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Connection control group
        control_group = QGroupBox(self.translator.translate('connection_control'))
        control_layout = QHBoxLayout()
        
        # Connect button
        self.connect_button = QPushButton(self.translator.translate('connect'))
        self.connect_button.clicked.connect(self._handle_connect)
        control_layout.addWidget(self.connect_button)
        
        # Disconnect button
        self.disconnect_button = QPushButton(self.translator.translate('disconnect'))
        self.disconnect_button.clicked.connect(self._handle_disconnect)
        self.disconnect_button.setEnabled(False)
        control_layout.addWidget(self.disconnect_button)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Chat group
        chat_group = QGroupBox(self.translator.translate('chat'))
        chat_layout = QVBoxLayout()
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(self.chat_display)
        
        # Message input
        message_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText(self.translator.translate('type_message'))
        self.message_input.returnPressed.connect(self._handle_send_message)
        message_layout.addWidget(self.message_input)
        
        # Send button
        self.send_button = QPushButton(self.translator.translate('send'))
        self.send_button.clicked.connect(self._handle_send_message)
        message_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(message_layout)
        chat_group.setLayout(chat_layout)
        main_layout.addWidget(chat_group)
        
    def _handle_connect(self):
        """Handle connect button click"""
        if not self.client:
            self.show_error("Client not initialized")
            return
            
        dialog = ConnectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            ip, port = dialog.get_connection_info()
            if not ip or not port:
                self.show_error(self.translator.translate('enter_ip_port'))
                return
                
            try:
                port = int(port)
                asyncio.create_task(self.client.connect(ip, port))
            except ValueError:
                self.show_error(self.translator.translate('invalid_port'))
            except Exception as e:
                self.show_error(str(e))
                
    def _handle_disconnect(self):
        """Handle disconnect button click"""
        if not self.client:
            self.show_error("Client not initialized")
            return
            
        try:
            asyncio.create_task(self.client.disconnect())
        except Exception as e:
            self.show_error(str(e))
            
    def _handle_send_message(self):
        """Handle send message button click"""
        if not self.client:
            self.show_error("Client not initialized")
            return
            
        message = self.message_input.text().strip()
        if not message:
            return
            
        try:
            asyncio.create_task(self.client.send_message('chat', {
                'message': message,
                'sender_id': 'Client'
            }))
            self.message_input.clear()
        except Exception as e:
            self.show_error(str(e))
            
    def update_connection_status(self, is_connected: bool):
        """Update connection status"""
        self.connect_button.setEnabled(not is_connected)
        self.disconnect_button.setEnabled(is_connected)
        self.message_input.setEnabled(is_connected)
        self.send_button.setEnabled(is_connected)
        
        if is_connected:
            self.status_label.setText(self.translator.translate('connected'))
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(self.translator.translate('disconnected'))
            self.status_label.setStyleSheet("color: red;")
            
    def show_chat_message(self, sender: str, message: str):
        """Show chat message in the chat display"""
        self.chat_display.append(f"{sender}: {message}")
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        
    def show_error(self, message: str):
        """Show an error message"""
        QMessageBox.critical(self, self.translator.translate('error'), message)

    def _setup_tray(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction(self.translator.translate('show'))
        show_action.triggered.connect(self.show)
        hide_action = tray_menu.addAction(self.translator.translate('hide'))
        hide_action.triggered.connect(self.hide)
        tray_menu.addSeparator()
        exit_action = tray_menu.addAction(self.translator.translate('exit'))
        exit_action.triggered.connect(self._handle_exit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _handle_exit(self):
        """Handle exit action"""
        QApplication.quit()

    def closeEvent(self, event):
        """Handle window close event"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            self.translator.translate('app_title'),
            self.translator.translate('minimized'),
            QSystemTrayIcon.Information,
            2000
        )

    def _process_messages(self):
        """Process messages from the queue"""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                if message['type'] == 'connect':
                    asyncio.create_task(self.client.connect(
                        message['connection_key'],
                        message.get('port', 8765)
                    ))
                elif message['type'] == 'disconnect':
                    asyncio.create_task(self.client.disconnect())
                elif message['type'] == 'chat':
                    asyncio.create_task(self.client.send_chat_message(message['text']))
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def set_client(self, client: 'USBRedirectorClient'):
        """Set the client instance"""
        self.client = client

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(300)
        self._init_ui()

    def _init_ui(self):
        """Initialize settings dialog UI"""
        layout = QVBoxLayout(self)

        # Server settings
        server_group = QWidget()
        server_layout = QVBoxLayout(server_group)
        
        server_layout.addWidget(QLabel("Server Settings:"))
        
        self.server_host = QLineEdit()
        self.server_host.setPlaceholderText("Server Host")
        server_layout.addWidget(self.server_host)
        
        self.server_port = QLineEdit()
        self.server_port.setPlaceholderText("Server Port")
        server_layout.addWidget(self.server_port)
        
        layout.addWidget(server_group)

        # Security settings
        security_group = QWidget()
        security_layout = QVBoxLayout(security_group)
        
        security_layout.addWidget(QLabel("Security Settings:"))
        
        self.stealth_mode = QCheckBox("Enable Stealth Mode")
        security_layout.addWidget(self.stealth_mode)
        
        self.auto_reconnect = QCheckBox("Auto Reconnect")
        security_layout.addWidget(self.auto_reconnect)
        
        layout.addWidget(security_group)

        # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)

    def _save_settings(self):
        """Save settings"""
        try:
            # Implement settings save logic
            self.accept()
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClientGUI()
    window.show()
    sys.exit(app.exec_()) 