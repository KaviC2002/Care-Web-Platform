import socket

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QSettings
from app.app_windows.RegisterWindow import RegisterWindow
import os
from app.databases.conn import OnlineDatabase
from app.util.network_manager import NetworkManager
from app.util.user_database_helper import UserDatabaseHelper

local_user_db = UserDatabaseHelper()

connection = NetworkManager()

class LoginWindow(QDialog):
    """
    A dialog window for user login.

    This class represents the login interface of the application, allowing users to
    enter their email and password to access their accounts. It supports both local
    and online user authentication and includes visual elements for branding and
    connectivity status.

    Attributes:
        user_db (UserDatabaseHelper): Instance of UserDatabaseHelper for local user database operations.
        currentUser (str): The email of the currently logged-in user.
        settings (QSettings): Settings object for reading application configurations.
        is_online_database (bool): Flag indicating if the online database is enabled.
    """

    def __init__(self, user_db):
        """
        Initializes the LoginWindow.

        Args:
            user_db (UserDatabaseHelper): An instance of UserDatabaseHelper for user database operations.

        Raises:
            Exception: If there is an issue with loading the stylesheet or initializing components.
        """

        super().__init__()

        self.load_stylesheet()
        self.currentUser = None
        self.user_db = user_db

        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 1180, 700)
        self.setFixedWidth(1180)
        self.setFixedHeight(700)

        self.layout = QVBoxLayout(self)
        self.layout.addStretch(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Logo at the top
        self.logo_label = QLabel(self)
        self.logo_label.setObjectName("image")
        self.logo_pixmap = QPixmap('app/resources/icons/logo.png')
        self.logo_label.setPixmap(self.logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        self.layout.addSpacing(20)

        # Title
        self.label = QLabel("Welcome to CARE", self)
        self.label.setObjectName("title")
        self.layout.addWidget(self.label, alignment=Qt.AlignCenter)

        # Subtitle
        self.sub_label = QLabel("Enter your email and password to access your account", self)
        self.sub_label.setObjectName("sub_heading")
        self.layout.addWidget(self.sub_label, alignment=Qt.AlignCenter)

        self.layout.addSpacing(30)

        # Username input
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Email")
        self.username_input.setFixedSize(350, 40)
        self.layout.addWidget(self.username_input, alignment=Qt.AlignCenter)

        # Password input
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setFixedSize(350, 40)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_input, alignment=Qt.AlignCenter)

        self.layout.addSpacing(30)

        # Login button
        self.login_button = QPushButton("Login", self)
        self.login_button.setObjectName("login_button")
        self.login_button.setFixedSize(250, 50)
        self.layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        self.layout.addSpacing(10)

        # Register button
        self.register_button = QPushButton("Register", self)
        self.register_button.setObjectName("register_button")
        self.register_button.setFixedSize(250, 50)
        self.layout.addWidget(self.register_button, alignment=Qt.AlignCenter)

        self.layout.addSpacing(20)

        # Wifi Icon
        self.wifi_label = QLabel(self)
        self.wifi_label.setFixedSize(30,30)
        self.update_wifi_icon()
        self.layout.addWidget(self.wifi_label, alignment=Qt.AlignCenter)

        self.layout.addSpacing(50)

        # Timer for connectivity checks
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wifi_icon)
        self.timer.start(10000)

        self.login_button.clicked.connect(self.handle_login)
        self.register_button.clicked.connect(self.open_register_window)
        self.settings = QSettings("YourCompany", "YourApp")
        self.is_online_database = self.settings.value("online_database_enabled")

    def load_stylesheet(self):
        """
        Loads the stylesheet from the specified CSS file and applies it to the dialog.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'login_window.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def handle_login(self):
        """
        Handles user login logic.

        This method retrieves the username and password from the input fields and checks
        the credentials against the local user database or online database, depending on
        the application's configuration. It displays appropriate message boxes for success
        or failure of the login attempt.

        Raises:
            Exception: If there is an issue during the login process.
        """

        username = self.username_input.text()
        password = self.password_input.text()
        if not self.is_online_database:
            local_user_db.login(username, password)
            user = local_user_db.get_user(username)
            if user:
                if not user.is_authorised:
                    QMessageBox.warning(self, 'Login Failed', 'You are not authorised. Ask admin for authorisation.')
                elif user.check_password(password):
                    QMessageBox.information(self, 'Login Success', f'Welcome, {username}')
                    self.currentUser = user.email
                    self.accept()
                else:
                    QMessageBox.warning(self, 'Login Failed', 'Incorrect username or password.')
            else:
                QMessageBox.warning(self, 'Login Failed', 'User does not exist.')
        else:
            if not connection.is_online():
                QMessageBox.warning(self, 'No Internet',
                'You are not connected to the internet. Please connect and try again.')

            else:
                conn = OnlineDatabase()
                user = conn.get_user(username)

                if user:
                    if not user.is_authorised:
                        QMessageBox.warning(self, 'Login Failed', 'You are not authorised. Ask admin for authorisation.')
                    elif user.check_password(password):
                        QMessageBox.information(self, 'Login Success', f'Welcome, {username}')
                        self.currentUser = user.email
                        self.accept()
                    else:
                        QMessageBox.warning(self, 'Login Failed', 'Incorrect username or password.')
                else:
                    QMessageBox.warning(self, 'Login Failed', 'User does not exist.')


        '''user = self.user_db.get_user(username)

        if user and user[3] == hash_password(password):
            QMessageBox.information(self, "Success", "Login successful!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Incorrect username or password")'''

    def open_register_window(self):
        """
        Opens the registration dialog.

        This method creates an instance of the RegisterWindow dialog and displays it to
        the user. If the registration is successful, a confirmation message box is shown.

        Raises:
            Exception: If there is an issue opening the registration window.
        """
        register_dialog = RegisterWindow(self.user_db)
        if register_dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Registration", "You have successfully registered!")

    """Method that updates wifi icon dependent on connection status"""
    def update_wifi_icon(self):
        """
        Updates the wifi icon based on the connection status.

        This method checks the current network status and updates the wifi icon displayed
        in the dialog accordingly. If the application is online, an online icon is shown;
        otherwise, an offline icon is displayed.
        """
        if connection.is_online():
            wifi_icon = QPixmap('app/resources/icons/online-icon.png')
        else:
            wifi_icon = QPixmap('app/resources/icons/offline-icon.png')
        self.wifi_label.setPixmap(wifi_icon.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
