
import os
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from app.util.network_manager import NetworkManager

class HomePage(QWidget):
    def __init__(self, main_window):
        """Initialize the HomePage with the main window and network manager.

        Args:
            main_window (QMainWindow): The main application window.
        """
        super().__init__()
        self.main_window = main_window
        self.buttons = {}

        self.network_manager = NetworkManager()
        self.network_manager.connectivityChanged.connect(self.update_button_visibility)
        self.network_manager.start()

        self.initUI()

    def initUI(self):
        """Set up the user interface for the HomePage."""
        self.load_stylesheet()

        layout = QVBoxLayout(self)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("content_widget")
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setSpacing(10)

        self.content_widget.setMaximumWidth(980)

        self.banner_label = QLabel(self)
        banner_pixmap = QPixmap("app/app_pages/resources/Te-Korowai-O-Waiheke_Web-banner_940x2500px-Standard.png")
        self.banner_label.setPixmap(banner_pixmap.scaled(880, 400, Qt.KeepAspectRatio))
        self.banner_label.setScaledContents(True)
        content_layout.addWidget(self.banner_label, alignment=Qt.AlignCenter)

        self.banner_text = QLabel("Te Korowai o Waiheke")
        self.banner_text.setObjectName("banner_text")
        content_layout.addWidget(self.banner_text, alignment=Qt.AlignCenter)

        button_layout = QHBoxLayout()
        button_names = {
            "Upload": "UploadPage",
            "Local Database": "LocalDatabasePage",
            "Online Database": "OnlineDatabasePage",
            "ReID Database": "ReIDDatabase"
        }

        for name, list_text in button_names.items():
            button = QPushButton(name)
            button.setObjectName(f"{name.lower()}_button")
            button.setFixedSize(175, 60)
            button.clicked.connect(lambda checked, page=name: self.switch_to_page(page))
            button_layout.addWidget(button)
            
            if name in ["Online Database", "Map"]:
                self.buttons[name] = button

        content_layout.addLayout(button_layout)

        middle_title = QLabel("Making Waiheke Island the world’s first predator-free urban island")
        middle_title.setObjectName("middle_title")
        content_layout.addWidget(middle_title, alignment=Qt.AlignCenter)

    def load_stylesheet(self):
        """Load Stylesheet"""
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'home_page.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())
    
    def switch_to_page(self, page_name):
        """Switch to the corresponding page in the main window."""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            if item.text() == page_name:
                self.main_window.list_widget.setCurrentItem(item)
                break
    
    def update_button_visibility(self, is_online):
        """Show or hide buttons based on the online status."""
        if "Online Database" in self.buttons:
            self.buttons["Online Database"].setVisible(is_online)
