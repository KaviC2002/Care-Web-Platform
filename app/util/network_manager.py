from PyQt5.QtCore import QThread, pyqtSignal
import requests

class NetworkManager(QThread):
    """Thread to manage network connectivity checks.

    Inherits from QThread to run network status checks in a separate thread,
    emitting signals to notify when connectivity status changes.
    """
    connectivityChanged = pyqtSignal(bool)

    def run(self):
        """Continuously checks for network connectivity.

        This method runs in a separate thread and emits a signal whenever
        the network connectivity status changes. The check is performed
        every second.
        """
        while True:
            online_status = self.is_online()
            self.connectivityChanged.emit(online_status)
            self.msleep(1000)

    def is_online(self):
        """Checks the internet connectivity status.

        Attempts to send a GET request to a reliable server (Google)
        to determine if the internet connection is available.

        Returns:
            bool: True if online, False otherwise.
        """
        try:
            requests.get("https://www.google.com", timeout=5)
            return True
        except requests.exceptions.RequestException:
            return False
