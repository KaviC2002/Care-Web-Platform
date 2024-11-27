import multiprocessing
import random
import tempfile
import time
from datetime import datetime
import os
import zipfile
from dotenv import load_dotenv
import boto3
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame, QPushButton, QMessageBox, QHBoxLayout, \
    QProgressBar, QSizePolicy, QTreeWidgetItem, QDialog, QCheckBox, QFileDialog, QComboBox
from PyQt5.QtGui import QPixmap
from botocore.exceptions import NoCredentialsError
from sqlalchemy.orm import sessionmaker
from PIL import Image
import io
# from app.databases.conn import engine, get_user_id
from app.databases import model, conn
from app.databases.model import Photo
from app.util.database_helper import DatabaseHelper
from app.databases.conn import OnlineDatabase

load_dotenv()
connection = OnlineDatabase()

# Drop all tables in the online database (if necessary) and recreate them.
# This might be part of initialization or a migration step.
# connection.drop_all_tables()
# connection.create_tables()

# Retrieve AWS credentials from environment variables.
access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
access_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

# Set up a session using SQLAlchemy for database interactions.
Session = sessionmaker(bind=conn.engine)


class UploadThread(QThread):
    """Thread class for handling image upload to S3 and database synchronization in the background."""
    # Signal to update progress in a GUI application.
    progress_updated = pyqtSignal(int, str)

    def __init__(self, current_user):
        super().__init__()
        # The current user who is uploading the images.
        self.current_user = current_user

        # Initialize an S3 client using the AWS credentials.
        self.s3_client = boto3.client('s3', aws_access_key_id=access_key_id,
                                      aws_secret_access_key=access_secret_key,
                                      region_name='ap-southeast-2')
        # The S3 bucket name where images will be uploaded.
        self.bucket_name = 'carewebbucket'

    def upload_to_s3(self, file_path, s3_key):
        """Method to upload files to S3."""
        try:
            # Upload the file to the specified S3 bucket and path.
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            normalized_file_path = file_path.replace('\\', '/')

            s3_url = f'https://{self.bucket_name}.s3.amazonaws.com/{normalized_file_path}'
            return s3_url
        except NoCredentialsError:
            print("S3 Credentials not available")
            return None

    def run(self):
        """The main method executed when the thread is run."""
        # Create a new database session for this thread.
        session = Session()
        # Helper to interact with the local database for image management.
        local_db = DatabaseHelper()
        # Retrieve all images that need to be synced to the online database.
        unsynced_images = local_db.images_tosync()

        try:
            total_images = len(unsynced_images)
            print(f"Found {total_images} unsynced images. Starting upload...")
            start_time = time.time()

            # Iterate over each unsynced image and upload it to S3.
            for idx, image in enumerate(unsynced_images):
                is_synced = image[9]

                if not is_synced:
                    # print(f"Uploading unsynced image ID {image[0]}...")

                    user = connection.get_user_id(self.current_user)
                    bbox_image_path = image[2]  # Local path to the bounding box image.
                    cropped_image_path = image[3]  # Local path to the cropped image.
                    thumbnail_path = image[4]  # Local path to the thumbnail image.
                    location = image[5]
                    upload_date = image[6]
                    confidence = image[7]
                    group_name = image[8]
                    animal = image[10]
                    # Extract the filename of the bounding box image.
                    bbox_image_filename = os.path.basename(bbox_image_path)
                    extracted_image_name = bbox_image_filename.split('_')[-1]
                    # print(f"Extracted image name: {extracted_image_name}")

                    # Check if this image already exists in the online database.
                    existing_photo = session.query(model.Photo).filter_by(name=extracted_image_name).first()
                    if existing_photo:
                        # If the image exists, mark it as synced in the local database and skip further processing.
                        local_db.mark_image_as_synced(image[0])
                        # print(f"Image '{bbox_image_filename}' already exists in the online database. Skipping upload.")
                        continue

                    # Prepare S3 keys (file paths in the S3 bucket) for each image type.
                    bbox_s3_key = f"images/bbox/{bbox_image_filename}"
                    cropped_s3_key = f"images/cropped/{os.path.basename(cropped_image_path)}"
                    thumbnail_s3_key = f"images/thumbnails/{os.path.basename(thumbnail_path)}"

                    # Upload each image to S3 and retrieve their URLs.
                    bbox_s3_url = self.upload_to_s3(bbox_image_path, bbox_s3_key)
                    cropped_s3_url = self.upload_to_s3(cropped_image_path, cropped_s3_key)
                    thumbnail_s3_url = self.upload_to_s3(thumbnail_path, thumbnail_s3_key)

                    # If all images were uploaded successfully, add the new photo record to the online database.
                    if bbox_s3_url and cropped_s3_url and thumbnail_s3_url:
                        new_photo = model.Photo(
                            user_id=user,
                            image_data=bbox_s3_url,
                            description=f'Cropped Image: {cropped_s3_url}, Thumbnail: {thumbnail_s3_url}',
                            group_name=group_name,
                            location=location,
                            is_synced=True,
                            confidence=confidence,
                            thumbnail=thumbnail_s3_url,
                            bbox=bbox_s3_url,
                            cropped=cropped_s3_url,
                            name=extracted_image_name,
                            animal=animal
                        )

                        # Mark the image as synced in the local database.
                        local_db.mark_image_as_synced(image[0])
                        session.add(new_photo)  # Add the new photo record to the session.

                        # Calculate and emit progress updates.
                        elapsed_time = time.time() - start_time
                        estimated_time = (elapsed_time / (idx + 1)) * (total_images - (idx + 1))

                        # Calculate the percentage of completion and the status message.
                        progress_percentage = (idx + 1) * 100 // total_images
                        status_message = f"{idx + 1}/{total_images} - Estimated Time Remaining: {estimated_time:.1f}s"
                        self.progress_updated.emit(progress_percentage, status_message)

            # Commit the session to save changes in the online database.
            session.commit()
            # print(f'Successfully uploaded {total_images} images to the online database.')

        except Exception as e:
            # If an error occurs, roll back any changes made in the session and print the error.
            session.rollback()
            print(f"Error uploading images: {e}")

        finally:
            # Close the session when done.
            session.close()


class OnlineDatabasePage(QWidget):
    """
        A QWidget that represents a user interface for managing images in an online database.

        This class allows users to upload images to an online database, refresh the database, and manage
        images with options to download, delete, or save them to a local database. It integrates with AWS S3
        for image storage and retrieval, and provides a user-friendly interface for viewing images in a
        paginated format.

        Attributes:
            current_user: The user currently logged in.
            s3_client: An S3 client instance for interacting with AWS S3.
            bucket_name: The name of the S3 bucket used for storing images.
            local_db: An instance of DatabaseHelper for local database operations.
            database_page: A reference to the database page.
            images: A list of fetched images from the database.
            selected_images: A set of selected image links for operations.
            images_per_page: The number of images displayed per page.
            current_page: The current page number in pagination.
            total_pages: The total number of pages for image navigation.
            in_delete_mode: Boolean indicating if the delete mode is active.
            in_download_mode: Boolean indicating if the download mode is active.
            in_reid_mode: Boolean indicating if the save to local database mode is active.

        Methods:
            __init__(user, database_page):
                Initializes the OnlineDatabasePage instance and sets up the user interface.

            init_ui():
                Sets up the user interface components and layout.

            fetch_images_from_db():
                Fetches images from the local database and returns them.

            start_upload_thread():
                Starts a separate thread for uploading photos to the online database.

            update_progress_bar(value, status_message):
                Updates the progress bar and status message during the upload process.

            upload_finished():
                Called when the upload thread finishes; updates the UI accordingly.

            get_pixmap_from_bytes(image_data):
                Converts image data from bytes to a QPixmap object for display.

            update_image_grid():
                Updates the grid of thumbnails based on the current page and selected images.

            toggle_image_selection(link):
                Toggles the selection state of an image for operations like delete or download.

            toggle_mode(mode):
                Toggles the operational mode (delete, download, or save) and updates the UI accordingly.

        Signals:
            No custom signals are defined; however, connections to buttons and actions trigger specific methods.
        """
    def __init__(self, user, database_page):
        """
        Initializes the OnlineDatabasePage instance.

        Args:
            user: The current user object.
            database_page: Reference to the database page for navigation.
        """
        super().__init__()
        self.init_ui()
        self.current_user = user
        self.s3_client = boto3.client('s3', aws_access_key_id=access_key_id,
                                      aws_secret_access_key=access_secret_key,
                                      region_name='ap-southeast-2')
        self.bucket_name = 'carewebbucket'
        self.local_db = DatabaseHelper()
        self.database_page = database_page

    def init_ui(self):
        """
        Sets up the user interface components and layout for the Online Database Page.
        This includes initializing buttons, comboboxes, progress bars, and layouts.
        """
        self.load_stylesheet()
        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)

        self.tw = QtWidgets.QTreeWidget()
        self.tw.setColumnCount(1)
        self.tw.setObjectName("onlineImagesTree")
        self.tw.setHeaderLabels(["Date"])
        self.layout.addWidget((self.tw))

        self.button_combobox_layout = QHBoxLayout()
        self.button_combobox_layout.setAlignment(Qt.AlignCenter)

        self.upload_button = QPushButton('Upload Photos to Online DB', self)
        self.upload_button.setObjectName("uploadButton")
        self.upload_button.setFixedSize(self.upload_button.sizeHint().width() + 150,
                                        self.upload_button.sizeHint().height() + 10)
        self.upload_button.clicked.connect(self.start_upload_thread)
        self.button_combobox_layout.addWidget(self.upload_button)
        # self.layout.addWidget(self.upload_button, alignment=Qt.AlignCenter)

        self.animal_combobox = QComboBox(self)
        self.animal_combobox.setObjectName("animalDropDown")
        self.animal_combobox.setFixedSize(200, 30)
        self.animal_combobox.addItem("All")
        self.populate_animal_combobox()
        self.animal_combobox.currentIndexChanged.connect(self.update_grid_by_animal)
        self.button_combobox_layout.addWidget(self.animal_combobox)

        self.refresh_button = QPushButton("Refresh Database")
        self.refresh_button.setObjectName("downloadButton")
        self.refresh_button.clicked.connect(self.refresh_database)
        self.refresh_button.setFixedSize(self.refresh_button.sizeHint().width() + 50,
                                         self.refresh_button.sizeHint().height() + 10)
        self.button_combobox_layout.addWidget(self.refresh_button)
        self.layout.addLayout(self.button_combobox_layout)

        # self.layout.addWidget(self.animal_combobox, alignment=Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setVisible(False)
        self.layout.addWidget(self.status_label)

        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setObjectName("thumbnailFrame")
        self.thumbnail_frame.setFixedHeight(360)
        self.thumbnail_layout = QGridLayout(self.thumbnail_frame)
        self.thumbnail_layout.setAlignment(Qt.AlignTop)
        self.layout.addWidget(self.thumbnail_frame)

        self.images_per_page = 10
        self.current_page = 0
        self.total_pages = 0
        self.thumbnail_size = (150, 150)

        self.images = []
        self.original_images = []
        self.selected_images = set()
        self.total_pages = max(1, (len(self.images) + self.images_per_page - 1) // self.images_per_page)

        self.select_all_checkbox = None
        self.in_delete_mode = False
        self.confirm_delete_button = None
        self.in_download_mode = False
        self.confirm_download_button = None
        self.confirm_reid_button = None
        self.in_reid_mode = False

        self.download_button = QPushButton("Download Images")
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(lambda: self.toggle_mode("download"))
        self.download_button.setFixedSize(self.download_button.sizeHint().width() + 50,
                                          self.download_button.sizeHint().height() + 10)
        self.download_button.setEnabled(False)

        self.reid_button = QPushButton("Save to Local Database")
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

        self.populate_tree_with_dates_and_folder()
        self.tw.itemClicked.connect(self.tree_click)

    def fetch_images_from_db(self):
        """
        Fetches all image thumbnails from the database.

        Returns:
        list: A list of thumbnail images retrieved from the database.
        """
        session = Session()
        images = session.query(model.Photo.thumbnail).all()
        session.close()
        return images

    def start_upload_thread(self):
        """
        Initializes and starts a new upload thread for uploading photos.
        It sets the progress bar visibility and connects signals to update
        the UI based on the upload progress and completion.
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.upload_thread = UploadThread(self.current_user)
        self.upload_thread.progress_updated.connect(self.update_progress_bar)
        self.upload_thread.finished.connect(self.upload_finished)
        self.upload_thread.start()

    def update_progress_bar(self, value, status_message):
        """
        Updates the progress bar and the status message displayed to the user.

        Args:
            value (int): The current progress value (0 to 100).
            status_message (str): A message indicating the status of the upload.
        """
        self.progress_bar.setValue(value)
        print(status_message)
        self.progress_bar.setFormat(status_message)
        self.status_label.setText(status_message)

    def upload_finished(self):
        """
        Handles actions to be performed after the upload is completed.
        It updates the UI, shows a message box, and refreshes the image list.
        """
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        QMessageBox.information(self, "Upload Complete", "All photos have been uploaded successfully!")
        self.update_sync_status()
        self.tw.clear()
        self.populate_tree_with_dates_and_folder()
        self.animal_combobox.clear()
        self.populate_animal_combobox()
        self.images = self.fetch_images_from_db()
        self.total_pages = max(1, (len(self.images) + self.images_per_page - 1) // self.images_per_page)
        # self.update_image_grid()

    def get_pixmap_from_bytes(self, image_data):
        """
        Converts image byte data to a QPixmap.

        Args:
            image_data (bytes): The raw byte data of the image.

        Returns:
            QPixmap: A QPixmap object representing the image, or None if an error occurred.
        """
        try:
            image = Image.open(io.BytesIO(image_data[0]))
            byte_array = io.BytesIO()
            image.save(byte_array, format='PNG')
            pixmap = QPixmap()
            pixmap.loadFromData(byte_array.getvalue())
            return pixmap
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    def update_image_grid(self):
        """
        Updates the grid of images displayed in the UI based on the current page
        and the selected images. It manages the layout and applies styles based on the
        current modes (delete, download, reid).
        """

        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        start_index = self.current_page * self.images_per_page
        end_index = min(start_index + self.images_per_page, len(self.images))

        row, col = 0, 0
        for i in range(start_index, end_index):
            thumbnail_label = QLabel()
            image_data = self.images[i]
            pixmap = QPixmap()
            pixmap.loadFromData(self.fetch_image_from_s3(image_data))
            if pixmap:
                thumbnail_label.setPixmap(pixmap)
                thumbnail_label.setFixedSize(*self.thumbnail_size)

                link = image_data[0]
                if link in self.selected_images:
                    if self.in_delete_mode:
                        thumbnail_label.setStyleSheet("border: 3px solid red;")
                    elif self.in_reid_mode:
                        thumbnail_label.setStyleSheet("border: 3px solid blue;")
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

                if self.in_delete_mode or self.in_download_mode or self.in_reid_mode:
                    thumbnail_label.mousePressEvent = lambda event, img_id=link: self.toggle_image_selection(img_id)
                else:
                    thumbnail_label.mousePressEvent = lambda event, image=image_data: self.open_image_popup(image)

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

    def toggle_image_selection(self, link):
        """
        Toggles the selection state of an image based on its link.
        Updates the selected images and UI buttons based on the current mode.

        Args:
            link (str): The link of the image to be toggled.
        """
        if link in self.selected_images:
            self.selected_images.remove(link)
        else:
            self.selected_images.add(link)

        self.update_image_grid()

        if self.in_delete_mode:
            self.confirm_delete_button.setEnabled(bool(self.selected_images))

        if self.in_download_mode:
            self.confirm_download_button.setEnabled(bool(self.selected_images))

        if self.in_reid_mode:
            self.confirm_reid_button.setEnabled(bool(self.selected_images))

    def toggle_mode(self, mode):
        """
        Toggles between different modes (delete, download, reid) in the UI.
        Updates the visibility of buttons and resets the controls based on the selected mode.

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
                self.reid_button.setText("Save to Local Database")
                self.download_button.setVisible(True)
                self.delete_button.setVisible(True)
                self.remove_controls(mode)

        self.update_image_grid()

    def add_controls(self, mode):
        """
        Adds specific control buttons to the UI based on the selected mode.
        These controls allow the user to confirm their actions.

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
            self.button_layout.insertWidget(1, self.confirm_download_button, alignment=Qt.AlignCenter)

        elif mode == "reid" and not self.confirm_reid_button:
            self.confirm_reid_button = QPushButton("Save Selected")
            self.confirm_reid_button.setObjectName("reidSelectedButton")
            self.confirm_reid_button.setFixedSize(self.download_button.sizeHint().width() + 80,
                                                  self.download_button.sizeHint().height())
            self.confirm_reid_button.clicked.connect(self.confirm_reid_selected)
            self.confirm_reid_button.setEnabled(False)
            self.button_layout.insertWidget(2, self.confirm_reid_button, alignment=Qt.AlignCenter)

    def remove_controls(self, mode):
        """
        Removes specific control buttons from the UI based on the selected mode.

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
        """
        Toggles the selection of all images based on the state of the "Select All" checkbox.

        Args:
            state (int): The state of the checkbox (0 for unchecked, 2 for checked).
        """
        if state == Qt.Checked:
            for image in self.images:
                self.selected_images.add(image[0])
        else:
            self.selected_images.clear()

        if self.in_delete_mode:
            self.confirm_delete_button.setEnabled(bool(self.selected_images))

        if self.in_download_mode:
            self.confirm_download_button.setEnabled(bool(self.selected_images))

        if self.in_reid_mode:
            self.confirm_reid_button.setEnabled(bool(self.selected_images))

        self.update_image_grid()

    def confirm_delete_selected(self):
        """
        Confirms the deletion of selected images and performs the deletion action.
        It provides feedback to the user about the success of the operation.
        """
        if self.selected_images:
            confirmation = QMessageBox.question(self, "Confirm Delete",
                                                f"Are you sure you want to delete {len(self.selected_images)} images? You will not be able to get these back! Please ensure you have these photos saved locally somewhere.",
                                                QMessageBox.Yes | QMessageBox.No)
            if confirmation == QMessageBox.Yes:
                deleted_images = []
                session = Session()
                try:
                    for link in self.selected_images:
                        photo = session.query(Photo).filter(Photo.thumbnail == link).first()

                        if photo:
                            self.delete_image_from_s3(photo.bbox)
                            if photo.cropped:
                                self.delete_image_from_s3(photo.cropped)
                            if photo.thumbnail:
                                self.delete_image_from_s3(photo.thumbnail)

                            session.delete(photo)
                            deleted_images.append(link)

                    session.commit()
                    QMessageBox.information(self, "Deletion Complete",
                                            f"{len(deleted_images)} images have been deleted.")

                except Exception as e:
                    session.rollback()
                    QMessageBox.critical(self, "Delete Error", f"An error occurred while deleting images: {str(e)}")
                finally:
                    session.close()

                self.selected_images.clear()
                self.in_delete_mode = False
                self.delete_button.setText("Delete Images")
                self.remove_controls("delete")
                self.delete_button.setEnabled(True)
                self.delete_button.setVisible(True)
                self.download_button.setEnabled(True)
                self.download_button.setVisible(True)
                self.reid_button.setEnabled(True)
                self.reid_button.setVisible(True)
                self.images = [img for img in self.images if img[0] not in deleted_images]
                self.original_images = []
                self.update_image_grid()
                self.filter_by_animal()

    def confirm_reid_selected(self):
        """
        Confirms the re-identification of selected images and performs the re-identification action.
        It provides feedback to the user about the success of the operation.
        """
        random_number = random.randint(1, 9999999)
        new_name = f"online-{random_number}"
        if not self.selected_images:
            QMessageBox.warning(self, "No Images Found", "No images were found in the online database.")
            return

        bbox_directory = "app/detection_model/temporary_detected_images/bbox_images"
        crop_directory = "app/detection_model/temporary_detected_images/crop_images"
        thumbnail_directory = "app/detection_model/temporary_detected_images/thumbnails"

        try:
            for link in self.selected_images:
                photo = self.fetch_full_image_data(link)
                user_id = photo[0]
                description = photo[1]
                date = photo[2]
                confidence = photo[3]
                location = photo[4]
                bbox = photo[5]
                bbox = bbox.replace("bbox_images", "bbox")
                cropped = photo[6]
                cropped = cropped.replace("crop_images", "cropped")
                group_name = photo[-3]
                thumbnail = photo[-4]
                name = photo[-2]
                animal = photo[10]

                bbox_photo = self.fetch_image_from_s3((bbox,))
                thumbnail_photo = self.fetch_image_from_s3((thumbnail,))
                cropped_photo = self.fetch_image_from_s3((cropped,))

                if bbox_photo:
                    bbox_image_path = os.path.join(bbox_directory, os.path.basename(bbox))
                    with open(bbox_image_path, 'wb') as f:
                        f.write(bbox_photo)

                if cropped_photo:
                    cropped_image_path = os.path.join(crop_directory, os.path.basename(cropped))
                    with open(cropped_image_path, 'wb') as f:
                        f.write(cropped_photo)

                if thumbnail_photo:
                    thumbnail_path = os.path.join(thumbnail_directory, os.path.basename(thumbnail))
                    with open(thumbnail_path, 'wb') as f:
                        f.write(thumbnail_photo)

                run_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                self.local_db.insert_image(
                    self.current_user, bbox_image_path, cropped_image_path, thumbnail_path, location,
                    run_datetime, confidence, new_name, animal
                )

            QMessageBox.information(self, "Download Complete",
                                    f"{len(self.selected_images)} image/s have been downloaded and saved to the local database successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"An error occurred while downloading images: {str(e)}")

        self.selected_images.clear()
        self.in_reid_mode = False
        self.reid_button.setText("Save Images to Local Database")
        self.remove_controls("reid")
        self.delete_button.setEnabled(True)
        self.delete_button.setVisible(True)
        self.download_button.setEnabled(True)
        self.download_button.setVisible(True)
        self.reid_button.setEnabled(True)
        self.reid_button.setVisible(True)
        self.update_image_grid()
        self.database_page.populate_tree()

    def confirm_download_selected(self):
        """
        Confirms the download of selected images and performs the download action.
        It provides feedback to the user about the success of the operation.
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
                for link in self.selected_images:
                    full_image_url = self.fetch_full_image_from_db(link)
                    full_image_url = full_image_url.replace("bbox_images", "bbox")
                    if full_image_url:
                        full_image_data = self.fetch_image_from_s3((full_image_url,))
                        if full_image_data:
                            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                                tmp_file.write(full_image_data)
                                tmp_file.close()

                                zipf.write(tmp_file.name, os.path.basename(full_image_url))
                                os.unlink(tmp_file.name)

            QMessageBox.information(self, "Download Complete",
                                    f"{len(self.selected_images)} images have been zipped and saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"An error occurred while creating the ZIP file: {str(e)}")

        self.selected_images.clear()
        self.in_download_mode = False
        self.download_button.setText("Download Images")
        self.remove_controls("download")
        self.delete_button.setEnabled(True)
        self.delete_button.setVisible(True)
        self.download_button.setEnabled(True)
        self.download_button.setVisible(True)
        self.reid_button.setEnabled(True)
        self.reid_button.setVisible(True)
        self.update_image_grid()

    def open_image_popup(self, image_data):
        """Open a popup dialog to display a full image along with its details.

        Args:
            image_data (tuple): A tuple containing the thumbnail URL.

        Returns:
            None
        """
        thumbnail_url = image_data[0]

        full_image_url = self.fetch_full_image_from_db(thumbnail_url)
        full_image_url = full_image_url.replace("bbox_images", "bbox")

        if not full_image_url:
            print(f"No full image found for the thumbnail: {thumbnail_url}")
            return

        popup = QDialog(self, Qt.Window)
        popup.setWindowTitle("Full Image")
        popup.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout(popup)
        full = (full_image_url,)
        full_image_data = self.fetch_image_from_s3(full, )
        session = Session()
        photo = session.query(Photo).filter(Photo.thumbnail == thumbnail_url).first()
        session.close()

        if full_image_data:
            image_label = QLabel(popup)
            pixmap = QPixmap()
            pixmap.loadFromData(full_image_data)
            image_label.setPixmap(
                pixmap.scaled(popup.width(), popup.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

            group_label = QLabel(f'Group: {photo.group_name}')
            group_label.setObjectName("groupLabel")
            confidence_label = QLabel(f'Confidence: {photo.confidence}')
            confidence_label.setObjectName("confidenceLabel")
            uploaded_by = connection.get_user_by_id(photo.user_id)
            uploaded_label = QLabel(f'Uploaded by: {uploaded_by.username}')
            uploaded_label.setObjectName("userLabel")
            animal_label = QLabel(f'Animal: {photo.animal}')
            animal_label.setObjectName("animalLabel")

            group_confidence_layout = QHBoxLayout()
            group_confidence_layout.addWidget(group_label)
            group_confidence_layout.addWidget(confidence_label)
            animal_user_layout = QHBoxLayout()
            animal_user_layout.addWidget(animal_label)
            animal_user_layout.addWidget(uploaded_label)

            layout.addWidget(image_label)
            layout.addLayout(group_confidence_layout)
            layout.addLayout(animal_user_layout)

            popup.setLayout(layout)
            popup.show()
        else:
            print(f"Failed to fetch full image from S3 for URL: {full_image_url}")

    def update_pagination(self):
        """Update the pagination controls based on the current image page.

        Returns:
            None
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

    def go_to_last_page(self):
        """Navigate to the last page of images.

        Returns:
            None
        """
        total_pages = max(1, (len(self.images) + self.images_per_page - 1) // self.images_per_page)
        self.go_to_page(total_pages - 1)

    def go_to_first_page(self):
        """Navigate to the first page of images.

        Returns:
            None
        """
        self.current_page = 0
        self.update_image_grid()

    def go_to_page(self, page_num):
        """Navigate to a specific page of images.

        Args:
            page_num (int): The page number to navigate to.

        Returns:
            None
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
        """Navigate to the previous page of images.

        Returns:
            None
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.update_image_grid()

    def next_page(self):
        """Navigate to the next page of images.

        Returns:
            None
        """
        if (self.current_page + 1) * self.images_per_page < len(self.images):
            self.current_page += 1
            self.update_image_grid()

    def folders(self):
        """Print the names of the folders from the database.

        Returns:
            None
        """
        print(connection.get_folder_names())

    def populate_tree_with_dates_and_folder(self):
        """Populate the tree widget with dates and corresponding folders containing images.

        Returns:
            None
        """
        for date, folders in sorted(connection.get_folder_names().items()):
            folder_count = len(folders)
            date_str = date.strftime("%Y-%m-%d")
            date_item = QTreeWidgetItem(self.tw)
            # date_item.setText(0, date_str)
            date_item.setText(0, f"{date_str} ({folder_count} folder/s)")
            for folder in folders:
                images_in_folder = connection.get_image_by_folder(folder)
                image_count = len(images_in_folder)
                folder_item = QTreeWidgetItem(date_item)
                folder_item.setText(0, f"{folder} ({image_count} images)")

    def tree_click(self, item, column):
        """Handle clicks on the tree widget to update images based on the selected folder or date.

        Args:
            item (QTreeWidgetItem): The clicked tree item.
            column (int): The column index of the clicked item.

        Returns:
            None
        """
        if item.parent() is not None:
            folder_name_with_images = item.text(column)
            folder_name = folder_name_with_images.split(" (")[0]
            self.images = connection.get_image_by_folder(folder_name)
        else:
            date_with_folder_count = item.text(column)
            date_str = date_with_folder_count.split(" (")[0]
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return
            all_images_for_date = []
            folders = connection.get_folder_names().get(date_obj)
            if folders:
                for folder in folders:
                    images_in_folder = connection.get_image_by_folder(folder)
                    all_images_for_date.extend(images_in_folder)
            self.images = all_images_for_date
        self.original_images = self.images
        self.current_page = 0
        self.filter_by_animal()
        self.update_image_grid()
        self.total_pages = max(1, (len(self.images) + self.images_per_page - 1) // self.images_per_page)
        self.update_pagination()
        self.download_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.reid_button.setEnabled(True)

    def update_grid_by_animal(self):
        """Update the image grid based on the selected animal filter.

        Returns:
            None
        """
        # self.images = self.original_images
        self.filter_by_animal()
        self.update_image_grid()

    def update_sync_status(self):
        """Update the user's sync status in the database.

        Returns:
            None
        """
        user = connection.get_user_id(self.current_user)
        connection.update_status(user)

    def fetch_image_from_s3(self, url):
        """Fetch an image from Amazon S3.

        Args:
            url (tuple): A tuple containing the URL of the image.

        Returns:
            bytes or None: The image data if successful, otherwise None.
        """
        url = url[0]
        split_keyword = "temporary_detected_images"
        split_part = url.split(split_keyword, 1)[1]
        split_key = f"images{split_part}"
        key = split_key
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except Exception as e:
            print(f"Error fetching image from S3: {e}")
            return None

    def delete_image_from_s3(self, image_url):
        """Delete an image from Amazon S3.

        Args:
            image_url (str): The URL of the image to be deleted.

        Returns:
            None
        """
        try:
            split_key = image_url.split(f'https://{self.bucket_name}.s3.amazonaws.com/')
            key = split_key[1]
            key_list = key.split('app/detection_model/temporary_detected_')
            s3_key = key_list[1]
            s3_key = s3_key.replace("bbox_images", "bbox")
            s3_key = s3_key.replace("crop_images", "cropped")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            print(f"Deleted {s3_key} from S3.")

        except Exception as e:
            print(f"Error deleting image from S3: {str(e)}")

    def fetch_full_image_from_db(self, thumbnail_url):
        """
        Fetch the bounding box of a full image from the database using the thumbnail URL.

        Args:
            thumbnail_url (str): The URL of the thumbnail image.

        Returns:
            bbox (str or None): The bounding box of the full image if found, otherwise None.
        """

        session = Session()
        photo = session.query(Photo).filter(Photo.thumbnail == thumbnail_url).first()

        if photo:
            return photo.bbox
        else:
            print(f"No image found for thumbnail: {thumbnail_url}")
            return None

    def fetch_full_image_data(self, thumbnail_url):
        """Fetch detailed information about a full image from the database using the thumbnail URL.

        Args:
            thumbnail_url (str): The URL of the thumbnail image.

        Returns:
            tuple or None: A tuple containing user ID, description, date, confidence,
                           location, bounding box, cropped status, thumbnail URL,
                           group name, and image name if found; otherwise, None.
        """
        session = Session()
        photo = session.query(Photo).filter(Photo.thumbnail == thumbnail_url).first()

        if photo:
            user_id = photo.user_id
            description = photo.description
            date = photo.created_at
            confidence = photo.confidence
            location = photo.location
            bbox = photo.bbox
            cropped = photo.cropped
            group_name = photo.group_name
            thumbnail = photo.thumbnail
            name = photo.name
            animal = photo.animal
            return (user_id, description, date, confidence, location, bbox, cropped, thumbnail, group_name, name, animal)

        else:
            print(f"No image found for thumbnail: {thumbnail_url}")
            return None

    def populate_animal_combobox(self):
        """Populate the animal combo box with distinct animal names from the database.

        Returns:
            None
        """
        get_animals = connection.get_distinct_animals()
        self.animal_combobox.clear()
        self.animal_combobox.addItem("▼ All")
        for animal in get_animals:
            self.animal_combobox.addItem(animal)

    def filter_by_animal(self):
        """Filter the images based on the currently selected animal in the combo box.

        Returns:
            None
        """
        selected_animal = self.animal_combobox.currentText()

        if selected_animal == "▼ All":
            filtered_images = self.original_images
        else:
            filtered_images = connection.get_animals_by_filter(self.original_images, selected_animal)

        self.images = filtered_images

    def refresh_database(self):
        """Refresh the database view by clearing the tree widget and reloading data.

        Returns:
            None
        """
        self.tw.clear()
        self.populate_tree_with_dates_and_folder()
        self.animal_combobox.clear()
        self.populate_animal_combobox()

    def load_stylesheet(self):
        """Load the stylesheet for the online database page from a CSS file.

        Returns:
            None
        """
        css_file = os.path.join(os.path.dirname(__file__), 'css', 'online_database_page.css')
        with open(css_file, 'r') as f:
            self.setStyleSheet(f.read())
