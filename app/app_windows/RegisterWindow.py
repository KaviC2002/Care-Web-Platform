import hashlib
import smtplib
import os
from email.mime.text import MIMEText

from PyQt5.QtCore import QTimer, Qt, QSettings
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from app.util.user_database_helper import UserDatabaseHelper
from app.databases import model
from app.databases.conn import OnlineDatabase
from app.util.network_manager import NetworkManager

connection = NetworkManager()
local_user_db = UserDatabaseHelper()

class RegisterWindow(QDialog):
    """
    A dialog window for user registration. This window allows users to
    create a new account by entering their email, username, and password.

    Attributes:
        user_db (UserDatabaseHelper): An instance of the user database helper to interact with local user data.
        layout (QVBoxLayout): The layout for arranging the widgets in the dialog.
        logo_label (QLabel): Displays the application logo.
        email_input (QLineEdit): Input field for the user's email.
        username_input (QLineEdit): Input field for the user's username.
        password_input (QLineEdit): Input field for the user's password.
        confirm_password_input (QLineEdit): Input field for confirming the password.
        confirm_button (QPushButton): Button to confirm registration.
        wifi_label (QLabel): Displays the Wi-Fi connection status icon.
        timer (QTimer): Timer to periodically check the connectivity status.
        settings (QSettings): Application settings to store and retrieve user preferences.
        is_online_database (bool): Flag indicating if the online database is enabled.
    """
    def __init__(self, user_db):
        """
        Initializes the RegisterWindow with the given user database.

        Parameters:
            user_db (UserDatabaseHelper): An instance of UserDatabaseHelper to manage user data.
        """
        super().__init__()

        self.load_stylesheet()

        self.user_db = user_db

        self.setWindowTitle("Register")
        self.setGeometry(100, 100, 1180, 700)
        self.setFixedWidth(1180)
        self.setFixedHeight(700)

        self.layout = QVBoxLayout(self)
        self.layout.addStretch(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.logo_label = QLabel(self)
        self.logo_label.setObjectName("image")
        self.logo_pixmap = QPixmap('app/resources/icons/logo.png')
        self.logo_label.setPixmap(self.logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        self.layout.addSpacing(20)

        self.label = QLabel("Please register", self)
        self.label.setObjectName("title")
        self.layout.addWidget(self.label, alignment=Qt.AlignCenter)

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Email")
        self.email_input.setFixedSize(350, 40)
        self.layout.addWidget(self.email_input, alignment=Qt.AlignCenter)

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedSize(350, 40)
        self.layout.addWidget(self.username_input, alignment=Qt.AlignCenter)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setFixedSize(350, 40)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_input, alignment=Qt.AlignCenter)

        self.confirm_password_input = QLineEdit(self)
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        self.confirm_password_input.setFixedSize(350, 40)
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.confirm_password_input, alignment=Qt.AlignCenter)

        self.layout.addSpacing(20)

        self.confirm_button = QPushButton("Register", self)
        self.confirm_button.setObjectName("register_button")
        self.confirm_button.setFixedSize(250, 50)
        self.layout.addWidget(self.confirm_button, alignment=Qt.AlignCenter)

        self.layout.addSpacing(30)

        # Wifi Icon
        self.wifi_label = QLabel(self)
        self.wifi_label.setFixedSize(30, 30)
        self.update_wifi_icon()
        self.layout.addWidget(self.wifi_label, alignment=Qt.AlignCenter)

        self.layout.addSpacing(50)

        # Timer that checks connectivity every 10 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wifi_icon)
        self.timer.start(10000)

        self.confirm_button.clicked.connect(self.handle_register)
        self.settings = QSettings("YourCompany", "YourApp")
        self.is_online_database = self.settings.value("online_database_enabled")
    
    def load_stylesheet(self):
        """
        Loads the stylesheet for the registration window from a CSS file.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'register_window.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def handle_register(self):
        """
        Handles the registration process when the register button is clicked.
        Validates user input, checks for existing usernames, and adds a new user
        to the appropriate database (local or online).
        """
        email = self.email_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        if not self.is_online_database:
            if username.strip() == "" or password == "" or confirm_password == "" or email.strip() == "":
                QMessageBox.warning(self, "Invalid Input", "Please Enter all fields")

            elif local_user_db.check_username(email):
                QMessageBox.warning(self, "Email already registered", "Email already registered")

            elif password != confirm_password:
                QMessageBox.warning(self, "Passwords", "Passwords do not match")

            else:
                new_user = model.User(email=email, username=username)
                new_user.set_password(password)
                local_user_db.add_user(new_user)
                QMessageBox.information(self, "Success", "Registration successful!")
                self.accept()
        else:
            if not connection.is_online():
                QMessageBox.warning(self, 'No Internet',
                    'You are not connected to the internet. Please connect and try again.')
            else:
                conn = OnlineDatabase()

                if username.strip() == "" or password == "" or confirm_password == "" or email.strip() == "":
                    QMessageBox.warning(self, "Invalid Input", "Please Enter all fields")

                elif conn.check_username(email):
                    QMessageBox.warning(self, "Email already registered", "Email already registered")

                elif password != confirm_password:
                    QMessageBox.warning(self, "Passwords", "Passwords do not match")

                else:
                    new_user = model.User(email=email, username = username)
                    new_user.set_password(password)
                    conn.add_user(new_user)
                    QMessageBox.information(self, "Success", "Registration successful!")
                    self.accept()


    def send_confirmation_email(self, email):
        """
        Sends a confirmation email to the registered user.
        To be implemented further
        Parameters:
            email (str): The email address of the user to send the confirmation email to.
        """
        msg = MIMEText("Thank you for registering.")
        msg['Subject'] = 'Registration Confirmation'
        msg['From'] = 'noreply.carewaiheke@gmail.com'
        msg['To'] = email

        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login('noreply.carewaiheke@gmail.com', '2f=ET:98RgaL')
                server.send_message(msg)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to send confirmation email: {str(e)}")

    """Method that updates wifi icon dependent on connection status"""

    def update_wifi_icon(self):
        """
        Updates the Wi-Fi icon based on the current network connectivity status.
        If the application is online, it displays the online icon; otherwise,
        it displays the offline icon.
        """
        if connection.is_online():
            wifi_icon = QPixmap('app/resources/icons/online-icon.png')
        else:
            wifi_icon = QPixmap('app/resources/icons/offline-icon.png')
        self.wifi_label.setPixmap(wifi_icon.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
