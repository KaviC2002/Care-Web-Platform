import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidget, QStackedWidget, QWidget, QLabel, QVBoxLayout, \
    QSplitter, QListWidgetItem, QPushButton, QMessageBox, QCheckBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSettings, QProcess, QSize
from app.app_pages.HomePage import HomePage
from app.app_pages.UploadPage import UploadPage
from app.app_pages.MapView import MapView
from app.app_pages.DatabasePage import DatabasePage
from app.app_pages.OnlineDatabasePage import OnlineDatabasePage
from app.app_pages.ReIDDatabase import ReIDDatabase
from app.app_pages.UserProfile import UserProfile
from app.util.database_helper import DatabaseHelper
from app.util.network_manager import NetworkManager
from app.databases.conn import OnlineDatabase
from app.util.user_database_helper import UserDatabaseHelper
class MainWindow(QMainWindow):
    """
    Main window for the project CARE application.

    This class initializes the main window, sets up the sidebar,
    manages the navigation between different pages, and handles
    online database connectivity.
    """
    def __init__(self, app):
        """
        Initializes the MainWindow instance.

        Args:
            app: The application instance that provides access to
                 the current user and other application-wide
                 settings.
        """
        super().__init__()
        self.local_db = DatabaseHelper()
        self.local_user_db = UserDatabaseHelper()
        self.app = app
        self.setWindowTitle("project CARE")
        self.setGeometry(100, 100, 1180, 700)

        self.load_stylesheet()

        self.splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(self.splitter)

        self.sidebar_widget = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(10)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("logoLabel")
        self.logo_pixmap = QPixmap('app/resources/icons/logo.png')
        self.logo_label.setPixmap(self.logo_pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.sidebar_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        self.list_widget = QListWidget()
        self.sidebar_layout.addWidget(self.list_widget)

        self.home_icon = QIcon('app/app_pages/resources/home.png')
        self.upload_icon = QIcon('app/app_pages/resources/upload-big-arrow.png')
        self.cloud_icon = QIcon('app/app_pages/resources/cloud-computing.png')
        self.stoat_icon = QIcon('app/app_pages/resources/weasel.png')
        self.map_icon = QIcon('app/app_pages/resources/pin.png')
        self.database_icon = QIcon('app/app_pages/resources/database.png')
        self.user_icon = QIcon('app/app_pages/resources/user.png')
        self.arrow_icon = QIcon('app/app_pages/resources/left-arrow.png')


        self.tab1 = QListWidgetItem(self.home_icon, "Home")
        self.tab2 = QListWidgetItem(self.upload_icon, "Upload")
        self.tab3 = QListWidgetItem(self.map_icon, "Map")
        self.tab4 = QListWidgetItem(self.database_icon, "Local Database")
        self.tab5 = QListWidgetItem(self.cloud_icon, "Online Database")
        self.tab6 = QListWidgetItem(self.stoat_icon, "ReID Database")
        self.tab7 = QListWidgetItem(self.user_icon, "User")
        self.list_widget.addItem(self.tab1)
        self.list_widget.addItem(self.tab2)
        self.list_widget.addItem(self.tab3)
        self.list_widget.addItem(self.tab4)
        self.list_widget.addItem(self.tab5)
        self.list_widget.addItem(self.tab6)
        self.list_widget.addItem(self.tab7)

        self.hide_tabs(["Online Database"], True)

        self.online_database_toggle = QPushButton("Online Database: Off")
        self.online_database_toggle.setCheckable(True)
        self.online_database_toggle.setChecked(self.load_online_database_setting())
        self.online_database_toggle.setObjectName("onlineDatabaseToggle")

        if self.online_database_toggle.isChecked():
            self.online_database_toggle.setText("Online Database: On")
            self.spacer_widget = None
        else:
            self.online_database_toggle.setText("Online Database: Off")
            self.spacer_widget = QListWidgetItem()
            spacer_widget = QWidget()
            spacer_layout = QVBoxLayout(spacer_widget)
            spacer_layout.addStretch()
            self.spacer_widget.setSizeHint(QSize(100, 40))
            self.list_widget.insertItem(7, self.spacer_widget)
            self.list_widget.setItemWidget(self.spacer_widget, spacer_widget)

        self.online_database_toggle.clicked.connect(self.toggle_online_database)

        def add_spacer_item(size=40):
            spacer_item = QListWidgetItem()
            spacer_widget = QWidget()
            spacer_layout = QVBoxLayout(spacer_widget)
            spacer_layout.addStretch()
            spacer_item.setSizeHint(QSize(100, size))
            self.list_widget.addItem(spacer_item)
            self.list_widget.setItemWidget(spacer_item, spacer_widget)

        add_spacer_item(size = 155)

        sync_button_widget = QWidget()
        sync_button_layout = QVBoxLayout(sync_button_widget)
        sync_button_layout.setContentsMargins(0, 0, 0, 0)

        self.last_synced_label = QLabel("Check Sync")
        self.last_synced_label.setObjectName("sync_status_label")
        sync_button_layout.addWidget(self.last_synced_label)

        self.check_data_sync_button = QPushButton("Check Data Sync")
        self.check_data_sync_button.setObjectName("main_sync_button")
        self.check_data_sync_button.setMinimumSize(150, 40)
        self.check_data_sync_button.clicked.connect(self.check_unsynced_photos)
        sync_button_layout.addWidget(self.check_data_sync_button)


        self.network_status_label = QLabel("Checking connectivity...")
        self.network_status_label.setObjectName("network_status_label")
        sync_button_layout.addWidget(self.network_status_label)

        sync_button_item = QListWidgetItem()
        sync_button_item.setSizeHint(sync_button_widget.sizeHint())
        self.list_widget.addItem(sync_button_item)
        self.list_widget.setItemWidget(sync_button_item, sync_button_widget)
        add_spacer_item(size=15)

        checkbox_item = QListWidgetItem()
        checkbox_item.setSizeHint(self.online_database_toggle.sizeHint())
        self.list_widget.addItem(checkbox_item)
        self.list_widget.setItemWidget(checkbox_item, self.online_database_toggle)

        self.splitter.addWidget(self.sidebar_widget)
        self.sidebar_widget.setFixedWidth(200)

        self.stacked_widget = QStackedWidget()
        self.splitter.addWidget(self.stacked_widget)

        self.HomePage = HomePage(self)
        self.MapView = MapView()
        self.ReIDPage = ReIDDatabase()
        self.DatabasePage = DatabasePage(self.ReIDPage)
        self.UploadPage = UploadPage(self.app.current_user, self.DatabasePage)
        self.UserProfile = UserProfile(self.app.current_user)

        self.UploadPage.images_saved_signal.connect(self.DatabasePage.refresh_tree)

        self.UserProfile.signOutSignal.connect(self.handle_sign_out)

        self.stacked_widget.addWidget(self.HomePage)
        self.stacked_widget.addWidget(self.UploadPage)
        self.stacked_widget.addWidget(self.MapView)
        self.stacked_widget.addWidget(self.DatabasePage)
        self.stacked_widget.addWidget(self.ReIDPage)
        self.stacked_widget.addWidget(self.UserProfile)

        self.page_map = {
            "Home": self.HomePage,
            "Upload": self.UploadPage,
            "Map": self.MapView,
            "Local Database": self.DatabasePage,
            "Online Database": None,
            "ReID Database": self.ReIDPage,
            "User": self.UserProfile
        }

        self.list_widget.currentItemChanged.connect(self.switch_page)

        self.splitter.setSizes([150, 650])

        self.network_manager = NetworkManager()
        self.network_manager.connectivityChanged.connect(self.update_connectivity_status)
        self.network_manager.start()

    def load_stylesheet(self):
        """Load the stylesheet for the main window."""
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'main_window.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def hide_tabs(self, labels, status):
        """Hide or show tabs in the list widget based on the label.

        Args:
            labels: List of tab labels to hide or show.
            status: Boolean value to set visibility.
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text() in labels:
                item.setHidden(status)

    def update_connectivity_status(self, is_online):
        """
        Updates the connectivity status label and manages the visibility of the
        Online Database tab based on the internet connection status.

        Args:
            is_online (bool): Indicates if the application is connected to the internet.
        """
        if is_online:
            self.network_status_label.setText("Connected to the internet.")
            if self.online_database_toggle.isChecked():
                self.hide_tabs(["Online Database"], False)
                if not hasattr(self, 'OnlineDatabasePage'):
                    self.OnlineDatabasePage = OnlineDatabasePage(self.app.current_user, self.DatabasePage)
                    self.stacked_widget.insertWidget(4, self.OnlineDatabasePage)
                    self.page_map["Online Database"] = self.OnlineDatabasePage
        else:
            self.network_status_label.setText("No internet connection.")
            self.hide_tabs(["Online Database"], True)

    def toggle_online_database(self, state):
        """
        Toggles the Online Database feature on or off, updating the settings and UI
        accordingly. It syncs users if the feature is enabled and the internet is
        connected.

        Args:
            state (bool): Indicates the desired state of the Online Database toggle.
        """
        settings = QSettings("YourCompany", "YourApp")
        settings.setValue("online_database_enabled", state == self.online_database_toggle.isChecked())

        if self.online_database_toggle.isChecked():
            self.online_database_toggle.setText("Online Database: On")
            settings = QSettings("YourCompany", "YourApp")
            settings.setValue("online_database_enabled", True)
            QMessageBox.information(self, "Online Database", "Online Database enabled.")
            if self.network_manager.is_online():
                self.sync_users()
                if not hasattr(self, 'OnlineDatabasePage'):
                    self.OnlineDatabasePage = OnlineDatabasePage(self.app.current_user, self.DatabasePage)
                    self.stacked_widget.insertWidget(4, self.OnlineDatabasePage)
                    self.page_map["Online Database"] = self.OnlineDatabasePage

                if self.spacer_widget is not None:
                    self.list_widget.takeItem(self.list_widget.row(self.spacer_widget))
                    self.spacer_widget = None
        else:
            self.online_database_toggle.setText("Online Database: Off")
            QMessageBox.information(self, "Online Database", "Online Database disabled.")
            settings = QSettings("YourCompany", "YourApp")
            settings.setValue("online_database_enabled", False)
            self.hide_tabs(["Online Database"], True)
            if self.network_manager.is_online():
                self.sync_online_users()
            if hasattr(self, 'OnlineDatabasePage'):
                self.stacked_widget.removeWidget(self.OnlineDatabasePage)
                del self.OnlineDatabasePage

            if self.spacer_widget is None:
                self.spacer_widget = QListWidgetItem()
                spacer_widget = QWidget()
                spacer_layout = QVBoxLayout(spacer_widget)
                spacer_layout.addStretch()
                self.spacer_widget.setSizeHint(QSize(100, 40))
                self.list_widget.insertItem(7, self.spacer_widget)
                self.list_widget.setItemWidget(self.spacer_widget, spacer_widget)

    def load_online_database_setting(self):
        """
        Loads the current setting for the Online Database feature from the application
        settings.

        Returns:
            bool: True if the Online Database is enabled, False otherwise.
        """
        settings = QSettings("YourCompany", "YourApp")
        return settings.value("online_database_enabled", False, type=bool)

    def handle_sign_out(self):
        """
        Handles the sign-out process for the user, updating the application settings
        to reflect that the user is no longer logged in.
        """
        settings = QSettings("YourCompany", "YourApp")
        settings.setValue("loggedIn", False)
        self.app.handle_sign_out()

    def check_unsynced_photos(self):
        """
        Checks for unsynced photos in the local database and displays a message box
        indicating the count of unsynced photos. Also calls to check the last synced status.
        """
        unsynced_count = self.local_db.fetch_unsynced_image_count()
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"{unsynced_count} photo(s) have not been synced.")
        msg.setWindowTitle("Data Sync Status")
        msg.exec_()
        self.check_last_synced_status()

    def check_last_synced_status(self):
        """
        Checks the last synced status for the current user. If online, retrieves the
        last synced time and updates the label accordingly.
        """
        connection = NetworkManager()
        if connection.is_online():
            conn = OnlineDatabase()
            last_synced = conn.get_status(self.app.current_user)
            if last_synced:
                self.last_synced_label.setText(f"Last Synced: {last_synced}")
            else:
                self.last_synced_label.setText("Has not been Synced")

    def switch_page(self, current_item, previous_item):
        """
        Switches to the corresponding page in the stacked widget when an item in the
        list is clicked.

        Args:
            current_item (QListWidgetItem): The currently selected item.
            previous_item (QListWidgetItem): The previously selected item.
        """
        if current_item is None:
            return

        page = self.page_map.get(current_item.text())

        if page is not None:
            self.stacked_widget.setCurrentWidget(page)


    def sync_users(self):
        """
        Syncs all user accounts with the online database if the connection is active.
        """
        connection = NetworkManager()
        if connection.is_online():
            conn = OnlineDatabase()
            conn.sync_all_user_accounts()

    def sync_online_users(self):
        """
        Syncs users from the online database to the local database if the connection is
        active.
        """
        local_user_db = UserDatabaseHelper()
        connection = NetworkManager()
        if connection.is_online():
            conn = OnlineDatabase()
            all_online_users = conn.get_all_users()
            local_user_db.sync_user(all_online_users)
