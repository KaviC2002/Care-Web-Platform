import multiprocessing
from concurrent.futures import ProcessPoolExecutor

from PyQt5.QtWidgets import QApplication, QSpacerItem, QFrame, QSizePolicy, QHBoxLayout, QDialog, QWidget, QVBoxLayout, \
    QLabel, QPushButton, QFileDialog, QProgressBar, QMessageBox, QGridLayout
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap
from datetime import datetime

import os
import zipfile
import cv2
import time

from app.detection_model.detection import main as detection_main
from app.util.generate_thumbnail import generate_thumbnail
from app.util.database_helper import DatabaseHelper
from app.app_pages.MapPopup import MapPopup
from app.databases import conn

# Determine the number of CPU cores and set maximum workers for image processing
num_cores = multiprocessing.cpu_count()
if num_cores > 1:
    max_workers = num_cores // 2
else:
    max_workers = 1

def process_image_func(index, image_path, temp_images_dir, group_name, user):
    """
    Process a single image for object detection and save results.

    Args:
        index (int): The index of the image in the list of images.
        image_path (str): The path to the image file.
        temp_images_dir (str): The directory to store temporary images.
        group_name (str): The group name associated with the images.
        user (str): The user requesting the processing.

    Returns:
        tuple: A tuple containing paths to the bounding box image and cropped image, confidence score,
               and updated group name. Returns None if the image cannot be processed.
    """
    loaded_image = cv2.imread(image_path)
    image_filename = os.path.basename(image_path)
    image_name, _ = os.path.splitext(image_filename)
    if loaded_image is None:
        return None

    result = detection_main([loaded_image])
    if not result:
        return None

    bbox_image, crop_image, label, confidence = result[0]
    #user = "TestUser"
    upload_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    confidence_str = f"{confidence:.3f}"

    bbox_image_path = os.path.join(temp_images_dir, 'bbox_images', f"bbox_{user}_{upload_date}_{confidence_str}_{image_name}.jpg")
    crop_image_path = os.path.join(temp_images_dir, 'crop_images', f"crop_{user}_{upload_date}_{confidence_str}_{image_name}.jpg")

    cv2.imwrite(bbox_image_path, bbox_image)
    cv2.imwrite(crop_image_path, crop_image)

    thumbnail_dir = os.path.join(temp_images_dir, 'thumbnails')
    thumbnail_path = generate_thumbnail(bbox_image_path, thumbnail_dir)

    group_name = group_name + " " + label

    return bbox_image_path, crop_image_path, confidence, group_name

class ImageProcessingWorker(QThread):
    """
    A worker class for processing images in a separate thread using a process pool.

    Signals:
        progress (int, str): Emitted to indicate processing progress with current count and estimated time remaining.
        result_ready (list): Emitted when processing is complete with the list of processed images.
        processing_complete: Emitted when all images have been processed.

    Args:
        images (list): List of images to be processed.
        temp_images_dir (str): Temporary directory for storing processed images.
        user (str): The user requesting the processing.
    """
    progress = pyqtSignal(int, str)
    result_ready = pyqtSignal(list)
    processing_complete = pyqtSignal()

    def __init__(self, images, temp_images_dir, user):
        super().__init__()
        self.images = images  # List of images to process
        self.temp_images_dir = temp_images_dir  # Directory for temporary images
        self.processed_images = []
        self.start_time = None  # To record the start time of processing
        self.current_user = user

    def run(self):
        """
        Run the image processing in a separate thread.
        This method will be called when the thread starts.
        """
        self.start_time = time.time()
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for index, (image_path, _, _, group_name) in enumerate(self.images):
                futures.append(executor.submit(process_image_func, index, image_path, self.temp_images_dir, group_name, self.current_user))

            for i, future in enumerate(futures):
                result = future.result()
                if result:
                    self.processed_images.append(result)
                elapsed_time = time.time() - self.start_time
                images_processed = i + 1
                avg_time_per_image = elapsed_time / images_processed
                remaining_time = avg_time_per_image * (len(self.images) - images_processed)
                remaining_time_str = f"Processing image {images_processed} of {len(self.images)}. Estimated remaining time: {int(remaining_time // 60)}m {int(remaining_time % 60)}s"
                self.progress.emit(i + 1, remaining_time_str)

        self.result_ready.emit(self.processed_images)
        self.processing_complete.emit()


class UploadPage(QWidget):
    """
    A QWidget for uploading images to identify wildlife.

    Signals:
        images_saved_signal: Emitted when images are successfully saved to the database.

    Args:
        user (str): The user uploading the images.
        database_page: Reference to the database page for data handling.
    """

    images_saved_signal = pyqtSignal()

    def __init__(self, user, database_page):
        super().__init__()
        self.db_helper = DatabaseHelper()
        self.current_user = user
        self.load_stylesheet()
        self.database_page = database_page

        # Setup layout for the upload page
        self.UploadPage_layout = QVBoxLayout()
        self.UploadPage_layout.setSpacing(10)

        self.UploadPage_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        label = QLabel("Upload Images to Identify Wildlife")
        label.setObjectName("titleLabel")
        self.UploadPage_layout.addWidget(label, alignment=Qt.AlignCenter)

        upload_button_layout = QHBoxLayout()

        self.upload_button = QPushButton("Upload Images")
        self.upload_button.setObjectName("uploadButtonProcess")
        self.upload_button.setFixedSize(self.upload_button.sizeHint().width() + 80, self.upload_button.sizeHint().height() + 20)
        self.upload_button.clicked.connect(self.upload_images)
        upload_button_layout.addWidget(self.upload_button)

        self.clear_upload_button = QPushButton("Clear Images")
        self.clear_upload_button.setObjectName("clearUploadButton")
        self.clear_upload_button.setFixedSize(self.upload_button.sizeHint().width() + 80, self.upload_button.sizeHint().height() + 20)
        self.clear_upload_button.clicked.connect(self.clear_uploaded_images)
        upload_button_layout.addWidget(self.clear_upload_button)

        self.clear_upload_button.setEnabled(False)

        button_container = QWidget()
        button_container.setLayout(upload_button_layout)

        self.UploadPage_layout.addWidget(button_container, alignment=Qt.AlignCenter)

        self.process_button = QPushButton("Process Images")
        self.process_button.setObjectName("processButton")
        self.process_button.setFixedSize(self.upload_button.sizeHint().width() + 80, self.upload_button.sizeHint().height() + 20)
        self.process_button.clicked.connect(self.process_images)
        self.process_button.setEnabled(False)
        self.UploadPage_layout.addWidget(self.process_button, alignment=Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.UploadPage_layout.addWidget(self.progress_bar)

        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setObjectName("thumbnailFrame")
        self.thumbnail_frame.setFixedHeight(360)
        self.thumbnail_layout = QGridLayout(self.thumbnail_frame)
        self.thumbnail_layout.setAlignment(Qt.AlignTop)
        self.UploadPage_layout.addWidget(self.thumbnail_frame)

        self.thumbnail_size = (150, 150)
        self.images_per_page = 10

        self.save_button = QPushButton("Save Images to Database")
        self.save_button.setObjectName("saveButton")
        self.save_button.setFixedSize(self.upload_button.sizeHint().width() + 100,
                                      self.upload_button.sizeHint().height() + 20)
        self.save_button.clicked.connect(self.save_images_to_database)
        self.save_button.setEnabled(False)
        self.UploadPage_layout.addWidget(self.save_button, alignment=Qt.AlignCenter)

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

        self.UploadPage_layout.addLayout(self.pagination_layout)



        self.UploadPage_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(self.UploadPage_layout)

        self.temp_images_dir = os.path.join('app', 'detection_model', 'temporary_detected_images')
        os.makedirs(self.temp_images_dir, exist_ok=True)

        self.images = []
        self.processed_images = []
        self.group_data = []

        self.current_page = 0
        self.images_per_page = 10
        self.thumbnail_size = (150, 150)

        self.image_list = []

        self.update_button_states('upload')

    def load_stylesheet(self):
        """
        Loads the CSS stylesheet for the upload page from the specified file.

        The CSS file is located in the 'css' directory relative to the current file's directory.
        The stylesheet is then applied to the current widget.
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'upload_page.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())

    def upload_images(self):
        """
        Opens a file dialog to select a folder containing images and uploads those images.

        The function searches for image files with specific extensions (.png, .jpg, .jpeg)
        in the selected folder and its subfolders. It organizes the images by their folder name
        and the current timestamp, then updates the image list and UI elements accordingly.

        Displays a warning if no images are found in the selected folder.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with Images")

        if folder:
            image_extensions = ['.png', '.jpg', '.jpeg']
            new_images = []

            for root, dirs, files in os.walk(folder):

                folder_name = os.path.basename(root)
                current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')
                group_name = f'{folder_name}_{current_datetime}'
                images_in_folder = 0 

                for file in files:
                    if os.path.splitext(file)[1].lower() in image_extensions:
                        image_path = os.path.join(root, file)
                        new_images.append((image_path, None, None, group_name))
                        images_in_folder += 1
                
                if images_in_folder > 0:
                    self.group_data.append(group_name)

            if not new_images:
                QMessageBox.warning(self, "No Images Found", "The selected folder does not contain any image files.")
                return

            self.image_list.extend(new_images)

            self.clear_thumbnails()
            self.update_thumbnails()

            self.upload_button.setText("Upload More Images")
            self.clear_upload_button.setEnabled(True)

            self.update_button_states('process')
    
    def clear_uploaded_images(self):
        """
        Clears all uploaded images from the UI and resets the related data.

        Displays a confirmation dialog to the user before clearing the images. If confirmed,
        the image list, group data, and UI elements are reset to their initial state.
        """
        confirmation = QMessageBox.question(self, "Clear Uploaded Images", "Are you sure you want to clear all uploaded images?", 
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if confirmation == QMessageBox.Yes:
            self.image_list = []
            self.group_data = []
            self.clear_thumbnails()
            self.clear_upload_button.setEnabled(False)
            self.upload_button.setText("Upload Images")
            self.update_button_states('upload')
            QMessageBox.information(self, "Cleared", "Uploaded images have been cleared.")

    def process_images(self):
        """
        Processes the uploaded images for further operations.

        Clears the current thumbnails, prepares directories for processed images,
        and initializes the progress bar. If no images are uploaded, a warning is displayed.
        Starts the image processing worker to handle the actual processing of images.
        """
        self.clear_thumbnails()
        thumbnail_dir = os.path.join(self.temp_images_dir, 'thumbnails')
        self.clear_non_detected_thumbnails(thumbnail_dir)

        if not self.image_list:
            QMessageBox.warning(self, "No Images", "Please upload images before processing...")
            return
        
        for i in range(self.pagination_layout.count()):
                widget = self.pagination_layout.itemAt(i).widget()
                if widget is not None:
                    widget.setVisible(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.image_list))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Processing... Estimating remaining time.")

        bbox_dir = os.path.join(self.temp_images_dir, 'bbox_images')
        crop_dir = os.path.join(self.temp_images_dir, 'crop_images')
        thumbnail_dir = os.path.join(self.temp_images_dir, 'thumbnails')

        os.makedirs(bbox_dir, exist_ok=True)
        os.makedirs(crop_dir, exist_ok=True)
        os.makedirs(thumbnail_dir, exist_ok=True)

        self.worker = ImageProcessingWorker(self.image_list, self.temp_images_dir, self.current_user)

        self.worker.progress.connect(self.update_progress)
        self.worker.result_ready.connect(self.handle_processed_images)
        self.worker.processing_complete.connect(self.on_processing_complete)

        self.worker.start()

    def update_progress(self, index, value):
        """
        Updates the progress bar based on the current processing state.

        Args:
            index (int): The index of the current image being processed.
            value (str): The status message to display in the progress bar.
        """
        self.progress_bar.setValue(index + 1)
        self.progress_bar.setFormat(value)

    def handle_processed_images(self, processed_images):
        """
        Handles the images that have been processed and updates the UI accordingly.

        Args:
            processed_images (list): A list of processed images.
        """
        self.processed_images = processed_images
        self.image_list = self.processed_images
        self.update_thumbnails()

    def on_processing_complete(self):
        """
        Executes when the image processing is complete.

        Hides the progress bar and updates button states based on the outcome of the processing.
        If no images were processed, it allows for new uploads; otherwise, it prepares to save the images.
        """
        self.progress_bar.setVisible(False)
        if not self.processed_images:
            self.update_button_states('upload')
        else:
            self.update_button_states('save')

    def save_images_to_database(self):
        """
        Saves the processed images to the database after user confirmation.

        Displays a confirmation dialog to the user before proceeding to save the images.
        If confirmed, it initiates the process to handle groups of images.
        """
        confirmation = QMessageBox.question(self, "Confirmation", "Do you want to save the images to the database?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if confirmation == QMessageBox.Yes:
            self.current_group_index = 0
            self.process_next_group()
        self.database_page.reload_tree_widget()
        self.database_page.populate_animal_combobox()
    
    def process_next_group(self):
        """
        Processes the next group of images for saving to the database.

        Iterates through the list of image groups, prompts the user for location,
        and saves the images accordingly. If all groups are processed, it emits a signal
        and displays a completion message.
        """
        while self.current_group_index < len(self.group_data):
            group_name = self.group_data[self.current_group_index]
            group_images = [image for image in self.processed_images if image[3].rsplit(' ',1)[0] == group_name]

            if group_images:
                map_view = MapPopup(group_name)
                map_view.location_selected_signal.connect(self.store_images_with_location)
                map_view.exec_()
                return

            self.current_group_index += 1

        self.images_saved_signal.emit()
        self.clear_thumbnails()
        self.processed_images.clear()
        self.group_data.clear()
        self.update_pagination()
        self.save_button.setEnabled(False)
        QMessageBox.information(self, "Save Complete", "Processed images have been saved to the local database.")
        self.show_download_popup()
        self.upload_button.setText("Upload Images")
        self.update_button_states('upload')
    
    def store_images_with_location(self, location):
        """
        Stores images in the database with the specified location information.

        Args:
            location (str): The location information provided by the user.
        """
        thumbnail_dir = os.path.join(self.temp_images_dir, 'thumbnails')
        group_name = self.group_data[self.current_group_index]

        group_images = [image for image in self.processed_images if image[3].rsplit(' ',1)[0] == group_name]

        for bbox_image_path, crop_image_path, confidence, group_name in group_images:
            thumbnail_path = os.path.join(thumbnail_dir, os.path.basename(bbox_image_path))
            user = self.current_user
            location_str = str(location)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            group_name_cleaned, animal = group_name.rsplit(' ', 1)
            self.db_helper.insert_image(user, bbox_image_path, crop_image_path, thumbnail_path, location_str, upload_date, confidence, group_name_cleaned, animal)

        self.current_group_index += 1
        self.process_next_group()

    def show_download_popup(self):
        """
        Displays a confirmation dialog asking the user if they would like to download processed images as a zip file.

        If the user confirms, it calls the download_images() method to proceed with the download.
        """
        download_prompt = QMessageBox.question(self, "Download Images", "Would you like to download the images as a zip file?",
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if download_prompt == QMessageBox.Yes:
            self.download_images()

    def download_images(self):
        """
        Initiates the process to download processed images as a zip file.

        Opens a dialog for the user to select a folder to save the zip file. If a folder is selected,
        it creates a zip file named 'processed_images.zip' in the chosen directory, containing all
        processed images.

        If the download is successful, a message box is displayed indicating the completion and the
        save location.

        Raises:
            OSError: If there is an error creating the zip file or writing images to it.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Save Processed Images")

        if folder:
            zip_path = os.path.join(folder, "processed_images.zip")
            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                for image_path, _ in self.processed_images:
                    zip_file.write(image_path, os.path.basename(image_path))
            QMessageBox.information(self, "Download Complete", f"Processed images have been saved to {zip_path}.")

    def update_thumbnails(self):
        """
        Updates the displayed thumbnails of images based on the current pagination state.

        Clears any existing thumbnails and retrieves a new set of images to display based on the
        current page and the number of images allowed per page. It generates and displays
        thumbnails for the images in the specified range.

        Thumbnails include hover effects and are wrapped in a container for layout management.
        Pagination is updated accordingly after loading the thumbnails.
        """
        self.clear_thumbnails()

        start_index = self.current_page * self.images_per_page
        end_index = min(start_index + self.images_per_page, len(self.image_list))

        row, col = 0, 0
        thumbnail_dir = os.path.join(self.temp_images_dir, 'thumbnails')

        for i in range(start_index, end_index):
            image_path, _, _, _ = self.image_list[i]
            thumbnail_path = os.path.join(thumbnail_dir, os.path.basename(image_path))

            if not os.path.exists(thumbnail_path):
                thumbnail_path = generate_thumbnail(image_path, thumbnail_dir)

            thumbnail_label = QLabel()
            pixmap = QPixmap(thumbnail_path)
            thumbnail_label.setPixmap(pixmap)
            thumbnail_label.setFixedSize(*self.thumbnail_size)
            thumbnail_label.mousePressEvent = lambda event, path=image_path: self.open_image_popup(path)

            overlay_label = QLabel(thumbnail_label)
            overlay_label.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
            overlay_label.setFixedSize(*self.thumbnail_size)

            def enter_event(event, lbl=overlay_label):
                lbl.setStyleSheet("background-color: rgba(0, 0, 0, 0.4);")

            def leave_event(event, lbl=overlay_label):
                lbl.setStyleSheet("background-color: rgba(0, 0, 0, 0);")

            thumbnail_label.enterEvent = enter_event
            thumbnail_label.leaveEvent = leave_event

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
        Updates the pagination controls based on the current page state and total number of images.

        This method enables or disables pagination buttons (first, previous, next, last) based on
        the current page and total pages calculated from the total number of images. It dynamically
        creates page number buttons for quick navigation and updates their visual state based on the
        current selection.
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
        Navigates the view to the last page of images.

        Calculates the total number of pages and invokes the go_to_page() method to
        set the current page to the last one.
        """
        total_pages = max(1, (len(self.image_list) + self.images_per_page - 1) // self.images_per_page)
        self.go_to_page(total_pages - 1)

    def go_to_first_page(self):
        """
        Navigates the view to the first page of images.

        Resets the current page index to zero and updates the thumbnail display accordingly.
        """
        self.current_page = 0
        self.update_thumbnails()

    def go_to_page(self, page_num):
        """
        Changes the current page to the specified page number.

        Validates the page number and updates the thumbnail display. If the page number
        is invalid, a warning message is shown to the user.

        Args:
            page_num (int): The page number to navigate to.

        Raises:
            ValueError: If page_num is not a valid page index.
        """
        try:
            total_pages = max(1, (len(self.image_list) + self.images_per_page - 1) // self.images_per_page)

            if 0 <= page_num < total_pages:
                self.current_page = page_num
                self.update_thumbnails()
            else:
                QMessageBox.warning(self, "Invalid Page", f"Please enter a number between 1 and {total_pages}.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")

    def clear_thumbnails(self):
        """
        Clears all currently displayed thumbnails from the layout.

        Iterates through the thumbnail layout and deletes all thumbnail widgets, freeing memory.
        After clearing, it processes events to update the UI.
        """
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        QApplication.processEvents()
    
    def clear_non_detected_thumbnails(self, thumbnail_dir):
        """
        Removes all non-detected thumbnails from the specified directory.

        Iterates through the thumbnail directory and deletes any files that do not start with "bbox_".

        Args:
            thumbnail_dir (str): The directory containing thumbnails to clear.
        """
        for file_name in os.listdir(thumbnail_dir):
            if not file_name.startswith("bbox_"):
                file_path = os.path.join(thumbnail_dir, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)

    def prev_page(self):
        """
        Navigates to the previous page of images if not currently on the first page.

        Decreases the current page index by one and updates the thumbnail display.
        """

        if self.current_page > 0:
            self.current_page -= 1
            self.update_thumbnails()

    def next_page(self):
        """
        Navigates to the next page of images if there are more pages available.

        Increases the current page index by one and updates the thumbnail display.
        """
        if (self.current_page + 1) * self.images_per_page < len(self.image_list):
            self.current_page += 1
            self.update_thumbnails()

    def open_image_popup(self, image_path):
        """
        Opens a dialog displaying the selected full-size image.

        Creates a new dialog, sets its title and size, and displays the specified image
        in a QLabel, maintaining the aspect ratio.

        Args:
            image_path (str): The path to the image to be displayed.
        """
        popup = QDialog(self, Qt.Window)
        popup.setWindowTitle("Full Image")
        popup.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout(popup)
        image_label = QLabel(popup)
        pixmap = QPixmap(image_path)
        image_label.setPixmap(pixmap.scaled(popup.width(), popup.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        layout.addWidget(image_label)
        popup.setLayout(layout)
        popup.show()

    def update_button_states(self, stage):
        """
        Updates the states of various buttons based on the current stage of the image processing workflow.

        The method adjusts the enabled state, text, and styling of the upload, process, and save buttons
        depending on the specified stage. Additionally, it manages the visibility of pagination layout items.

        Args:
            stage (str): The current stage of the workflow. Accepted values are:
                - 'upload': Indicates that images are ready to be uploaded.
                - 'process': Indicates that images are currently being processed.
                - 'save': Indicates that images have been processed and are ready to be saved.
                - 'complete': Indicates that the processing is complete.

        Raises:
            ValueError: If the provided stage is not one of the accepted values.
        """
        if stage == 'upload':
            self.upload_button.setEnabled(True)
            self.upload_button.setObjectName("uploadButtonHighlighted")
            self.upload_button.setText("Upload Images")
            self.upload_button.setStyleSheet("")

            self.process_button.setEnabled(False)
            self.save_button.setEnabled(False)

        elif stage == 'process':
            self.upload_button.setEnabled(True)
            self.upload_button.setObjectName("uploadButtonDefault")
            self.upload_button.setText("Upload More Images")
            self.upload_button.setStyleSheet("")

            self.process_button.setEnabled(True)
            self.save_button.setEnabled(False)

        elif stage == 'save':
            self.upload_button.setEnabled(False)
            self.clear_upload_button.setEnabled(False)
            self.upload_button.setText("Upload More Images")

            for i in range(self.pagination_layout.count()):
                widget = self.pagination_layout.itemAt(i).widget()
                if widget is not None:
                    widget.setVisible(True)

            self.process_button.setEnabled(False)
            self.save_button.setEnabled(True)

        elif stage == 'complete':
            self.upload_button.setEnabled(True)
            self.upload_button.setText("Upload More Images")

            self.process_button.setEnabled(False)
            self.save_button.setEnabled(False)
