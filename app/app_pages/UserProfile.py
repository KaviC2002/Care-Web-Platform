from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QTableView, QAbstractItemView, \
    QHeaderView, QTableWidgetItem, QInputDialog, QComboBox
from PyQt5.QtCore import QSettings, pyqtSignal, Qt
import os

from app.databases.conn import OnlineDatabase
from app.util.network_manager import NetworkManager
from app.util.user_database_helper import UserDatabaseHelper
check_network = NetworkManager()
connection = OnlineDatabase()
local_connection = UserDatabaseHelper()


class UserProfile(QWidget):
    """
    A QWidget that represents the user profile interface, allowing users to manage user accounts based on their role
    (admin or regular user).

    This class provides functionality for displaying user information, approving or rejecting users, and handling
    sign-out actions.

    Attributes:
        signOutSignal (pyqtSignal): Signal emitted when the user signs out.
        UserProfile_layout (QVBoxLayout): Layout for organizing widgets in the user profile.
        username (str): The username of the current user.
        database_connection: The database connection for user data management.
    """
    signOutSignal = pyqtSignal()

    def __init__(self, username):
        """
        Initializes the UserProfile widget.

        Args:
            username (str): The username of the logged-in user.
        """
        super().__init__()
        self.UserProfile_layout = QVBoxLayout()
        self.username = username

        # Check if the user is an admin
        if check_network.is_online():
            self.database_connection = connection
            if self.database_connection.check_admin_status(username):
                self.init_admin_view()
            else:
                self.init_user_view()
        else:
            self.database_connection = local_connection
            if self.database_connection.check_admin_status(username):
                self.init_admin_view()
            else:
                self.init_user_view()

    def init_admin_view(self):
        """Initializes the user interface for admin users."""
        # Title label
        title_label = QLabel("User Management")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            margin-bottom: 20px; 
            color: #2C3E50;
        """)
        self.UserProfile_layout.addWidget(title_label)

        self.filterComboBox = QComboBox()
        self.filterComboBox.addItem("All Users")
        self.filterComboBox.addItem("Authorised Users")
        self.filterComboBox.addItem("Unauthorised Users")
        self.filterComboBox.setStyleSheet("""
            font-size: 16px; 
            padding: 10px; 
            margin-bottom: 20px; 
            border: 1px solid #BDC3C7; 
            border-radius: 5px; 
        """)
        self.filterComboBox.currentIndexChanged.connect(self.apply_filter)
        self.UserProfile_layout.addWidget(self.filterComboBox)

        self.userTableModel = QStandardItemModel()
        self.userTableModel.setHorizontalHeaderLabels(
            ["Email Address", "Creation Date", "Username", "Is Authorized", "Is Admin"]
        )
        self.userTableView = QTableView()
        self.userTableView.setModel(self.userTableModel)
        self.userTableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.userTableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.userTableView.setStyleSheet("""
            font-size: 14px; 
            background-color: #ECF0F1; 
            border-radius: 5px; 
            color: black;
        """)
        self.UserProfile_layout.addWidget(self.userTableView)

        self.approveButton = QPushButton("Approve")
        self.rejectButton = QPushButton("Reject")
        self.approveButton.clicked.connect(self.approve_user)
        self.rejectButton.clicked.connect(self.reject_user)

        # Button styles
        self.approveButton.setStyleSheet("""
            background-color: #27AE60; 
            color: white; 
            font-size: 16px; 
            margin: 5px; 
            padding: 10px; 
            border: none; 
            border-radius: 5px; 
        """)
        self.rejectButton.setStyleSheet("""
            background-color: #C0392B; 
            color: white; 
            font-size: 16px; 
            margin: 5px; 
            padding: 10px; 
            border: none; 
            border-radius: 5px; 
        """)

        # Button hover effect
        self.approveButton.setStyleSheet("""
            background-color: #27AE60; 
            color: white; 
            font-size: 16px; 
            margin: 5px; 
            padding: 10px; 
            border: none; 
            border-radius: 5px; 
        """)
        self.rejectButton.setStyleSheet("""
            background-color: #C0392B; 
            color: white; 
            font-size: 16px; 
            margin: 5px; 
            padding: 10px; 
            border: none; 
            border-radius: 5px; 
        """)

        self.UserProfile_layout.addWidget(self.approveButton)
        self.UserProfile_layout.addWidget(self.rejectButton)

        # Sign Out Button
        self.sign_out_button = QPushButton("Sign Out")
        self.sign_out_button.setObjectName("signOutButton")
        self.sign_out_button.setFixedSize(self.sign_out_button.sizeHint().width() + 50,
                                          self.sign_out_button.sizeHint().height() + 10)  # Add padding
        self.sign_out_button.setStyleSheet("""
            background-color: #E67E22; 
            color: white; 
            font-size: 14px; 
            margin: 5px;
            padding: 10px; 
            border: none; 
            border-radius: 5px; 
        """)
        self.UserProfile_layout.addWidget(self.sign_out_button, alignment=Qt.AlignCenter)

        self.sign_out_button.clicked.connect(self.handle_sign_out)

        self.setLayout(self.UserProfile_layout)
        self.apply_filter()  # Load users initially

    def init_user_view(self):
        """Initializes the user interface for regular users."""
        # Initialization code for normal user view (not an admin)
        self.load_stylesheet()
        label = QLabel("User Profile")
        label.setObjectName("profileLabel")
        label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            margin-bottom: 20px; 
            color: #2C3E50;
        """)
        self.UserProfile_layout.addWidget(label)

        # Sign Out Button
        self.sign_out_button = QPushButton("Sign Out")
        self.sign_out_button.setObjectName("signOutButton")
        self.sign_out_button.setFixedSize(self.sign_out_button.sizeHint().width() + 50,
                                          self.sign_out_button.sizeHint().height() + 10)  # Add padding

        self.UserProfile_layout.addWidget(self.sign_out_button, alignment=Qt.AlignCenter)

        self.sign_out_button.clicked.connect(self.handle_sign_out)

        self.setLayout(self.UserProfile_layout)

    def load_user(self, users):
        """
        Loads the user data into the user table model.

        Args:
            users (list): A list of user objects to be displayed in the table.
        """
        all_users = users
        self.userTableModel.clear()
        self.userTableModel.setHorizontalHeaderLabels(
            ["Email Address", "Creation Date", "Username", "Is Authorized", "Is Admin"]
        )
        for user in all_users:
            if not user.is_admin:
                is_authorised = "Yes" if user.is_authorised else "No"
                is_admin = "Yes" if user.is_admin else "No"
                created_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
                self.userTableModel.appendRow(
                    [
                        QStandardItem(user.email),
                        QStandardItem(created_at),
                        QStandardItem(user.username),
                        QStandardItem(is_authorised),
                        QStandardItem(is_admin)
                    ]
                )

    def approve_user(self):
        """Approves the selected user in the user table."""
        selected_row = self.userTableView.currentIndex().row()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a user to approve.")
            return

        email = self.userTableModel.item(selected_row, 0).text()
        self.database_connection.approve_user(email)
        self.apply_filter()

    def reject_user(self):
        """Rejects the selected user in the user table."""
        selected_row = self.userTableView.currentIndex().row()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a user to reject.")
            return

        email = self.userTableModel.item(selected_row, 0).text()
        #password, ok = QInputDialog.getText(self, "Admin Password", "Enter your admin password:", QLineEdit.Password)
        #if ok and password:  # Check if the password was entered
        self.database_connection.reject_user(email)
        self.apply_filter()

    def apply_filter(self):
        """Applies the selected filter to the user list and reloads the user data."""
        current_index = self.filterComboBox.currentIndex()
        all_users = self.database_connection.load_all_users()
        users = []
        if current_index == 0:
            return self.load_user(all_users)
        elif current_index == 1:
            for user in all_users:
                if user.is_authorised:
                    users.append(user)
            self.load_user(users)
        else:
            for user in all_users:
                if not user.is_authorised:
                    users.append(user)
            self.load_user(users)

    def handle_sign_out(self):
        """Handles the sign-out process for the user."""
        confirmation = QMessageBox.question(self, "Confirm Sign Out",
                                            "Are you sure you want to sign out? You will need an internet connection to sign back in.",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if confirmation == QMessageBox.Yes:
            settings = QSettings("YourCompany", "YourApp")
            settings.setValue("loggedIn", False)
            QMessageBox.information(self, "Sign Out", "You have been signed out.")
            self.signOutSignal.emit()

    def load_stylesheet(self):
        """
        Loads the stylesheet from the specified CSS file and applies it to the widget.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'user_profile.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())