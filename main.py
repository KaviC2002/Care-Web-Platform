import os
import sys

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QDialog, QSplashScreen
from PyQt5.QtCore import QSettings, Qt, QTimer
from app.app_windows.MainWindow import MainWindow
from app.app_windows.LoginWindow import LoginWindow
from app.util.user_database_helper import UserDatabaseHelper

class MyApp(QApplication):
    """Main application class for the user interface.

        This class initializes the application, manages user authentication,
        and handles the display of different windows (main and login).
        """
    def __init__(self, argv):
        """Initializes the MyApp instance.

        Args:
            argv (list): The list of command line arguments.
        """
        super().__init__(argv)
        self.main_window = None
        self.login_window = None
        self.settings = QSettings("YourCompany", "YourApp")
        self.user_db = UserDatabaseHelper()
        self.current_user = None
        is_online = self.settings.value("online_database_enabled")
        print(is_online)
        self.splash = None

    def show_main_window(self):
        """Displays the main application window."""
        self.main_window = MainWindow(self)
        self.main_window.show()

    def close_main_window(self):
        """Closes the main application window."""
        self.main_window.close()
        self.main_window = None

    def show_login_window(self):
        """Displays the login window and handles user login."""
        self.login_window = LoginWindow(self.user_db)
        if self.login_window.exec_() == QDialog.Accepted:
            self.settings.setValue("loggedIn", True)
            self.current_user = self.login_window.currentUser
            self.settings.setValue("currentUser", self.current_user)
            self.show_main_window()


    def handle_sign_out(self):
        """Handles user sign-out process."""
        self.current_user = None
        self.settings.setValue("loggedIn", False)
        self.settings.remove("currentUser")
        #self.settings.clear()  # Clears all settings to start fresh
        self.settings.sync()
        self.close_main_window()
        self.show_login_window()

    def load_user(self):
        """Checks to see if user is logged in retrieves user email"""
        is_logged_in = self.settings.value("loggedIn", False)
        if is_logged_in:
            saved_username = self.settings.value("currentUser", None)
            if saved_username:
                self.current_user = str(saved_username)
                return True
        return False

    def show_splash_screen(self):
        """Displays the splash screen while the application loads."""
        splash_image_path = os.path.abspath("app/resources/icons/Logo.png")
        print(f"Loading splash image from: {splash_image_path}")
        splash_image = QPixmap(splash_image_path)

        if splash_image.isNull():
            return
        self.splash = QSplashScreen(splash_image, Qt.WindowStaysOnTopHint)
        self.splash.show()
        self.processEvents()

    def hide_splash_screen(self):
        """Hides the splash screen when the application loads."""
        if self.splash:
            self.splash.close()


def main():
    """Main entry point for the application."""
    app = MyApp(sys.argv)
    app.show_splash_screen()
    QTimer.singleShot(2000, lambda: initialize_app(app))
    sys.exit(app.exec_())

def initialize_app(app):
    """Initializes the application by checking user login status.

    Args:
        app (MyApp): The instance of the MyApp application.
    """
    if app.load_user():
        app.show_main_window()
    else:
        print(app.current_user)
        app.show_login_window()

    app.hide_splash_screen()


if __name__ == "__main__":
    main()

