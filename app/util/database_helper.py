import sqlite3
import os
from datetime import datetime
from app.databases.model import User

class DatabaseHelper:
    def __init__(self):
        """Initializes the DatabaseHelper and creates necessary tables."""
        base_path = os.path.dirname(os.path.dirname(__file__))
        self.db_path = os.path.join(base_path, 'databases', 'image_database.db')  # Correctly point to the database
        self.connection = sqlite3.connect(self.db_path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.create_user_table()
        self.create_table()
        self.create_reid_table()


    def create_table(self):
        """Creates the images table if it doesn't already exist."""
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY,
                    user TEXT,
                    bbox_image_path TEXT,
                    cropped_image_path TEXT,
                    thumbnail_path TEXT,
                    location TEXT,  -- Stored as "(x, y)"
                    upload_date TEXT,
                    confidence FLOAT,
                    group_name TEXT,
                    is_synced BOOLEAN DEFAULT 0,  -- 0 = False, 1 = True
                    animal TEXT
                )
            """)

    def create_reid_table(self):
        """Creates the reid table if it doesn't already exist."""
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS reid (
                    id INTEGER PRIMARY KEY ,
                    run_id TEXT,  -- Unique identifier for each re-identification run
                    image_id INTEGER,  -- Foreign key to images table
                    reid_id TEXT,  -- Stores 'ID-0', 'ID-1', etc.
                    run_datetime TEXT,  -- Date and time of the re-identification run
                    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
                )
            """)

    def create_user_table(self):
        """Creates the users table if it doesn't already exist."""
        with self.connection:
            self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                password TEXT NOT NULL,
                username TEXT NOT NULL,
                is_synced BOOLEAN DEFAULT False,
                is_authorised BOOLEAN DEFAULT True,
                is_admin BOOLEAN DEFAULT False
            )
        """)

    def insert_user(self, user):
        """Inserts a new user into the users table if the user does not already exist.

        Args:
            user: An instance of User containing user information.
        """
        with self.connection:
            check_user = self.connection.execute("""
            SELECT * FROM user WHERE email = ?""", user.email).fetchone()

            if check_user is None:
                # Insert the new user into the local database
                self.connection.execute("""
                            INSERT INTO user (id, password, username, is_synced, is_authorised, is_admin)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                user.id, user.password, user.username, False, True, False))

                print("User added successfully.")
            else:
                print("User already exists.")

    def insert_reid_result(self, run_id, image_id, reid_id, run_datetime):
        """Inserts a re-identification result into the reid table.

        Args:
            run_id (str): The unique identifier for the re-identification run.
            image_id (int): The foreign key referencing the image in the images table.
            reid_id (str): The re-identification ID.
            run_datetime (str): The date and time of the re-identification run.
        """
        query = """
            INSERT INTO reid (run_id, image_id, reid_id, run_datetime)
            VALUES (?, ?, ?, ?)
        """
        self.connection.execute(query, (run_id, image_id, reid_id, run_datetime))
        self.connection.commit()

    def insert_image(self, user, bbox_image_path, cropped_image_path, thumbnail_path, location, upload_date, confidence,
                     group_name, animal):
        """Inserts a new image record into the images table.

        Args:
            user (str): The username of the user uploading the image.
            bbox_image_path (str): The file path to the bounding box image.
            cropped_image_path (str): The file path to the cropped image.
            thumbnail_path (str): The file path to the thumbnail image.
            location (str): The location stored as "(x, y)".
            upload_date (str): The date of image upload.
            confidence (float): The confidence score associated with the image.
            group_name (str): The group name associated with the image.
            animal (str): The type of animal represented in the image.
        """
        confidence = float(confidence)

        with self.connection:
            self.connection.execute("""
                INSERT INTO images (user, bbox_image_path, cropped_image_path, thumbnail_path, location, upload_date, confidence, group_name, animal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
            user, bbox_image_path, cropped_image_path, thumbnail_path, location, upload_date, confidence, group_name, animal))

    def fetch_unsynced_images(self):
        """Fetches all unsynced images from the images table.

        Returns:
            list: A list of unsynced images.
        """
        with self.connection:
            return self.connection.execute("""
                SELECT * FROM images
            """).fetchall()
        
    def fetch_image_path_by_id(self, image_id):
        """Fetches the file paths of images by their ID.

        Args:
            image_id (int): The ID of the image.

        Returns:
            tuple: A tuple containing the bounding box, cropped, and thumbnail image paths.
        """
        with self.connection:
            result = self.connection.execute("""
                SELECT bbox_image_path, cropped_image_path, thumbnail_path FROM images WHERE id = ?
            """, (image_id,)).fetchone()
            return result

    def fetch_image_path_by_reid(self, image_id):
        """Fetches the image paths associated with a re-identification ID.

        Args:
            image_id (int): The ID of the image.

        Returns:
            tuple: A tuple containing the bounding box, cropped, and thumbnail image paths.
        """
        connection = self.get_connection()
        with connection:
            result = connection.execute("""
                SELECT bbox_image_path, cropped_image_path, thumbnail_path 
                FROM images 
                WHERE id = ?""", (image_id,))
            return result.fetchone()

    def get_connection(self):
        """Gets a new database connection.

        Returns:
            sqlite3.Connection: A new database connection object.
        """
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def fetch_id_by_path(self, path):
        """Fetches the ID of an image based on the cropped image path.

        Args:
            path (str): The file path of the cropped image.

        Returns:
            int: The ID of the image, or None if not found.
        """
        with self.connection:
            result = self.connection.execute("""
                SELECT id FROM images WHERE cropped_image_path = ?
            """, (path,)).fetchone()

            if result is not None:
                return result[0]
            return None

    def fetch_images_in_group(self, pin_group):
        """Fetches images belonging to a specific group.

        Args:
            pin_group (list): A list of image IDs.

        Returns:
            list: A list of images belonging to the specified group.
        """
        with self.connection:
            return self.connection.execute(f"""
                SELECT id, user, bbox_image_path, cropped_image_path, thumbnail_path, location, upload_date, confidence
                FROM images
                WHERE id IN ({','.join('?' for _ in pin_group)})
            """, pin_group).fetchall()

    def delete_image(self, image_id):
        """Deletes an image from the images table based on its ID.

        Args:
            image_id (int): The ID of the image to be deleted.
        """
        with self.connection:
            self.connection.execute("""
                DELETE FROM images WHERE id = ?
            """, (image_id,))

    def delete_reid(self, image_id):
        """Deletes a re-identification result from the reid table based on the image ID.

        Args:
            image_id (int): The ID of the image associated with the re-identification result.
        """
        with self.connection:
            self.connection.execute("""
                DELETE FROM reid WHERE id = ?
            """, (image_id,))


    def close(self):
        """Closes the database connection."""
        self.connection.close()
    
    @staticmethod
    def _convert_location_to_tuple(location_str):
        """Converts a string representation of a location to a tuple.

        Args:
            location_str (str): The location string in the format "(x, y)".

        Returns:
            tuple: A tuple containing the coordinates (x, y), or None if conversion fails.
        """
        try:
            x, y = map(int, location_str.strip('()').split(','))
            return (x, y)
        except ValueError:
            return None

    def mark_image_as_synced(self, image_id):
        """Marks an image as synced in the images table.

        Args:
            image_id (int): The ID of the image to be marked as synced.
        """
        with self.connection:
            self.connection.execute("""
                UPDATE images
                SET is_synced = 1
                WHERE id = ?
            """, (image_id,))

    def fetch_unsynced_image_count(self):
        """Fetches the count of unsynced images.

        Returns:
            int: The count of unsynced images.
        """
        with self.connection:
            result = self.connection.execute("""
                SELECT COUNT(*) FROM images WHERE is_synced = 0
            """).fetchone()
            return result[0] if result else 0

    def images_tosync(self):
        """Fetches the unsynced images. """
        with self.connection:
            result = self.connection.execute("""
                SELECT * FROM images WHERE is_synced = 0
            """).fetchall()
            return result

    def get_images_by_date(self):
        """Gets images by upload date and returns a dict of image records."""
        with self.connection:
            images_dict = {}
            result = self.connection.execute("""
            SELECT * FROM images
            """).fetchall()

            for image in result:
                upload_date = image[6]  # Assuming upload_date is at index 6
                if upload_date not in images_dict:
                    images_dict[upload_date] = []
                images_dict[upload_date].append(image)

        return images_dict

    def get_reid_id_by_date(self):
        """Gets reid run by date and returns a dict of reid id"""
        with self.connection:
            reid_dict = {}
            result = self.connection.execute("""
            SELECT run_datetime, reid_id FROM reid""").fetchall()
            for x in result:
                if x[0] not in reid_dict:
                    reid_dict[x[0]] = []
                if x[1] not in reid_dict[x[0]]:
                    reid_dict[x[0]].append(x[1])
            return reid_dict

    def get_image_by_date_and_id(self, date, id):
        """Fetches images based on the specified date and re-identification ID.

        Args:
            date (str): The date of the re-identification run.
            id (str): The re-identification ID.

        Returns:
            list: A list of images that match the specified date and ID.
        """
        with self.connection:
            result = self.connection.execute("""
            SELECT images.*, reid.id FROM images 
            JOIN reid ON images.id = reid.image_id
            WHERE reid.reid_id = ? AND reid.run_datetime = ?""", (id, date)).fetchall()
        return result

    def get_reid_image_by_date(self, date):
        """Fetches images associated with a specific re-identification run date.

        Args:
            date (str): The date of the re-identification run.

        Returns:
            list: A list of images associated with the specified date.
        """
        with self.connection:
            result = self.connection.execute("""
            SELECT images.*, reid.id FROM images 
            JOIN reid ON images.id = reid.image_id
            WHERE reid.run_datetime = ?""", (date,)).fetchall()
        return result

    def get_images_by_date(self):
        """Fetches images grouped by upload date and group name.

        Returns:
            dict: A dictionary where each key is a date, and the value is another
                  dictionary with group names as keys and lists of images as values.
        """
        with self.connection:
            # Modify the SQL query to select images and group by date and group_name
            result = self.connection.execute("""
            SELECT DATE(upload_date) AS upload_date, group_name, * FROM images 
            ORDER BY upload_date, group_name
            """).fetchall()

        images_by_date = {}
        for row in result:
            date = row[0]  # The date part
            group_name = row[1]  # The group name
            if date not in images_by_date:
                images_by_date[date] = {}
            if group_name not in images_by_date[date]:
                images_by_date[date][group_name] = []
            images_by_date[date][group_name].append(row)

        return images_by_date

    def get_image_by_date(self, date, group_name, min_confidence, max_confidence):
        """Fetches images based on date, group name, and confidence range.

        Args:
            date (str): The date of the images to fetch.
            group_name (str): The group name associated with the images.
            min_confidence (float): The minimum confidence threshold.
            max_confidence (float): The maximum confidence threshold.

        Returns:
            list: A list of images that match the specified criteria.
        """
        with self.connection:
            result = self.connection.execute("""
                SELECT * FROM images
                WHERE DATE(upload_date) = ? 
                AND group_name = ?
                AND confidence BETWEEN ? AND ?
            """, (date, group_name, min_confidence, max_confidence)).fetchall()
        return result

    def parent_date_click(self, date, min_confidence, max_confidence):
        """Fetches images based on date and confidence range without filtering by group.

        Args:
            date (str): The date of the images to fetch.
            min_confidence (float): The minimum confidence threshold.
            max_confidence (float): The maximum confidence threshold.

        Returns:
            list: A list of images that match the specified date and confidence range.
        """
        with self.connection:
            result = self.connection.execute("""
                SELECT * FROM images
                WHERE DATE(upload_date) = ?
                AND confidence BETWEEN ? AND ?
            """, (date, min_confidence, max_confidence)).fetchall()
        return result

    def get_distinct_animals(self):
        """Fetches a list of distinct animal types from the images table.

        Returns:
            list: A list of distinct animal types.
        """
        query = "SELECT DISTINCT animal FROM images"
        result = self.connection.execute(query).fetchall()
        return [row[0] for row in result]

    def get_images_by_animal(self, animal):
        """Fetches images associated with a specific animal type.

        Args:
            animal (str): The type of animal to filter images by.

        Returns:
            list: A list of images associated with the specified animal type.
        """
        query = "SELECT * FROM images WHERE animal = ?"
        result = self.connection.execute(query, (animal,)).fetchall()
        return result




