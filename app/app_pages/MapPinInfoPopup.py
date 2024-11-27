from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QGridLayout, QPushButton, QFrame, QHBoxLayout, QMenu, QSlider, \
    QWidgetAction, QLineEdit, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt
import os

class MapPinInfoPopup:
    """
    A dialog that displays information about images associated with map pins.
    It allows users to filter images based on confidence levels, navigate through
    pages of images, and view detailed information for each image.
    """
    def __init__(self, pin_group):
        """
        Initializes the MapPinInfoPopup with a group of pins.

        :param pin_group: A list of images associated with map pins.
        """
        self.image_list = pin_group
        self.filtered_image_list = pin_group
        self.current_page = 0
        self.images_per_page = 10
        self.min_confidence = 0.000
        self.max_confidence = 1.000
        self.min_menu_open = False
        self.max_menu_open = False
        self.dialog = self.create_dialog()
        self.load_stylesheet()
        self.to_check = False
    
    def load_stylesheet(self):
        """
        Loads the stylesheet for the dialog from a CSS file.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'map_pin_info_popup.css')
        with open(css_file, 'r') as f:
            self.dialog.setStyleSheet(f.read())

    def create_dialog(self):
        """
        Creates and sets up the main dialog interface, including input fields,
        thumbnail display, and pagination buttons.

        :return: The configured QDialog instance.
        """
        dialog = QDialog()
        dialog.setWindowTitle("Images Info")
        dialog.setMinimumSize(800, 600)

        dialog_layout = QVBoxLayout(dialog)

        self.label = QLabel(f"{len(self.image_list)} images found")
        self.label.setObjectName("title")
        dialog_layout.addWidget(self.label)

        self.confidence_input_layout = QHBoxLayout()

        self.min_input = QLineEdit(f"{self.min_confidence:.3f}")
        self.min_input.setObjectName("minInput")
        self.min_input.setFixedSize(65, 30)
        self.min_input.setValidator(QDoubleValidator(0.0, 1.0, 3))
        self.min_input.textChanged.connect(self.update_min_confidence_from_input)


        self.max_input = QLineEdit(f"{self.max_confidence:.3f}")
        self.max_input.setObjectName("maxInput")
        self.max_input.setFixedSize(65, 30)
        self.max_input.setValidator(QDoubleValidator(0, 1, 3))
        self.max_input.textChanged.connect(self.update_max_confidence_from_input)

        self.confidence_input_layout.addWidget(QLabel("Confidence Range:"))
        self.confidence_input_layout.addWidget(self.min_input)
        self.confidence_input_layout.addWidget(QLabel(" - "))
        self.confidence_input_layout.addWidget(self.max_input)

        self.confidence_input_layout.addStretch()
        dialog_layout.addLayout(self.confidence_input_layout)

        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setObjectName("thumbnailFrame")
        self.thumbnail_frame.setFixedHeight(360)
        self.thumbnail_layout = QGridLayout(self.thumbnail_frame)
        self.thumbnail_layout.setAlignment(Qt.AlignTop)
        dialog_layout.addWidget(self.thumbnail_frame)

        self.pagination_layout = QHBoxLayout()

        self.prev_button = QPushButton("Previous")
        self.prev_button.setObjectName("prevButton")
        self.prev_button.setFixedSize(self.prev_button.sizeHint().width() + 20, self.prev_button.sizeHint().height() + 10)
        self.prev_button.clicked.connect(self.prev_page)

        self.first_button = QPushButton("«")
        self.first_button.setObjectName("firstPageButton")
        self.first_button.setFixedSize(30, 30)
        self.first_button.clicked.connect(self.go_to_first_page)

        self.last_button = QPushButton("»")
        self.last_button.setObjectName("lastPageButton")
        self.last_button.setFixedSize(30, 30)
        self.last_button.clicked.connect(self.go_to_last_page)

        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("nextButton")
        self.next_button.setFixedSize(self.next_button.sizeHint().width() + 20, self.next_button.sizeHint().height() + 10)
        self.next_button.clicked.connect(self.next_page)

        self.pagination_layout.addWidget(self.prev_button, alignment=Qt.AlignCenter)
        self.pagination_layout.addWidget(self.first_button, alignment=Qt.AlignCenter)
        self.pagination_layout.addWidget(self.last_button, alignment=Qt.AlignCenter)
        self.pagination_layout.addWidget(self.next_button, alignment=Qt.AlignCenter)

        self.first_button.setEnabled(False)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.last_button.setEnabled(False)

        dialog_layout.addLayout(self.pagination_layout)
        self.update_thumbnails()

        dialog.setLayout(dialog_layout)
        return dialog

    def show_error_message(self):
        """
        Displays an error message dialog when invalid input is provided for confidence levels.
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Please enter a value between 0 and 1.")
        msg.setWindowTitle("Invalid Input")
        msg.exec_()

    def update_min_confidence_from_input(self):
        """
        Updates the minimum confidence level based on user input from the QLineEdit.
        Ensures the value is within the valid range and adjusts if necessary.
        """
        try:
            value = float(self.min_input.text())
            if not (0.0 <= value <= 1.0):
                self.show_error_message()
                self.min_input.setText("0")
                return
            if value > self.max_confidence:
                value = self.max_confidence
            self.min_confidence = value
            self.update_confidence_range()
        except ValueError:
            pass

    def update_max_confidence_from_input(self):
        """
        Updates the maximum confidence level based on user input from the QLineEdit.
        Ensures the value is within the valid range and adjusts if necessary.
        """
        try:
            value = float(self.max_input.text())
            if not (0.0 <= value <= 1.0):
                self.show_error_message()
                self.max_input.setText("1")
                return
            if value < self.min_confidence:
                value = self.min_confidence
            self.max_confidence = value
            self.update_confidence_range()
        except ValueError:
            pass

    def update_confidence_range(self):
        """
        Filters the image list based on the current confidence range and updates the thumbnail display.
        """
        self.filter_images_by_confidence(self.min_confidence, self.max_confidence)
        self.update_thumbnails()

    def filter_images_by_confidence(self, min_value, max_value):
        """
        Filters the list of images based on the specified confidence range.

        :param min_value: Minimum confidence value for filtering.
        :param max_value: Maximum confidence value for filtering.
        """
        self.filtered_image_list = [
            image for image in self.image_list if min_value <= image[7] <= max_value
        ]
        self.current_page = 0

    def update_thumbnails(self):
        """
        Updates the displayed thumbnails in the dialog based on the current page and filtered image list.
        Handles pagination and thumbnail display logic.
        """
        self.clear_thumbnail_display()

        start_index = self.current_page * self.images_per_page
        end_index = min(start_index + self.images_per_page, len(self.filtered_image_list))

        row, col = 0, 0

        if len(self.filtered_image_list) != len(self.image_list):
            self.label.setText(f"Results: {len(self.filtered_image_list)} Photos from {len(self.image_list)} Photos")
        else:
            self.label.setText(f"{len(self.image_list)} Images Found")

        for i in range(start_index, end_index):
            image_id, user, bbox_image_path, _, thumbnail_path, _, _, confidence, _, _, _ = self.filtered_image_list[i]

            thumbnail_label = QLabel()
            pixmap = QPixmap(thumbnail_path)
            thumbnail_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            thumbnail_label.setFixedSize(150, 150)

            overlay_label = QLabel(thumbnail_label)
            overlay_label.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
            thumbnail_size = (150, 150)
            overlay_label.setFixedSize(*thumbnail_size)

            def enter_event(event, lbl=overlay_label):
                lbl.setStyleSheet("background-color: rgba(0, 0, 0, 0.4);")

            def leave_event(event, lbl=overlay_label):
                lbl.setStyleSheet("background-color: rgba(0, 0, 0, 0);")

            thumbnail_label.enterEvent = enter_event
            thumbnail_label.leaveEvent = leave_event


            thumbnail_label.mousePressEvent = lambda event, image=self.filtered_image_list[i]: self.open_image_popup(image)

            self.thumbnail_layout.addWidget(thumbnail_label, row, col)
            col += 1
            if col >= 5:
                col = 0
                row += 1

        self.update_pagination()

    def update_pagination(self):
        """
        Updates the state of the pagination buttons based on the current page and total images.
        Enables or disables buttons as appropriate.
        """
        for i in reversed(range(self.pagination_layout.count())):
            widget = self.pagination_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton) and widget not in [self.prev_button, self.next_button, self.last_button, self.first_button]:
                self.pagination_layout.removeWidget(widget)
                widget.deleteLater()

        total_pages = max(1, (len(self.image_list) + self.images_per_page - 1) // self.images_per_page)

        self.first_button.setEnabled(self.current_page > 0)
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled((self.current_page + 1) * self.images_per_page < len(self.image_list))
        self.last_button.setEnabled(self.current_page < total_pages - 1)

        max_visible_pages = 5
        start_page = max(0, min(self.current_page - max_visible_pages // 2, total_pages - max_visible_pages))
        end_page = min(total_pages, start_page + max_visible_pages)

        for page_num in range(start_page, end_page):
            page_button = QPushButton(str(page_num + 1))
            page_button.setFixedSize(40, 30)

            if page_num == self.current_page:
                page_button.setObjectName("selectedPageButton")
            else:
                page_button.setObjectName("unselectedPageButton")

            page_button.clicked.connect(lambda _, p=page_num: self.go_to_page(p))
            self.pagination_layout.insertWidget(self.pagination_layout.count() - 2, page_button, alignment=Qt.AlignCenter)

    def go_to_last_page(self):
        """
        Navigates to the last page of thumbnails.
        """
        total_pages = max(1, (len(self.filtered_image_list) + self.images_per_page - 1) // self.images_per_page)
        self.go_to_page(total_pages - 1)

    def go_to_first_page(self):
        """
        Navigates to the first page of thumbnails.
        """
        if self.to_check == True:
            self.to_check = False
            return
        self.current_page = 0
        self.update_thumbnails()

    def go_to_page(self, page_num):
        """
        Navigates to a specific page of thumbnails if available.
        """
        if page_num >= 0 and page_num < (len(self.filtered_image_list) + self.images_per_page - 1) // self.images_per_page:
            self.current_page = page_num
            self.update_thumbnails()

    def prev_page(self):
        """
        Navigates to the previous page of thumbnails if available.
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.update_thumbnails()

    def next_page(self):
        """
        Navigates to the next page of thumbnails if available.
        """
        if (self.current_page + 1) * self.images_per_page < len(self.filtered_image_list):
            self.current_page += 1
            self.update_thumbnails()

    def clear_thumbnail_display(self):
        """
        Clears the current thumbnails from the display.
        """
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def open_image_popup(self, image):
        """
        Opens a new dialog to display full image information for the selected image.

        :param image: The selected image's data to display.
        """
        popup = QDialog(self.dialog)
        popup.setWindowTitle("Full Image")
        popup.setGeometry(100, 100, 800, 600)
        main_layout = QVBoxLayout(popup)

        image_label = QLabel(popup)
        pixmap = QPixmap(image[2])
        image_label.setPixmap(
            pixmap.scaled(popup.width(), popup.height() - 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        image_label.setAlignment(Qt.AlignCenter)

        group_confidence_layout = QHBoxLayout()
        group_label = QLabel(f'Group: {image[-3]}')
        group_label.setObjectName("groupLabel")
        confidence_label = QLabel(f'Confidence: {image[-4]}')
        confidence_label.setObjectName("confidenceLabel")

        group_confidence_layout.addWidget(group_label)
        group_confidence_layout.addWidget(confidence_label)

        animal_user_layout = QHBoxLayout()
        animal_label = QLabel(f'Animal: {image[-1]}')
        animal_label.setObjectName("animalLabel")
        user_label = QLabel(f'Uploaded By: {image[1]}')
        user_label.setObjectName("userLabel")
        confidence_label.setAlignment(Qt.AlignCenter)
        user_label.setAlignment(Qt.AlignCenter)
        animal_label.setAlignment(Qt.AlignCenter)
        group_label.setAlignment(Qt.AlignCenter)

        animal_user_layout.addWidget(animal_label)
        animal_user_layout.addWidget(user_label)

        main_layout.addWidget(image_label)
        main_layout.addLayout(group_confidence_layout)
        main_layout.addLayout(animal_user_layout)

        main_layout.setAlignment(Qt.AlignCenter)
        popup.setLayout(main_layout)
        popup.show()

    def exec_(self):
        self.dialog.exec_()
