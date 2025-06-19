import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QListWidget,
    QStatusBar, QSystemTrayIcon, QMenu, QAction,
    QMessageBox, QDialog, QLineEdit, QCheckBox,
    QTabWidget, QTableWidget, QTableWidgetItem,
    QGroupBox, QSpinBox, QHeaderView, QStyle, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QColor
import logging
import json
import asyncio
import threading
from common.translator import Translator

logger = logging.getLogger('ServerGUI')

class ConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("الاتصال بالعميل")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Connection Info Group
        info_group = QGroupBox("معلومات الاتصال")
        info_layout = QVBoxLayout()

        # Connection Key
        key_layout = QHBoxLayout()
        self.key_label = QLabel("مفتاح الاتصال:")
        self.key_input = QLineEdit()
        key_layout.addWidget(self.key_label)
        key_layout.addWidget(self.key_input)
        info_layout.addLayout(key_layout)

        # Port
        port_layout = QHBoxLayout()
        self.port_label = QLabel("المنفذ:")
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8765)
        port_layout.addWidget(self.port_label)
        port_layout.addWidget(self.port_input)
        info_layout.addLayout(port_layout)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Buttons
        button_layout = QHBoxLayout()
        connect_button = QPushButton("اتصال")
        connect_button.clicked.connect(self._connect)
        button_layout.addWidget(connect_button)
        
        cancel_button = QPushButton("إلغاء")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)

    def _connect(self):
        """Connect using provided information"""
        if not self.key_input.text():
            QMessageBox.warning(self, "خطأ", "الرجاء إدخال مفتاح الاتصال")
            return
        
        self.accept()

class ServerGUI(QMainWindow):
    def __init__(self, translator: Translator):
        super().__init__()
        self.translator = translator
        self.server = None
        self.setWindowTitle(self.translator.translate('server_title'))
        self.setMinimumSize(800, 600)
        self.connected_clients = {}  # Store connected clients
        
        # Check for required dependencies
        try:
            import websockets
            import asyncio
            import ssl
            from cryptography.fernet import Fernet
        except ImportError as e:
            QMessageBox.critical(self, self.translator.translate('error'),
                               f"Missing required dependencies: {str(e)}\nPlease install all requirements using: pip install -r requirements.txt")
            raise
        except Exception as e:
            logger.error(f"Error initializing server GUI: {e}")
            QMessageBox.critical(self, self.translator.translate('error'),
                               f"Error initializing server: {str(e)}")
            raise
            
        # Initialize UI
        self._init_ui()
        self._setup_tray()

    def _init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Server Status Group
        status_group = QGroupBox(self.translator.translate('server_status'))
        status_layout = QHBoxLayout()
        
        # Status Indicator
        status_indicator_layout = QHBoxLayout()
        self.status_label = QLabel(self.translator.translate('status'))
        self.status_value = QLabel(self.translator.translate('stopped'))
        self.status_value.setStyleSheet("color: red;")
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
        status_indicator_layout.addWidget(self.status_label)
        status_indicator_layout.addWidget(self.status_value)
        status_indicator_layout.addWidget(self.status_indicator)
        status_layout.addLayout(status_indicator_layout)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Server Control Group
        control_group = QGroupBox(self.translator.translate('server_control'))
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton(self.translator.translate('start_server'))
        self.stop_button = QPushButton(self.translator.translate('stop_server'))
        self.stop_button.setEnabled(False)
        
        self.start_button.clicked.connect(self._handle_start_server)
        self.stop_button.clicked.connect(self._handle_stop_server)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Connection Info Group
        info_group = QGroupBox(self.translator.translate('connection_info'))
        info_layout = QVBoxLayout()

        # Local IP Address
        local_ip_layout = QHBoxLayout()
        self.local_ip_label = QLabel("Local IP:")
        self.local_ip_value = QLabel("--")
        self.copy_local_ip_btn = QPushButton(self.translator.translate('copy'))
        self.copy_local_ip_btn.clicked.connect(lambda: self._handle_copy_ip(self.local_ip_value.text()))
        self.copy_local_ip_btn.setEnabled(False)
        local_ip_layout.addWidget(self.local_ip_label)
        local_ip_layout.addWidget(self.local_ip_value)
        local_ip_layout.addWidget(self.copy_local_ip_btn)
        info_layout.addLayout(local_ip_layout)

        # WAN IP Address
        wan_ip_layout = QHBoxLayout()
        self.wan_ip_label = QLabel("WAN IP:")
        self.wan_ip_value = QLabel("--")
        self.copy_wan_ip_btn = QPushButton(self.translator.translate('copy'))
        self.copy_wan_ip_btn.clicked.connect(lambda: self._handle_copy_ip(self.wan_ip_value.text()))
        self.copy_wan_ip_btn.setEnabled(False)
        wan_ip_layout.addWidget(self.wan_ip_label)
        wan_ip_layout.addWidget(self.wan_ip_value)
        wan_ip_layout.addWidget(self.copy_wan_ip_btn)
        info_layout.addLayout(wan_ip_layout)

        # Port
        port_layout = QHBoxLayout()
        self.port_label = QLabel(self.translator.translate('port') + ":")
        self.port_value = QLabel("--")
        self.copy_port_btn = QPushButton(self.translator.translate('copy'))
        self.copy_port_btn.clicked.connect(self._handle_copy_port)
        self.copy_port_btn.setEnabled(False)
        port_layout.addWidget(self.port_label)
        port_layout.addWidget(self.port_value)
        port_layout.addWidget(self.copy_port_btn)
        info_layout.addLayout(port_layout)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Chat Group
        chat_group = QGroupBox(self.translator.translate('chat'))
        chat_layout = QVBoxLayout()

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(self.chat_display)

        # Chat input
        chat_input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(self.translator.translate('type_message'))
        self.chat_input.returnPressed.connect(self._handle_send_message)
        
        self.send_message_btn = QPushButton(self.translator.translate('send'))
        self.send_message_btn.clicked.connect(self._handle_send_message)
        self.send_message_btn.setEnabled(False)
        
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.send_message_btn)
        chat_layout.addLayout(chat_input_layout)

        chat_group.setLayout(chat_layout)
        layout.addWidget(chat_group)

        # Connected Clients Group
        clients_group = QGroupBox(self.translator.translate('connected_clients'))
        clients_layout = QVBoxLayout()
        
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(2)
        self.clients_table.setHorizontalHeaderLabels([
            self.translator.translate('client_id'),
            self.translator.translate('status')
        ])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        clients_layout.addWidget(self.clients_table)
        
        clients_group.setLayout(clients_layout)
        layout.addWidget(clients_group)

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
        start_action = tray_menu.addAction(self.translator.translate('start_server'))
        start_action.triggered.connect(self._handle_start_server)
        stop_action = tray_menu.addAction(self.translator.translate('stop_server'))
        stop_action.triggered.connect(self._handle_stop_server)
        tray_menu.addSeparator()
        exit_action = tray_menu.addAction(self.translator.translate('exit'))
        exit_action.triggered.connect(self._handle_exit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _handle_start_server(self):
        """Handle start server button click"""
        try:
            if not self.server:
                from server.main import USBRedirectorServer
                self.server = USBRedirectorServer(self, self.translator)
            
            # Create event loop in a separate thread
            def run_server():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Start the server
                    loop.run_until_complete(self.server.start())
                    # Keep the event loop running
                    loop.run_forever()
                except Exception as e:
                    logger.error(f"Error starting server: {e}")
                    self.update_server_status(False)
                    self.show_error(f"Error starting server: {str(e)}")
                finally:
                    loop.close()
            
            # Start server in a separate thread
            server_thread = threading.Thread(target=run_server)
            server_thread.daemon = True
            server_thread.start()
            
            # Update UI
            self.update_server_status(True)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            self.update_server_status(False)
            self.show_error(f"Error starting server: {str(e)}")

    def _handle_stop_server(self):
        """Handle stop server button click"""
        try:
            if not self.server:
                return
            
            def stop_server():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.server.stop_server())
                except Exception as e:
                    logger.error(f"Error stopping server: {e}")
                    self.show_error(f"Error stopping server: {str(e)}")
            
            thread = threading.Thread(target=stop_server)
            thread.daemon = True
            thread.start()
            
            # Update UI
            self.update_server_status(False)
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.send_message_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            self.update_server_status(False)
            self.show_error(f"Error stopping server: {str(e)}")

    def _handle_copy_ip(self, ip: str):
        """Handle copy IP button click"""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(ip)
        QMessageBox.information(self, self.translator.translate('success'),
                              "IP address copied to clipboard")

    def _handle_copy_port(self):
        """Handle copy port button click"""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.port_value.text())
        QMessageBox.information(self, self.translator.translate('success'),
                              "Port number copied to clipboard")

    def _handle_send_message(self):
        """Handle send message button click"""
        if not self.server:
            self.show_error("Server not initialized")
            return
            
        message = self.chat_input.text().strip()
        if not message:
            return
            
        try:
            # Send message to all connected clients
            for client_id in self.server.clients:
                asyncio.create_task(self.server.send_message(client_id, 'chat', {
                    'message': message,
                    'sender_id': 'Technician'
                }))
            self.chat_input.clear()
        except Exception as e:
            self.show_error(str(e))

    def show_chat_message(self, sender: str, message: str):
        """Show chat message in the chat display"""
        self.chat_display.append(f"{sender}: {message}")
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def add_client(self, client_id: str):
        """Add client to the table"""
        row = self.clients_table.rowCount()
        self.clients_table.insertRow(row)
        
        self.clients_table.setItem(row, 0, QTableWidgetItem(client_id))
        self.clients_table.setItem(row, 1, QTableWidgetItem(self.translator.translate('connected')))
        
        self.connected_clients[client_id] = {
            'status': 'connected'
        }
        
        # Enable chat functionality
        self.send_message_btn.setEnabled(True)
        
        # Show notification
        QMessageBox.information(self, self.translator.translate('new_connection'),
                              f"New client connected: {client_id}")

    def remove_client(self, client_id: str):
        """Remove client from the table"""
        for row in range(self.clients_table.rowCount()):
            if self.clients_table.item(row, 0).text() == client_id:
                self.clients_table.removeRow(row)
                if client_id in self.connected_clients:
                    del self.connected_clients[client_id]
                break
        
        # Disable chat if no clients
        if self.clients_table.rowCount() == 0:
            self.send_message_btn.setEnabled(False)

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

    def _handle_exit(self):
        """Handle exit action"""
        QApplication.quit()

    def update_server_status(self, running: bool, ip: str = None, port: int = None):
        """Update server status display"""
        if running:
            self.status_value.setText(self.translator.translate('running'))
            self.status_value.setStyleSheet("color: green;")
            self.status_indicator.setStyleSheet("background-color: green; border-radius: 10px;")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.send_message_btn.setEnabled(True)
            
            if ip:
                self.wan_ip_value.setText(ip)
                self.copy_wan_ip_btn.setEnabled(True)
            if port:
                self.port_value.setText(str(port))
                self.copy_port_btn.setEnabled(True)
            else:
                # Set default port if not provided
                self.port_value.setText("8765")
                self.copy_port_btn.setEnabled(True)
        else:
            self.status_value.setText(self.translator.translate('stopped'))
            self.status_value.setStyleSheet("color: red;")
            self.status_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.send_message_btn.setEnabled(False)
            self.copy_wan_ip_btn.setEnabled(False)
            self.copy_port_btn.setEnabled(False)
            self.port_value.setText("--")

    def show_error(self, message: str):
        QMessageBox.critical(self, self.translator.translate('error'), message)

    def update_connection_info(self, ip: str, port: str):
        """Update the connection info display"""
        self.wan_ip_value.setText(ip)
        self.port_value.setText(str(port))
        self.copy_wan_ip_btn.setEnabled(ip != "--")
        self.copy_port_btn.setEnabled(port != "--")

    def update_client_list(self, clients: list):
        """Update client list display"""
        self.client_list.clear()
        for client_id in clients:
            self.client_list.addItem(client_id)

    def update_device_list(self, devices: dict):
        """Update device list display"""
        self.device_list.clear()
        for client_id, client_devices in devices.items():
            for device in client_devices:
                item = QListWidgetItem(f"{client_id} - {device['name']} ({device['status']})")
                item.setData(Qt.UserRole, {'client_id': client_id, 'device_id': device['id']})
                self.device_list.addItem(item)

    def update_wan_ip(self, ip: str):
        """Update WAN IP display"""
        self.wan_ip_value.setText(ip)
        self.copy_wan_ip_btn.setEnabled(ip != "--")

    def update_local_ip(self, ip: str):
        """Update local IP display"""
        self.local_ip_value.setText(ip)
        self.copy_local_ip_btn.setEnabled(ip != "--")

    def update_client_status(self, client_id: str, status: str):
        """Update client status in the table"""
        for row in range(self.clients_table.rowCount()):
            if self.clients_table.item(row, 0).text() == client_id:
                self.clients_table.setItem(row, 1, QTableWidgetItem(status))
                break

    def update_client_devices(self, client_id: str, device_count: int):
        """Update client device count"""
        for row in range(self.clients_table.rowCount()):
            if self.clients_table.item(row, 0).text() == client_id:
                self.clients_table.setItem(row, 1, QTableWidgetItem(f"Connected ({device_count} devices)"))
                break

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ServerGUI()
    window.show()
    sys.exit(app.exec_()) 