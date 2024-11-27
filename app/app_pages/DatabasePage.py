import zipfile
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QTreeWidget, QTreeWidgetItem, QPushButton, \
    QDialog, QHBoxLayout, QFrame, QCheckBox, QMessageBox, QComboBox, QMenu, QWidgetAction, QSlider, QFileDialog, \
    QProgressBar, QSizePolicy, QApplication, QLineEdit
from PyQt5.QtGui import QPixmap, QDoubleValidator
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from app.util.database_helper import DatabaseHelper
from datetime import datetime
import os
from app.detection_model.ReID import main as reid

class ReIDWorker(QThread):
    """
        This class represents a worker thread for running Re-Identification (ReID) tasks on selected images.

        It inherits from QThread to run tasks in the background without blocking the main UI thread. The worker processes
        a list of selected images, retrieves relevant image paths from the database, and performs ReID on these images.

        Attributes:
            selected_images (list): A list of image IDs to be processed.
            db_helper (object): A helper object to interface with the database for fetching image paths.
            reid_list (list): A list to store the image paths for ReID processing.

        Signals:
            progress_updated (int): Signal to update progress in the UI.
            reid_finished (dict): Signal emitted when the ReID process is complete, returning the results.
        """
    progress_updated = pyqtSignal(int)
    reid_finished = pyqtSignal(dict)

    def __init__(self, selected_images, db_helper):
        super().__init__()
        self.selected_images = selected_images
        self.db_helper = db_helper
        self.reid_list = []

    def run(self):
        """
        The main function executed when the thread starts. It fetches image paths for the selected images,
        processes them for ReID, and emits the result. The progress is updated at each step.
                """
        self.progress_updated.emit(0)
        for index, image_id in enumerate(self.selected_images):
            image_data = self.db_helper.fetch_image_path_by_reid(image_id)
            if image_data is not None:
                bbox_image_path, crop_image_path, thumbnail_path = image_data
                self.reid_list.append(crop_image_path)

        output = reid(self.reid_list, progress_callback=self.progress_updated.emit)
        self.reid_finished.emit(output)


class DatabasePage(QWidget):
    """
        This class represents the Database page in the application's GUI. It provides functionality to display,
        filter, sort, and manage images stored in the database. Users can sort images by date or confidence score,
        filter images based on animal types, and update confidence ranges for displayed images. Additionally,
        the page includes functionality for downloading, running ReID, and deleting images.

        Attributes:
            db_helper (DatabaseHelper): An instance of the helper class to interact with the database.
            reid_database (str): The re-identification database that stores processed data.
            tree_widget (QTreeWidget): A widget displaying unsynced images by upload date.
            sort_combobox (QComboBox): A dropdown menu for sorting options (date or confidence).
            animal_combobox (QComboBox): A dropdown menu to filter images by animal type.
            min_confidence (float): The minimum confidence value for filtering images.
            max_confidence (float): The maximum confidence value for filtering images.
            min_input (QLineEdit): Input field for entering the minimum confidence value.
            max_input (QLineEdit): Input field for entering the maximum confidence value.
            progress_bar (QProgressBar): A progress bar to display the progress of an ongoing task (e.g., ReID).
            thumbnail_frame (QFrame): A frame for displaying image thumbnails.
            pagination_layout (QHBoxLayout): Layout containing buttons for pagination control.
            download_button (QPushButton): Button for downloading images.
            reid_button (QPushButton): Button for running the ReID task.
            delete_button (QPushButton): Button for deleting images.
            image_list (list): A list of images currently displayed.
            selected_images (set): A set of images selected by the user.
            sorting_option (str): The current sorting option chosen by the user.
        """
    def __init__(self, reid_database):
        """
                Initializes the DatabasePage widget and its components, setting up layouts, input fields, dropdowns,
                pagination controls, and buttons for filtering, sorting, and managing images.

                Args:
                    reid_database (str): The re-identification database used in the application.
                """
        super().__init__()

        self.db_helper = DatabaseHelper()
        self.reid_database = reid_database
        self.load_stylesheet()

        self.DatabasePage_layout = QVBoxLayout()

        self.tree_widget = QTreeWidget()
        self.tree_widget.setObjectName("unsyncedImagesTree")
        self.tree_widget.setHeaderLabels(["Upload Date"])
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.DatabasePage_layout.addWidget(self.tree_widget)

        self.top_layout = QHBoxLayout()


        self.sort_combobox = QComboBox(self)
        self.sort_combobox.setObjectName("sortDropDown")
        self.sort_combobox.addItems(
            ["▼ Sort by Latest (Date)", "▼ Sort by Oldest (Date)", "▼ Sort by Highest Confidence (Images)", "▼ Sort by Lowest Confidence (Images)"])
        self.sort_combobox.currentIndexChanged.connect(self.sort_images)
        self.sort_combobox.setFixedSize(250, 30)


        self.top_layout.addWidget(self.sort_combobox, alignment=Qt.AlignLeft)

        self.animal_combobox = QComboBox(self)
        self.animal_combobox.setObjectName("animalDropDown")
        self.animal_combobox.setFixedSize(200, 30)
        self.animal_combobox.addItem("All")
        self.animal_combobox.currentIndexChanged.connect(self.filter_by_animal)
        self.top_layout.addWidget(self.animal_combobox, alignment=Qt.AlignCenter)

        self.top_layout.addStretch(1)

        self.min_confidence = 0.000
        self.max_confidence = 1.000
        self.min_menu_open = False
        self.max_menu_open = False

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

        self.top_layout.addLayout(self.confidence_input_layout, stretch=0)

        self.DatabasePage_layout.addLayout(self.top_layout)

        self.setLayout(self.DatabasePage_layout)

        self.progress_label = QLabel("")
        self.DatabasePage_layout.addWidget(self.progress_label, alignment=Qt.AlignCenter)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.DatabasePage_layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)

        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setObjectName("thumbnailFrame")
        self.thumbnail_frame.setFixedHeight(360)
        self.thumbnail_layout = QGridLayout(self.thumbnail_frame)
        self.thumbnail_layout.setAlignment(Qt.AlignTop)
        self.DatabasePage_layout.addWidget(self.thumbnail_frame)

        self.select_all_checkbox = None
        self.in_delete_mode = False
        self.confirm_delete_button = None
        self.in_download_mode = False
        self.confirm_download_button = None
        self.confirm_reid_button = None
        self.in_reid_mode = False

        self.current_page = 0
        self.images_per_page = 10
        self.thumbnail_size = (150, 150)
        self.image_list = []
        self.selected_images = set()

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

        self.DatabasePage_layout.addLayout(self.pagination_layout)

        self.setLayout(self.DatabasePage_layout)
        self.populate_tree()


        self.sorting_option = "▼ Sort by Latest (Date)"
        self.selected_date = None

        self.download_button = QPushButton("Download Images")
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(lambda: self.toggle_mode("download"))
        self.download_button.setFixedSize(self.download_button.sizeHint().width() + 50,
                                          self.download_button.sizeHint().height() + 10)
        self.download_button.setEnabled(False)

        self.reid_button = QPushButton("Run ReID")
        self.reid_button.setObjectName("reidButton")
        self.reid_button.clicked.connect(lambda: self.toggle_mode("reid"))
        self.reid_button.setFixedSize(self.download_button.sizeHint().width() + 50,
                                      self.download_button.sizeHint().height() + 10)
        self.reid_button.setEnabled(False)

        self.button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete Images")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setFixedSize(self.delete_button.sizeHint().width() + 50,
                                        self.delete_button.sizeHint().height() + 10)
        self.delete_button.clicked.connect(lambda: self.toggle_mode("delete"))
        self.delete_button.setEnabled(False)

        self.button_layout.addWidget(self.download_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.delete_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.reid_button, alignment=Qt.AlignCenter)

        self.DatabasePage_layout.insertLayout(5, self.button_layout)

        self.populate_animal_combobox()


    def populate_animal_combobox(self):
        """
                Populates the animal combobox with distinct animal types fetched from the database.
                """
        self.animal_combobox.clear()
        self.animal_combobox.addItem("▼ All")
        animal_types = self.db_helper.get_distinct_animals()
        for animal in animal_types:
            self.animal_combobox.addItem(animal)

    def filter_by_animal(self):
        """
                Filters the displayed images based on the selected animal type from the combobox.
                """
        self.refresh_images_for_selected_group2()
        selected_animal = self.animal_combobox.currentText()
        if not self.image_list:
            return

        if selected_animal == "▼ All":
            filtered_images = self.image_list
        else:
            filtered_images = [img for img in self.image_list if
                               img[-1] == selected_animal]

        self.image_list = filtered_images
        self.update_thumbnails()

    def load_stylesheet(self):
        """
        Loads and applies the CSS stylesheet for the database page layout and components.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'database_page.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def show_error_message(self):
        """
        Shows Error Message if user inputs enters an invalid number in the range.
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Please enter a value between 0 and 1.")
        msg.setWindowTitle("Invalid Input")
        msg.exec_()

    def update_min_confidence_from_input(self):
        """
        Updates the minimum confidence value based on the input provided by the user.
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
            self.refresh_images_for_selected_group()
        except ValueError:
            pass

    def update_max_confidence_from_input(self):
        """
        Updates the maximum confidence value based on the input provided by the user.
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
            self.refresh_images_for_selected_group()
        except ValueError:
            pass

    def sort_images(self):
        """
        Sorts the images displayed in the tree widget based on the selected sorting option
        from the combo box. The options include sorting by date (latest or oldest) or
        sorting by confidence level (highest or lowest).
        """
        self.sorting_option = self.sort_combobox.currentText()

        if self.sorting_option == "▼ Sort by Latest (Date)":
            self.tree_widget.sortItems(0, Qt.DescendingOrder)
        elif self.sorting_option == "▼ Sort by Oldest (Date)":
            self.tree_widget.sortItems(0, Qt.AscendingOrder)
        elif self.sorting_option == "▼ Sort by Highest Confidence (Images)":
            self.image_list.sort(key=lambda img: img[-4], reverse=True)
            self.update_thumbnails()
        elif self.sorting_option == "▼ Sort by Lowest Confidence (Images)":
            self.image_list.sort(key=lambda img: img[-4], reverse=False)
            self.update_thumbnails()

    def on_item_clicked(self, item, column):
        """
        Handles the event when an item in the tree widget is clicked. Depending on whether
        the clicked item has a parent, retrieves images based on the date and name, applies
        filtering by confidence, and updates the image display and related buttons.

        Args:
            item (QTreeWidgetItem): The item that was clicked.
            column (int): The column index of the clicked item.
        """
        if item.parent() is not None:
            date_with_count = item.parent().text(0)
            date = date_with_count.split(" (")[0]
            name_with_count = item.text(0)
            name = name_with_count.rsplit(" (", 1)[0]
            min_confidence = self.min_confidence
            max_confidence = self.max_confidence
            get_images = self.db_helper.get_image_by_date(date, name, min_confidence, max_confidence)
        else:
            date_with_count = item.text(0)
            date = date_with_count.split(" (")[0]
            min_confidence = self.min_confidence
            max_confidence = self.max_confidence
            get_images = self.db_helper.parent_date_click(date, min_confidence, max_confidence)

        images_list = []
        for image in get_images:
            images_list.append(image)
        self.image_list = images_list
        self.sort_images()
        self.filter_by_animal()
        self.current_page = 0
        self.update_thumbnails()
        self.download_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.reid_button.setEnabled(True)

    def populate_tree(self):
        """
        Populates the tree widget with images organized by date and group. Each date is a
        parent item, and groups of images under each date are child items. The count of
        folders and images is displayed next to each item.
        """
        self.tree_widget.clear()
        images_by_date = self.db_helper.get_images_by_date()

        for date_str, groups in images_by_date.items():
            folder_count = len(groups)
            date_item = QTreeWidgetItem(self.tree_widget)
            date_item.setText(0, f"{date_str} ({folder_count} folder/s)")

            for group_name, images in groups.items():
                group_item = QTreeWidgetItem(date_item)
                image_count = len(images)
                group_item.setText(0, f"{group_name} ({image_count} image/s)")
                group_item.setData(0, Qt.UserRole, images)
        
        self.sort_images()

    def refresh_images_for_selected_group(self):
        """
        Refreshes the displayed images based on the currently selected group in the tree
        widget. Retrieves images filtered by the selected group's date and name, updates
        the image list, and resets the current page for display.
        """
        current_item = self.tree_widget.currentItem()

        if current_item:
            min_confidence = self.min_confidence
            max_confidence = self.max_confidence

            if current_item.parent() is not None:
                date_with_count = current_item.parent().text(0)
                date = date_with_count.split(" (")[0]
                name_with_count = current_item.text(0)
                name = name_with_count.split(" (")[0]
                get_images = self.db_helper.get_image_by_date(date, name, min_confidence, max_confidence)
            else:
                if current_item.parent() is None:
                    date_with_count = current_item.text(0)
                    date = date_with_count.split(" (")[0]
                else:
                    date_with_count = current_item.parent().text(0)
                    date = date_with_count.split(" (")[0]
                get_images = self.db_helper.parent_date_click(date, min_confidence, max_confidence)

            images_list = [image for image in get_images]
            self.image_list = images_list
            self.sort_images()
            self.current_page = 0
            self.filter_by_animal()
            self.update_thumbnails()

    def refresh_images_for_selected_group2(self):
        """
        Similar to refresh_images_for_selected_group, this function refreshes the images
        displayed for the currently selected group. This version is does not have the self.filterbyanimal() function to avoid infinite loop.
        """
        current_item = self.tree_widget.currentItem()

        if current_item:
            min_confidence = self.min_confidence
            max_confidence = self.max_confidence

            if current_item.parent() is not None:
                date_with_count = current_item.parent().text(0)
                date = date_with_count.split(" (")[0]
                name_with_count = current_item.text(0)
                name = name_with_count.split(" (")[0]
                get_images = self.db_helper.get_image_by_date(date, name, min_confidence, max_confidence)
            else:
                if current_item.parent() is None:
                    date_with_count = current_item.text(0)
                    date = date_with_count.split(" (")[0]
                else:
                    date_with_count = current_item.parent().text(0)
                    date = date_with_count.split(" (")[0]
                get_images = self.db_helper.parent_date_click(date, min_confidence, max_confidence)

            images_list = [image for image in get_images]
            self.image_list = images_list
            self.sort_images()
            self.current_page = 0
            self.update_thumbnails()





    def update_thumbnails(self):
        """
        Updates the thumbnail display by clearing the current display and rendering the
        thumbnails for the images in the current page. It also applies different styles
        based on selection and modes (delete, download, reid).
        """
        self.clear_thumbnail_display()

        start_index = self.current_page * self.images_per_page
        end_index = min(start_index + self.images_per_page, len(self.image_list))

        row, col = 0, 0

        for i in range(start_index, end_index):
            image_id, user, image_path, crop_path, thumbnail_path, _, _, _, _, _, _ = self.image_list[i]

            thumbnail_label = QLabel()
            pixmap = QPixmap(thumbnail_path)
            thumbnail_label.setPixmap(pixmap)
            thumbnail_label.setFixedSize(*self.thumbnail_size)

            if image_id in self.selected_images:
                if self.in_delete_mode:
                    thumbnail_label.setStyleSheet("border: 3px solid red;")
                elif self.in_reid_mode:
                    thumbnail_label.setStyleSheet("border: 3px solid lightblue;")
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

            thumbnail_label.image_id = image_id
            thumbnail_label.image_path = image_path

            if self.in_delete_mode:
                thumbnail_label.mousePressEvent = lambda event, img_id=image_id: self.toggle_image_selection(img_id)
            elif self.in_download_mode:
                thumbnail_label.mousePressEvent = lambda event, img_id=image_id: self.toggle_image_selection(img_id)
            elif self.in_reid_mode:
                thumbnail_label.mousePressEvent = lambda event, img_id=image_id: self.toggle_image_selection(img_id)
            else:
                thumbnail_label.mousePressEvent = lambda event, image=self.image_list[i]: self.open_image_popup(image)

            container_widget = QWidget()
            container_layout = QVBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(thumbnail_label, alignment=Qt.AlignCenter)

            self.thumbnail_layout.addWidget(container_widget, row, col)
            col += 1
            if col >= 5:
                col = 0
                row += 1

        self.update_pagination()

    def update_pagination(self):
        """
        Updates the pagination controls based on the current page and total number of images.
        It enables or disables the pagination buttons and displays the appropriate page buttons
        based on the current selection.
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
        """Navigate to the last page of the image list."""
        total_pages = max(1, (len(self.image_list) + self.images_per_page - 1) // self.images_per_page)
        self.go_to_page(total_pages - 1)

    def go_to_first_page(self):
        """Navigate to the first page of the image list."""
        self.current_page = 0
        self.update_thumbnails()

    def go_to_page(self, page_num):
        """Navigate to a specific page of the image list."""
        try:
            total_pages = max(1, (len(self.image_list) + self.images_per_page - 1) // self.images_per_page)

            if 0 <= page_num < total_pages:
                self.current_page = page_num
                self.update_thumbnails()
            else:
                QMessageBox.warning(self, "Invalid Page", f"Please enter a number between 1 and {total_pages}.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")

    def toggle_mode(self, mode):
        """Toggle the selected mode (delete, download, or reID).

        Args:
            mode (str): The mode to toggle ('delete', 'download', or 'reid').
        """
        if mode == "delete":
            if not self.in_delete_mode:
                self.in_delete_mode = True
                self.delete_button.setText("Cancel")
                self.download_button.setVisible(False)
                self.reid_button.setVisible(False)
                self.add_controls(mode)
            else:
                self.in_delete_mode = False
                self.delete_button.setText("Delete Images")
                self.download_button.setVisible(True)
                self.reid_button.setVisible(True)
                self.remove_controls(mode)

        elif mode == "download":
            if not self.in_download_mode:
                self.in_download_mode = True
                self.download_button.setText("Cancel")
                self.delete_button.setVisible(False)
                self.reid_button.setVisible(False)
                self.add_controls(mode)
            else:
                self.in_download_mode = False
                self.download_button.setText("Download Images")
                self.delete_button.setVisible(True)
                self.reid_button.setVisible(True)
                self.remove_controls(mode)

        elif mode == "reid":
            if not self.in_reid_mode:
                self.in_reid_mode = True
                self.reid_button.setText("Cancel")
                self.delete_button.setVisible(False)
                self.download_button.setVisible(False)
                self.add_controls(mode)
            else:
                self.in_reid_mode = False
                self.reid_button.setText("Run ReID")
                self.download_button.setVisible(True)
                self.delete_button.setVisible(True)
                self.remove_controls(mode)

        self.update_thumbnails()

    def add_controls(self, mode):
        """Add control buttons based on the selected mode.

        Args:
            mode (str): The mode for which to add controls ('delete', 'download', or 'reid').
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

        elif mode == "reid" and not self.confirm_reid_button:
            self.confirm_reid_button = QPushButton("Run on Selected")
            self.confirm_reid_button.setObjectName("reidSelectedButton")
            self.confirm_reid_button.setFixedSize(self.download_button.sizeHint().width() + 80,
                                                      self.download_button.sizeHint().height())
            self.confirm_reid_button.clicked.connect(self.confirm_reid_selected)
            self.confirm_reid_button.setEnabled(False)
            self.button_layout.insertWidget(2, self.confirm_reid_button, alignment=Qt.AlignCenter)


    def remove_controls(self, mode):
        """Remove control buttons based on the selected mode.

        Args:
            mode (str): The mode for which to remove controls ('delete', 'download', or 'reid').
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

        elif mode == "reid" and self.confirm_reid_button:
            self.button_layout.removeWidget(self.confirm_reid_button)
            self.confirm_reid_button.deleteLater()
            self.confirm_reid_button = None

        self.selected_images.clear()

    def toggle_select_all(self, state):
        """Toggle the selection of all images based on the state of the 'Select All' checkbox.

        Args:
            state (int): The state of the checkbox (checked or unchecked).
        """
        if state == Qt.Checked:
            for image in self.image_list:
                self.selected_images.add(image[0])
        else:
            self.selected_images.clear()

        if self.in_delete_mode:
            self.confirm_delete_button.setEnabled(bool(self.selected_images))

        if self.in_download_mode:
            self.confirm_download_button.setEnabled(bool(self.selected_images))

        if self.in_reid_mode:
            self.confirm_reid_button.setEnabled(bool(self.selected_images))

        self.update_thumbnails()

    def toggle_image_selection(self, image_id):
        """Toggle the selection of a specific image.

        Args:
            image_id (int): The ID of the image to toggle.
        """
        if image_id in self.selected_images:
            self.selected_images.remove(image_id)
        else:
            self.selected_images.add(image_id)

        self.update_thumbnails()

        if self.in_delete_mode:
            self.confirm_delete_button.setEnabled(bool(self.selected_images))

        if self.in_download_mode:
            self.confirm_download_button.setEnabled(bool(self.selected_images))

        if self.in_reid_mode:
            self.confirm_reid_button.setEnabled(bool(self.selected_images))

    def confirm_delete_selected(self):
        """Confirm deletion of selected images and delete them if confirmed."""
        if self.selected_images:
            confirmation = QMessageBox.question(self, "Confirm Delete",
                                                f"Are you sure you want to delete {len(self.selected_images)} images?",
                                                QMessageBox.Yes | QMessageBox.No)
            if confirmation == QMessageBox.Yes:
                deleted_images = []
                for image_id in self.selected_images:
                    image_data = self.db_helper.fetch_image_path_by_id(image_id)

                    if image_data is not None:
                        bbox_image_path, crop_image_path, thumbnail_path = image_data

                        if os.path.exists(bbox_image_path):
                            os.remove(bbox_image_path)
                        if os.path.exists(crop_image_path):
                            os.remove(crop_image_path)
                        if os.path.exists(thumbnail_path):
                            os.remove(thumbnail_path)

                        self.db_helper.delete_image(image_id)
                        deleted_images.append(image_id)

                self.selected_images.clear()

                self.in_delete_mode = False
                self.delete_button.setText("Delete Images")
                self.remove_controls("delete")

                self.image_list = [img for img in self.image_list if img[0] not in deleted_images]

                self.update_thumbnails()
                self.delete_button.setEnabled(True)
                self.download_button.setEnabled(True)
                self.reid_button.setEnabled(True)
                self.delete_button.setVisible(True)
                self.reid_button.setVisible(True)
                self.download_button.setVisible(True)
                self.refresh_tree()
                self.reload_tree_widget()
                self.reid_database.populate_tree()
                self.reid_database.update_image_grid()

    def confirm_reid_selected(self):
        """Confirm ReID process for selected images and handle the execution."""
        self.reid_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.reid_worker = ReIDWorker(self.selected_images, self.db_helper)

        self.reid_worker.progress_updated.connect(self.update_progress_bar)
        self.reid_worker.reid_finished.connect(self.handle_reid_finished)

        self.reid_worker.start()

    def update_progress_bar(self, value):
        """Update the progress bar label with the current progress value.

        Args:
            value (int): The current progress percentage.
        """
        self.progress_label.setText(f"Progress: {value}%")


    def handle_reid_finished(self, output):
        """Handle the completion of the ReID process.

        Args:
            output (dict): A dictionary where keys are ReID IDs and values are lists of images.
        """
        path = "app/detection_model/temporary_detected_images/crop_images/"
        run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for reid_id, images in output.items():
            for image in images:
                full_path = path + image
                id = self.db_helper.fetch_id_by_path(full_path)
                self.db_helper.insert_reid_result(image, id, reid_id, run_datetime)
        self.reid_database.populate_tree()
        self.selected_images.clear()
        self.in_reid_mode = False
        self.reid_button.setText("Run ReID")
        self.remove_controls("reid")
        self.delete_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.reid_button.setEnabled(True)
        self.delete_button.setVisible(True)
        self.reid_button.setVisible(True)
        self.download_button.setVisible(True)
        self.update_thumbnails()
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")

    def refresh_thumbnails_after_delete(self):
        """Refresh the thumbnail display after deleting selected images."""
        self.image_list = [img for img in self.image_list if img[0] not in self.selected_images]
        self.update_thumbnails()

    def confirm_download_selected(self):
        """Confirm and execute the download of selected images."""
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
                    image_data = self.db_helper.fetch_image_path_by_id(image_id)

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
        self.delete_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.reid_button.setEnabled(True)
        self.delete_button.setVisible(True)
        self.reid_button.setVisible(True)
        self.download_button.setVisible(True)
        self.update_thumbnails()

    def prev_page(self):
        """Navigate to the previous page of the image list, if possible."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_thumbnails()

    def next_page(self):
        """Navigate to the next page of the image list, if possible."""
        if (self.current_page + 1) * self.images_per_page < len(self.image_list):
            self.current_page += 1
            self.update_thumbnails()

    def clear_thumbnail_display(self):
        """Clear all thumbnails from the display."""
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def open_image_popup_event(self, event):
        """Handle the event when an image thumbnail is clicked to open a popup.

        Args:
            event (QEvent): The event triggered by clicking the thumbnail.
        """
        image = event.widget().image
        self.open_image_popup(image)

    def open_image_popup(self, image):
        """Open a popup dialog to display the full image and its details.

        Args:
            image (tuple): A tuple containing image details including the path and metadata.
        """
        popup = QDialog(self, Qt.Window)
        popup.setWindowTitle("Full Image")
        popup.setGeometry(100, 100, 800, 600)
        main_layout = QVBoxLayout(popup)

        image_label = QLabel(popup)
        pixmap = QPixmap(image[2])
        image_label.setPixmap(pixmap.scaled(popup.width(), popup.height() - 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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

    def refresh_tree(self):
        """Refresh the tree view to show updated thumbnails."""
        self.update_thumbnails()

    def reload_tree_widget(self):
        """Reload the tree widget by clearing and repopulating it."""
        self.tree_widget.clear()
        self.populate_tree()
