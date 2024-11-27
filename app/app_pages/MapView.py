from PyQt5.QtWidgets import (QWidget, QFrame, QVBoxLayout, QLabel, QGraphicsView, 
                             QGraphicsScene, QScrollArea, QPushButton, QGraphicsPixmapItem, 
                             QGraphicsEllipseItem, QGraphicsItem, QDialog, QGridLayout, QHBoxLayout)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPixmap, QPainter, QColor
from app.util.database_helper import DatabaseHelper
from app.app_pages.MapPinInfoPopup import MapPinInfoPopup
import os
import math

class MapView(QWidget):
    """
    A widget that displays a map and allows users to interact with it by zooming in/out and placing pins.

    The MapView class provides functionality to visualize a map image, manage zooming features,
    and display location pins based on image data fetched from a database. Users can view images
    associated with each pin by clicking on them, which opens a pop-up with relevant information.

    Attributes:
        db_helper (DatabaseHelper): An instance of DatabaseHelper for interacting with the database.
        layout (QVBoxLayout): The main layout of the widget.
        scene (QGraphicsScene): The scene that holds the map and pin items.
        view (QGraphicsView): The view for displaying the graphics scene.
        scroll_area (QScrollArea): A scroll area that allows for panning around the map.
        container_layout (QVBoxLayout): A layout to hold the scroll area and zoom buttons.
        map_image (QPixmap): The QPixmap object representing the map image.
        map_item (QGraphicsPixmapItem): The graphical item for the map image.
        min_scale (float): The minimum zoom scale factor.
        max_scale (float): The maximum zoom scale factor.
        current_scale (float): The current zoom scale factor.
        pins (list): A list of pin items displayed on the map.

    Methods:
        load_stylesheet(): Loads the custom stylesheet for the widget.
        load_pins(): Fetches images from the database and adds corresponding pins to the map.
        group_pins(images, threshold=50): Groups pins that are close to each other based on a distance threshold.
        calculate_distance(loc1, loc2): Calculates the distance between two locations.
        add_pin(pin_group): Adds a pin to the map based on a group of images.
        show_images(pin_group): Displays a pop-up with images associated with the selected pin.
        zoom_in(): Increases the zoom level of the map.
        zoom_out(): Decreases the zoom level of the map.
        adjust_initial_zoom(): Adjusts the initial zoom level based on the view's width.
        refresh_pins(): Clears and reloads the pins on the map.
        showEvent(event): Overrides the show event to refresh pins when the widget is shown.
        update_zoom_buttons(): Updates the enabled state of the zoom buttons based on the current scale.
    """
    def __init__(self):
        super().__init__()

        self.db_helper = DatabaseHelper()
        
        self.load_stylesheet()

        self.layout = QVBoxLayout(self)
        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.view)

        self.container_layout = QVBoxLayout(self)
        self.container_layout.addWidget(self.scroll_area)

        zoom_buttons_layout = QHBoxLayout()

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.setObjectName("zoomInButton")
        self.zoom_in_button.setFixedSize(self.zoom_in_button.sizeHint().width() + 20, self.zoom_in_button.sizeHint().height() + 10)
        self.zoom_in_button.clicked.connect(self.zoom_in)

        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.setObjectName("zoomInButton")
        self.zoom_out_button.setFixedSize(self.zoom_out_button.sizeHint().width() + 20, self.zoom_out_button.sizeHint().height() + 10)
        self.zoom_out_button.clicked.connect(self.zoom_out)

        zoom_buttons_layout.addWidget(self.zoom_in_button)
        zoom_buttons_layout.addWidget(self.zoom_out_button)

        self.container_layout.addLayout(zoom_buttons_layout)

        self.layout.addLayout(self.container_layout)

        self.map_image = QPixmap(os.path.join(os.path.dirname(__file__), 'resources', 'waihekemap.png'))
        self.map_item = QGraphicsPixmapItem(self.map_image)
        self.scene.addItem(self.map_item)

        self.min_scale = 0.5
        self.max_scale = 2.0
        self.current_scale = 1.0

        self.adjust_initial_zoom()

        self.pins = []
        self.load_pins()

        self.update_zoom_buttons()

    def load_stylesheet(self):
        """Loads the custom stylesheet for the widget."""
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'map_view.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def load_pins(self):
        """Fetches images from the database and adds corresponding pins to the map."""
        images = self.db_helper.fetch_unsynced_images()
        pin_groups = self.group_pins(images, threshold=50)
        for pin_group in pin_groups:
            self.add_pin(pin_group)

    def group_pins(self, images, threshold=50):
        """
        Groups pins that are close to each other based on a distance threshold.

        Args:
            images (list): A list of images to group.
            threshold (int): The distance threshold for grouping pins.

        Returns:
            list: A list of groups of images.
        """
        pin_groups = []
        for image in images:
            x, y = map(int, image[5].strip('()').split(','))
            added = False
            for group in pin_groups:
                group_x, group_y = map(int, group[0][5].strip('()').split(','))
                if self.calculate_distance((x, y), (group_x, group_y)) < threshold:
                    group.append(image)
                    added = True
                    break
            if not added:
                pin_groups.append([image])
        return pin_groups

    def calculate_distance(self, loc1, loc2):
        """
        Calculates the distance between two locations.

        Args:
            loc1 (tuple): The first location as (x, y).
            loc2 (tuple): The second location as (x, y).

        Returns:
            float: The distance between the two locations.
        """
        return math.sqrt((loc1[0] - loc2[0]) ** 2 + (loc1[1] - loc2[1]) ** 2)

    def add_pin(self, pin_group):
        """
        Adds a pin to the map based on a group of images.

        Args:
            pin_group (list): A group of images associated with the pin.
        """
        x = sum(int(img[5].strip('()').split(',')[0]) for img in pin_group) / len(pin_group)
        y = sum(int(img[5].strip('()').split(',')[1]) for img in pin_group) / len(pin_group)

        pin_image_path = os.path.join(os.path.dirname(__file__), 'resources', 'map_pin.png')
        pin_pixmap = QPixmap(pin_image_path)

        scaled_pin_pixmap = pin_pixmap.scaled(int(pin_pixmap.width() * 0.05), int(pin_pixmap.height() * 0.05), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        pin_item = QGraphicsPixmapItem(scaled_pin_pixmap)

        pin_item.setOffset(-scaled_pin_pixmap.width() / 2, -scaled_pin_pixmap.height())
        pin_item.setPos(x, y)
        pin_item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        pin_item.setToolTip(f"{len(pin_group)} images")
        
        pin_item.setAcceptHoverEvents(True)
        pin_item.mousePressEvent = lambda event: self.show_images(pin_group)

        self.scene.addItem(pin_item)
        self.pins.append(pin_item)

    def show_images(self, pin_group):
        """
        Displays a pop-up with images associated with the selected pin.

        Args:
            pin_group (list): The group of images to display.
        """
        image_popup = MapPinInfoPopup(pin_group)
        image_popup.exec_()

    def zoom_in(self):
        """Increases the zoom level of the map."""
        factor = 1.2
        new_scale = self.current_scale * factor
        if new_scale <= self.max_scale:
            self.current_scale = new_scale
            self.view.scale(factor, factor)
        else:
            self.current_scale = self.max_scale

        self.update_zoom_buttons()

    def zoom_out(self):
        """Decreases the zoom level of the map."""
        factor = 0.8
        new_scale = self.current_scale * factor
        if new_scale >= self.min_scale:
            self.current_scale = new_scale
            self.view.scale(factor, factor)
        else:
            self.current_scale = self.min_scale

        self.update_zoom_buttons()

    def adjust_initial_zoom(self):
        """Adjusts the initial zoom level based on the view's width."""
        map_width = self.map_item.pixmap().width()
        view_width = self.view.viewport().width()

        scale_factor = view_width / map_width

        if scale_factor < self.min_scale:
            scale_factor = self.min_scale

        self.view.resetTransform()
        self.view.scale(scale_factor, scale_factor)

        self.current_scale = scale_factor

    def refresh_pins(self):
        """Clears and reloads the pins on the map."""
        for pin in self.pins:
            self.scene.removeItem(pin)
        self.pins.clear()

        self.load_pins()

    def showEvent(self, event):
        """Overrides the show event to refresh pins when the widget is shown."""
        super().showEvent(event)
        self.refresh_pins()

    def update_zoom_buttons(self):
        """Updates the enabled state of the zoom buttons based on the current scale."""
        self.zoom_in_button.setEnabled(self.current_scale < self.max_scale)
        self.zoom_out_button.setEnabled(self.current_scale > self.min_scale)
