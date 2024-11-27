from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGraphicsView, 
                             QGraphicsScene, QScrollArea, QPushButton, QGraphicsPixmapItem, 
                             QGraphicsEllipseItem, QGraphicsItem, QDialog, QGridLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor
import os

class MapPopup(QDialog):
    """
    A dialog for selecting a location on a map image.

    This dialog displays a map image and allows the user to zoom in and out,
    as well as select a specific location by clicking on the map. The selected
    location can be confirmed and emitted via a signal.

    Attributes:
        location_selected_signal (pyqtSignal): Signal emitted when a location is confirmed.
        group_name (str): The name of the group associated with the map.
        current_scale (float): Current zoom scale of the map.
        min_scale (float): Minimum zoom scale.
        max_scale (float): Maximum zoom scale.
        selected_location (tuple): The (x, y) coordinates of the selected location on the map.
        pin_item (QGraphicsPixmapItem): The graphical item representing the pin on the map.
    """
    location_selected_signal = pyqtSignal(tuple)

    def __init__(self, group_name):
        """
        Initializes the MapPopup dialog.

        :param group_name: The name of the group associated with the map.
        """
        super().__init__()

        self.group_name = group_name

        self.load_stylesheet()

        self.setWindowTitle("Select Image Location on Map")
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout(self)

        group_label = QLabel(f"{self.group_name}")
        group_label.setAlignment(Qt.AlignCenter)
        group_label.setObjectName("groupLabel")
        self.layout.addWidget(group_label)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.view)

        self.map_image = QPixmap(os.path.join(os.path.dirname(__file__), 'resources', 'waihekemap.png'))
        self.map_item = QGraphicsPixmapItem(self.map_image)
        self.scene.addItem(self.map_item)

        zoom_buttons_layout = QHBoxLayout()

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.setObjectName("zoomInButton")
        self.zoom_in_button.setFixedSize(self.zoom_in_button.sizeHint().width() + 20, self.zoom_in_button.sizeHint().height() + 10)
        self.zoom_in_button.clicked.connect(self.zoom_in)

        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.setObjectName("zoomOutButton")
        self.zoom_out_button.setFixedSize(self.zoom_out_button.sizeHint().width() + 20, self.zoom_out_button.sizeHint().height() + 10)
        self.zoom_out_button.clicked.connect(self.zoom_out)

        zoom_buttons_layout.addWidget(self.zoom_in_button)
        zoom_buttons_layout.addWidget(self.zoom_out_button)

        self.layout.addWidget(self.scroll_area)
        self.layout.addLayout(zoom_buttons_layout)

        self.min_scale = 0.5
        self.max_scale = 2.0
        self.current_scale = 1.0

        self.adjust_initial_zoom()

        self.selected_location = None
        self.pin_item = None

        self.view.mousePressEvent = self.map_clicked

        confirm_button_layout = QHBoxLayout()

        self.confirm_button = QPushButton("Confirm Location")
        self.confirm_button.setObjectName("confirmButton")
        self.confirm_button.setFixedSize(self.confirm_button.sizeHint().width() + 80, self.confirm_button.sizeHint().height() + 20)
        self.confirm_button.clicked.connect(self.confirm_location)
        confirm_button_layout.addWidget(self.confirm_button)

        self.layout.addLayout(confirm_button_layout)

        self.confirm_button.setEnabled(False)

        self.update_zoom_buttons()
        
    def load_stylesheet(self):
        """
        Loads the stylesheet for the dialog from a CSS file.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'map_popup.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def zoom_in(self):
        """
        Zooms in on the map image by a factor of 1.2.

        Increases the current zoom scale and updates the view accordingly,
        ensuring it does not exceed the maximum scale.
        """
        factor = 1.2
        new_scale = self.current_scale * factor
        if new_scale <= self.max_scale:
            self.current_scale = new_scale
            self.view.scale(factor, factor)
        else:
            self.current_scale = self.max_scale

        self.update_zoom_buttons()

    def zoom_out(self):
        """
        Zooms out of the map image by a factor of 0.8.

        Decreases the current zoom scale and updates the view accordingly,
        ensuring it does not fall below the minimum scale.
        """
        factor = 0.8
        new_scale = self.current_scale * factor
        if new_scale >= self.min_scale:
            self.current_scale = new_scale
            self.view.scale(factor, factor)
        else:
            self.current_scale = self.min_scale

        self.update_zoom_buttons()

    def adjust_initial_zoom(self):
        """
        Adjusts the initial zoom level based on the map image and view size.

        Scales the map image to fit within the view while maintaining the
        minimum scale requirement.
        """
        map_width = self.map_item.pixmap().width()
        view_width = self.view.viewport().width()

        scale_factor = view_width / map_width

        if scale_factor < self.min_scale:
            scale_factor = self.min_scale

        self.view.resetTransform()
        self.view.scale(scale_factor, scale_factor)

        self.current_scale = scale_factor
        self.update_zoom_buttons()

    def map_clicked(self, event):
        """
        Handles mouse click events on the map.

        :param event: The mouse event containing the click position.
        """
        click_position = self.view.mapToScene(event.pos())
        x, y = int(click_position.x()), int(click_position.y())

        self.selected_location = (x, y)

        self.add_or_move_pin(x, y)

        self.confirm_button.setEnabled(True)

    def add_or_move_pin(self, x, y):
        """
        Adds or moves a pin to the selected location on the map.

        :param x: The x-coordinate of the selected location.
        :param y: The y-coordinate of the selected location.
        """
        pin_image_path = os.path.join(os.path.dirname(__file__), 'resources', 'map_pin.png')
        pin_pixmap = QPixmap(pin_image_path)

        scaled_pin_pixmap = pin_pixmap.scaled(int(pin_pixmap.width() * 0.05), int(pin_pixmap.height() * 0.05), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        if self.pin_item:
            self.pin_item.setPos(x, y)
        else:
            self.pin_item = QGraphicsPixmapItem(scaled_pin_pixmap)

            self.pin_item.setOffset(-scaled_pin_pixmap.width() / 2, -scaled_pin_pixmap.height())
            self.pin_item.setPos(x, y)
            self.pin_item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

            self.scene.addItem(self.pin_item)

    def confirm_location(self):
        """
        Confirms the selected location and emits the location_selected_signal.

        Displays a confirmation dialog and, if the user agrees, emits the
        selected location. If no location has been selected, a warning is shown.
        """
        if self.selected_location:
            confirmation = QMessageBox.question(self, "Confirm Location", 
                                                f"Do you want to save the selected location {self.selected_location}?",
                                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if confirmation == QMessageBox.Yes:
                self.location_selected_signal.emit(self.selected_location)
                self.close()
        else:
            QMessageBox.warning(self, "No Location Selected", "Please click on the map to select a location.")

    def update_zoom_buttons(self):
        """
        Updates the state of the zoom buttons based on the current scale.

        Enables or disables the zoom in and zoom out buttons as appropriate.
        """
        self.zoom_in_button.setEnabled(self.current_scale < self.max_scale)
        self.zoom_out_button.setEnabled(self.current_scale > self.min_scale)
