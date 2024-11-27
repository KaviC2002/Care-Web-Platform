import os
import zipfile

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton, QHBoxLayout, \
    QGridLayout, QFrame, QSizePolicy, QProgressBar, QDialog, QCheckBox, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt
from app.util.database_helper import DatabaseHelper
from datetime import datetime

database_helper = DatabaseHelper()
class ReIDDatabase(QWidget):
    """
    A QWidget for managing and displaying a database of REID images.

    This class provides functionality to load images from a database, display
    them in a grid, and allow users to select images for downloading or deletion.
    """
    def __init__(self):
        """
        Initializes the ReIDDatabase class and sets up the user interface.
        """
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """
        Initializes the user interface elements, including layout, buttons,
        and tree widget for displaying REID images.
        """
        self.load_stylesheet()

        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)

        self.tw = QTreeWidget()
        self.tw.setColumnCount(1)
        self.tw.setObjectName("reidImagesTree")
        self.tw.setHeaderLabels(["REID Date"])
        self.layout.addWidget(self.tw)

        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setObjectName("thumbnailFrame")
        self.thumbnail_frame.setFixedHeight(360)
        self.thumbnail_layout = QGridLayout(self.thumbnail_frame)
        self.thumbnail_layout.setAlignment(Qt.AlignTop)
        self.layout.addWidget(self.thumbnail_frame)
        self.thumbnail_size = (150, 150)

        self.selected_images = set()
        self.select_all_checkbox = None
        self.in_delete_mode = False
        self.confirm_delete_button = None
        self.in_download_mode = False
        self.confirm_download_button = None

        self.button_layout = QHBoxLayout()
        self.download_button = QPushButton("Download Images")
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(lambda: self.toggle_mode("download"))
        self.download_button.setFixedSize(self.download_button.sizeHint().width() + 50,
                                          self.download_button.sizeHint().height() + 10)
        self.download_button.setEnabled(False)

        self.delete_button = QPushButton("Delete Images")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setFixedSize(self.delete_button.sizeHint().width() + 50,
                                        self.delete_button.sizeHint().height() + 10)
        self.delete_button.clicked.connect(lambda: self.toggle_mode("delete"))
        self.delete_button.setEnabled(False)
        self.button_layout.addWidget(self.download_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.delete_button, alignment=Qt.AlignCenter)
        self.layout.addLayout(self.button_layout)

        self.pagination_layout = QHBoxLayout()

        self.prev_button = QPushButton("Previous")
        self.prev_button.setObjectName("prevButton")
        self.prev_button.setFixedSize(self.prev_button.sizeHint().width() + 20,
                                      self.prev_button.sizeHint().height() + 10)
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
        self.next_button.setFixedSize(self.next_button.sizeHint().width() + 20,
                                      self.next_button.sizeHint().height() + 10)
        self.next_button.clicked.connect(self.next_page)

        self.pagination_layout.addWidget(self.prev_button, alignment=Qt.AlignCenter)
        self.pagination_layout.addWidget(self.first_button, alignment=Qt.AlignCenter)
        self.pagination_layout.addWidget(self.last_button, alignment=Qt.AlignCenter)
        self.pagination_layout.addWidget(self.next_button, alignment=Qt.AlignCenter)

        self.first_button.setEnabled(False)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.last_button.setEnabled(False)

        self.layout.addLayout(self.pagination_layout)

        self.setLayout(self.layout)

        self.images = []
        self.images_per_page = 10
        self.current_page = 0
        self.total_pages = max(1, (len(self.images) + self.images_per_page -1) // self.images_per_page)
        self.populate_tree()
        self.tw.itemClicked.connect(self.tree_click)

    def update_image_grid(self):
        """
        Updates the thumbnail display grid to show images corresponding to
        the current page.
        """
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        start_index = self.current_page * self.images_per_page
        end_index = min(start_index + self.images_per_page, len(self.images))

        row = 0
        col = 0

        for i in range(start_index, end_index):
            thumbnail_label = QLabel()
            image_data = self.images[i]
            thumbnail_path = image_data[4]
            reid_id = image_data[-1]
            pixmap = QPixmap(thumbnail_path)
            thumbnail_label.setPixmap(pixmap)
            thumbnail_label.setFixedSize(*self.thumbnail_size)

            if reid_id in self.selected_images:
                if self.in_delete_mode:
                    thumbnail_label.setStyleSheet("border: 3px solid red;")
                elif self.in_download_mode:
                    thumbnail_label.setStyleSheet("border: 3px solid yellow;")
            else:
                thumbnail_label.setStyleSheet("border: none;")

            overlay_label = QLabel(thumbnail_label)
            overlay_label.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
            overlay_label.setFixedSize(*self.thumbnail_size)

            def enter_event(event, lbl=overlay_label):
                lbl.setStyleSheet("background-color: rgba(0, 0, 0, 0.4);")

            def leave_event(event, lbl=overlay_label):
                lbl.setStyleSheet("background-color: rgba(0, 0, 0, 0);")

            thumbnail_label.enterEvent = enter_event
            thumbnail_label.leaveEvent = leave_event

            if self.in_delete_mode or self.in_download_mode:
                thumbnail_label.mousePressEvent = lambda event, img_id=reid_id: self.toggle_image_selection(img_id)
            else:
                thumbnail_label.mousePressEvent = lambda event, image=image_data: self.open_image_popup(image)

            container_widget = QWidget()
            container_layout = QVBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(thumbnail_label, alignment=Qt.AlignCenter)

            self.thumbnail_layout.addWidget(container_widget, row, col, alignment=Qt.AlignCenter)

            col += 1
            if col >= 5:
                col = 0
                row += 1

        self.update_pagination()

    def toggle_select_all(self, state):
        """
        Toggles the selection of all images based on the state of the
        'Select All' checkbox.

        Args:
            state (Qt.CheckState): The new state of the checkbox.
        """
        if state == Qt.Checked:
            for image in self.images:
                self.selected_images.add(image[-1])
        else:
            self.selected_images.clear()

        if self.in_delete_mode:
            self.confirm_delete_button.setEnabled(bool(self.selected_images))

        if self.in_download_mode:
            self.confirm_download_button.setEnabled(bool(self.selected_images))

        self.update_image_grid()

    def toggle_image_selection(self, image_id):
        """
        Toggles the selection state of a single image by its ID.

        Args:
            image_id (str): The ID of the image to toggle.
        """
        if image_id in self.selected_images:
            self.selected_images.remove(image_id)
        else:
            self.selected_images.add(image_id)

        self.update_image_grid()

        if self.in_delete_mode:
            self.confirm_delete_button.setEnabled(bool(self.selected_images))

        if self.in_download_mode:
            self.confirm_download_button.setEnabled(bool(self.selected_images))

    def toggle_mode(self, mode):
        """
        Toggles between download and delete modes.

        Args:
            mode (str): The mode to switch to ("delete" or "download").
        """
        if mode == "delete":
            if not self.in_delete_mode:
                self.in_delete_mode = True
                self.delete_button.setText("Cancel")
                self.download_button.setVisible(False)
                self.add_controls(mode)
            else:
                self.in_delete_mode = False
                self.delete_button.setText("Delete Images")
                self.download_button.setVisible(True)
                self.remove_controls(mode)

        elif mode == "download":
            if not self.in_download_mode:
                self.in_download_mode = True
                self.download_button.setText("Cancel")
                self.delete_button.setVisible(False)
                self.add_controls(mode)
            else:
                self.in_download_mode = False
                self.download_button.setText("Download Images")
                self.delete_button.setVisible(True)
                self.remove_controls(mode)

        self.update_image_grid()

    def add_controls(self, mode):
        """
        Adds control buttons to the UI based on the specified mode.

        Args:
            mode (str): The mode determining which buttons to add ('delete' or 'download').
        """
        if not self.select_all_checkbox:
            self.select_all_checkbox = QCheckBox("Select All")
            self.select_all_checkbox.setObjectName("selectAllCheckbox")
            self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
            self.button_layout.insertWidget(0, self.select_all_checkbox, alignment=Qt.AlignCenter)

        if mode == "delete" and not self.confirm_delete_button:
            self.confirm_delete_button = QPushButton("Delete Selected")
            self.confirm_delete_button.setObjectName("deleteSelectedButton")
            self.confirm_delete_button.setFixedSize(self.delete_button.sizeHint().width() + 80,
                                                    self.delete_button.sizeHint().height())
            self.confirm_delete_button.clicked.connect(self.confirm_delete_selected)
            self.confirm_delete_button.setEnabled(False)
            self.button_layout.insertWidget(2, self.confirm_delete_button, alignment=Qt.AlignCenter)

        elif mode == "download" and not self.confirm_download_button:
            self.confirm_download_button = QPushButton("Download Selected")
            self.confirm_download_button.setObjectName("downloadSelectedButton")
            self.confirm_download_button.setFixedSize(self.download_button.sizeHint().width() + 80,
                                                      self.download_button.sizeHint().height())
            self.confirm_download_button.clicked.connect(self.confirm_download_selected)
            self.confirm_download_button.setEnabled(False)
            self.button_layout.insertWidget(2, self.confirm_download_button, alignment=Qt.AlignCenter)

    def remove_controls(self, mode):
        """
        Removes control buttons from the UI based on the specified mode.

        Args:
            mode (str): The mode determining which buttons to remove ('delete' or 'download').
        """
        if self.select_all_checkbox:
            self.button_layout.removeWidget(self.select_all_checkbox)
            self.select_all_checkbox.deleteLater()
            self.select_all_checkbox = None

        if mode == "delete" and self.confirm_delete_button:
            self.button_layout.removeWidget(self.confirm_delete_button)
            self.confirm_delete_button.deleteLater()
            self.confirm_delete_button = None

        elif mode == "download" and self.confirm_download_button:
            self.button_layout.removeWidget(self.confirm_download_button)
            self.confirm_download_button.deleteLater()
            self.confirm_download_button = None

        self.selected_images.clear()

    def confirm_delete_selected(self):
        """
        Confirms and deletes the selected images from the database.

        If images are selected, a confirmation dialog appears. If confirmed, the images are deleted
        from the database and the UI is updated accordingly.
        """
        if self.selected_images:
            confirmation = QMessageBox.question(self, "Confirm Delete",
                                                f"Are you sure you want to delete {len(self.selected_images)} images from the ReID Database? The original photos will remain in local database",
                                                QMessageBox.Yes | QMessageBox.No)
            if confirmation == QMessageBox.Yes:
                deleted_images = []
                for image_id in self.selected_images:
                    database_helper.delete_reid(image_id)
                    deleted_images.append(image_id)

                self.selected_images.clear()

                self.in_delete_mode = False
                self.delete_button.setText("Delete Images")
                self.remove_controls("delete")
                self.images = [img for img in self.images if img[0] not in deleted_images]
                self.populate_tree()
                self.clear_thumbnail_display()
                self.download_button.setEnabled(True)
                self.delete_button.setEnabled(True)
                self.download_button.setVisible(True)
                self.delete_button.setVisible(True)


    def confirm_download_selected(self):
        """
        Confirms and downloads the selected images as a ZIP file.

        If images are selected, a dialog appears for selecting the download folder and filename.
        The selected images are then zipped and saved to the specified location.
        """

        if not self.selected_images:
            QMessageBox.warning(self, "No Selection", "No images selected for download.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")

        if not folder:
            return

        zip_filename, _ = QFileDialog.getSaveFileName(self, "Save Zip File", folder, "Zip Files (*.zip)")

        if not zip_filename:
            return

        if not zip_filename.endswith(".zip"):
            zip_filename += ".zip"

        try:
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for image_id in self.selected_images:
                    image_data = database_helper.fetch_image_path_by_reid(image_id)

                    if image_data is not None:
                        bbox_image_path, crop_image_path, thumbnail_path = image_data

                        if os.path.exists(bbox_image_path):
                            zipf.write(bbox_image_path, os.path.basename(bbox_image_path))
                        if os.path.exists(crop_image_path):
                            zipf.write(crop_image_path, os.path.basename(crop_image_path))
                        if os.path.exists(thumbnail_path):
                            zipf.write(thumbnail_path, os.path.basename(thumbnail_path))

            QMessageBox.information(self, "Download Complete",
                                    f"{len(self.selected_images)} images have been zipped and saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"An error occurred while creating the ZIP file: {str(e)}")

        self.selected_images.clear()
        self.in_download_mode = False
        self.download_button.setText("Download Images")
        self.remove_controls("download")
        self.download_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.download_button.setVisible(True)
        self.delete_button.setVisible(True)
        self.update_image_grid()

    def update_pagination(self):
        """
        Updates the pagination controls based on the current state of the images.

        This method calculates the total number of pages and updates the navigation buttons
        (first, previous, next, last) as well as the visible page numbers.
        """
        for i in reversed(range(self.pagination_layout.count())):
            widget = self.pagination_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton) and widget not in [self.prev_button, self.next_button, self.last_button,
                                                                  self.first_button]:
                self.pagination_layout.removeWidget(widget)
                widget.deleteLater()

        total_pages = max(1, (len(self.images) + self.images_per_page - 1) // self.images_per_page)

        self.first_button.setEnabled(self.current_page > 0)
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled((self.current_page + 1) * self.images_per_page < len(self.images))
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
            self.pagination_layout.insertWidget(self.pagination_layout.count() - 2, page_button,
                                                alignment=Qt.AlignCenter)

    def open_image_popup(self, image):
        """
        Opens a popup dialog to display a full-size image and its metadata.

        Args:
            image (tuple): A tuple containing image metadata including file path, user, animal type,
                           group, and confidence level.
        """
        popup = QDialog(self, Qt.Window)
        popup.setWindowTitle("Full Image")
        popup.setGeometry(100, 100, 800, 600)
        main_layout = QVBoxLayout(popup)

        image_label = QLabel(popup)
        pixmap = QPixmap(image[2])
        image_label.setPixmap(
            pixmap.scaled(popup.width(), popup.height() - 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        image_label.setAlignment(Qt.AlignCenter)

        group_confidence_layout = QHBoxLayout()
        group_label = QLabel(f'Group: {image[-4]}')
        group_label.setObjectName("groupLabel")
        confidence_label = QLabel(f'Confidence: {image[-5]}')
        confidence_label.setObjectName("confidenceLabel")

        group_confidence_layout.addWidget(group_label)
        group_confidence_layout.addWidget(confidence_label)

        animal_user_layout = QHBoxLayout()
        animal_label = QLabel(f'Animal: {image[-2]}')
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

    def go_to_last_page(self):
        """
        Navigates to the last page of the image gallery.
        """
        total_pages = max(1, (len(self.images) + self.images_per_page - 1) // self.images_per_page)
        self.go_to_page(total_pages - 1)

    def go_to_first_page(self):
        """Navigates to the first page of the image gallery and updates the display.

            This method sets the current page to the first page (index 0) and refreshes the image grid
            to reflect the images on that page.
            """
        self.current_page = 0
        self.update_image_grid()

    def go_to_page(self, page_num):
        """Navigates to a specified page number in the image gallery.

        Args:
            page_num (int): The page number to navigate to (0-based index).

        Raises:
            ValueError: If the provided page number is not a valid integer.

        If the page number is valid, it updates the current page and refreshes the image grid.
        If the page number is out of range, it displays a warning message.
        """
        try:
            total_pages = max(1, (len(self.images) + self.images_per_page - 1) // self.images_per_page)

            if 0 <= page_num < total_pages:
                self.current_page = page_num
                self.update_image_grid()
            else:
                QMessageBox.warning(self, "Invalid Page", f"Please enter a number between 1 and {total_pages}.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")

    def prev_page(self):
        """Navigates to the previous page in the image gallery.

        If the current page is greater than 0, this method decreases the current page index by one
        and updates the image grid to display the previous set of images.
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.update_image_grid()

    def next_page(self):
        """Navigates to the next page in the image gallery.

        If there are more images to display on the next page, this method increases the current page index
        by one and updates the image grid to display the next set of images.
        """
        if (self.current_page + 1) * self.images_per_page < len(self.images):
            self.current_page += 1
            self.update_image_grid()

    def populate_tree(self):
        """Populates the tree widget with images organized by date.

        This method clears the existing tree and fetches the REID IDs grouped by date from the database.
        It then creates top-level items for each date and child items for each REID ID under the corresponding date.
        """
        self.tw.clear()
        for date, ids in database_helper.get_reid_id_by_date().items():
            top_directory = QTreeWidgetItem(self.tw)
            top_directory.setText(0, date)
            for id in ids:
                id_item = QTreeWidgetItem(top_directory)
                id_item.setText(0, id)

    def tree_click(self, item, column):
        """Handles click events on the tree widget items.

        Args:
            item (QTreeWidgetItem): The item that was clicked.
            column (int): The column index of the clicked item.

        If the clicked item is a child of a date, this method retrieves images associated with the
        selected date and REID ID, updates the images list, and refreshes the image grid.
        If the clicked item is a date, it fetches all images associated with that date.
        It also enables the download and delete buttons after loading the images.
        """
        if item.parent() is not None:
            date = item.parent().text(0)
            reid_id = item.text(0)
            get_images = database_helper.get_image_by_date_and_id(date, reid_id)
        else:
            date = item.text(0)
            get_images = database_helper.get_reid_image_by_date(date)

        images_list = []
        for image in get_images:
            images_list.append(image)

        self.images = images_list
        self.current_page = 0
        self.total_pages = max(1, (len(self.images) + self.images_per_page -1) // self.images_per_page)
        self.update_image_grid()
        self.download_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def load_stylesheet(self):
        """Loads and applies a stylesheet to the widget.

        This method reads a CSS file located in the 'css' directory and applies the styles to the
        current widget, enhancing the visual appearance of the interface.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'reid_page.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def clear_thumbnail_display(self):
        """Clears the thumbnail display area.

        This method removes all thumbnails from the thumbnail layout by iterating through its items
        and deleting them. It ensures that the display area is empty and ready for new thumbnails.
        """
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()


