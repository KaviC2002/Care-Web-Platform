import multiprocessing
import os

import pytz
from PyQt5.QtGui import QPixmap, QImage
from sqlalchemy import create_engine, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from app.databases import model
from datetime import datetime
import re
from PIL import Image
import io
from app.util.network_manager import NetworkManager
from app.util.database_helper import DatabaseHelper
from app.util.user_database_helper import UserDatabaseHelper

connectivity = NetworkManager()
local_db = DatabaseHelper()
num_cores = multiprocessing.cpu_count()

if num_cores > 1:
    max_workers = num_cores // 2
else:
    max_workers = 1

# Add the username and password
user = 'postgres'
password = 'sagar1234'
host = 'database-3.cbyvolvk60lh.ap-southeast-2.rds.amazonaws.com'
port = '5432'
database = 'postgres'
# for creating connection string
connection_str = f'postgresql://{user}:{password}@{host}:{port}/{database}'
# SQLAlchemy engine
engine = create_engine(connection_str)

import pytz
from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.databases import model
from app.util.network_manager import NetworkManager


class OnlineDatabase:
    """A class to handle operations related to an online PostgreSQL database."""
    def __init__(self):
        """Initialise the OnlineDatabase with connection parameters and network manager."""
        user = 'postgres'
        password = 'sagar1234'
        host = 'database-3.cbyvolvk60lh.ap-southeast-2.rds.amazonaws.com'
        port = '5432'
        database = 'postgres'
        # for creating connection string
        self.connection_str = f'postgresql://{user}:{password}@{host}:{port}/{database}'
        self.engine = create_engine(self.connection_str)
        self.Session = sessionmaker(bind=self.engine)
        self.connectivity = NetworkManager()
        self.local_user_db = UserDatabaseHelper()

    def connect(self):
        """Establish a connection to the online database.

        Returns:
            Connection object or None if unable to connect.
        """
        if not self.connectivity.is_online():
            print("No internet connection. Cannot connect to the online database.")
            return None
        try:
            connection = self.engine.connect()
            print('Successfully connected to the PostgreSQL database.')
            return connection
        except Exception as ex:
            print(f'Failed to connect: {ex}')
            return None

    def add_user(self, user):
        """Add a new user to the database if they do not already exist.

        Args:
            user (model.User): The user object to add to the database.
        """
        session = self.Session()
        try:
            check_user = session.query(model.User).filter_by(email=user.email).first()
            if check_user is None:
                session.add(user)
                session.commit()  # Commit the transaction here
                print("User added successfully.")
                users = session.query(model.User).all()
                for user in users:
                    print(f'{type(user)} - {user.email}')
            else:
                print("User already exists.")
        except Exception as ex:
            session.rollback()  # Rollback the session in case of an error
            print(f"Error adding user: {ex}")
        finally:
            session.close()  # Ensure session is closed

    def get_user(self, username):
        """Retrieve a user by their username (email).

        Args:
            username (str): The email of the user to retrieve.

        Returns:
            model.User or None: The user object if found, else None.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(email=username).first()
            if user:
                session.close()
                return user
            else:
                session.close()
                return None

    def login(self, username, user_password):
        """Log in a user by checking their credentials.

        Args:
            username (str): The email of the user.
            user_password (str): The user's password.

        Returns:
            bool: True if logged in successfully, False otherwise.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(email=username.lower()).first()
            session.close()
            if user:
                print("User found.")
                if user.check_password(user_password):
                    print("Logged in successfully.")
                    return True
                else:
                    print("Incorrect credentials. Please try again.")
                    return False
            else:
                print("User not found.")
                return False

    def check_username(self, username):
        """Check if a username (email) is already taken.

        Args:
            username (str): The email to check.

        Returns:
            bool: True if the username is taken, False otherwise.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(email=username).first()
            session.close()
            if user:
                print("Username is taken.")
                return True
            else:
                print("Username available.")
                return False

    def get_user_id(self, user):
        """Get the user ID based on the user's email.

        Args:
            user (str): The email of the user.

        Returns:
            int: The ID of the user.
        """
        with self.Session() as session:
            user_id = session.query(model.User).filter_by(email=user).first()
            return user_id.id

    def get_user_by_id(self, user_id):
        """Retrieve a user by their ID.

        Args:
            user_id (int): The ID of the user.

        Returns:
            model.User or None: The user object if found, else None.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(id=user_id).first()
            session.close()
            return user

    def get_folder_names(self):
        """Retrieve distinct folder names from photos based on their creation date.

        Returns:
            dict: A dictionary where keys are dates and values are lists of folder names.
        """
        with self.Session() as session:
            date_dict = {}
            photos = session.query(model.Photo).all()
            for photo in photos:
                date = photo.created_at.date()
                folder_name = photo.group_name[:-16]
                if date not in date_dict:
                    date_dict[date] = [folder_name]
                else:
                    if folder_name not in date_dict[date]:
                        date_dict[date].append(folder_name)
            session.close()
            return date_dict

    def get_image_by_folder(self, folder_name):
        """Retrieve images by folder name.

        Args:
            folder_name (str): The folder name to filter images.

        Returns:
            list: A list of image thumbnails belonging to the specified folder.
        """
        with self.Session() as session:
            # Truncate the last 16 characters from group_name and compare with folder_name
            truncated_group_name = func.substr(model.Photo.group_name, 1, func.length(model.Photo.group_name) - 16)

            images = session.query(model.Photo.thumbnail).filter(
                truncated_group_name == folder_name
            ).all()

            session.close()
            return images

    def update_status(self, user_id):
        """Update the last synced time for a user.

        Args:
            user_id (int): The ID of the user.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(id=user_id).first()
            if user:
                user.last_synced = datetime.now(pytz.timezone("Pacific/Auckland"))
                session.commit()
                print("User status updated successfully.")
            session.close()

    def get_status(self, email):
        """Get the last synced status of a user by their email.

        Args:
            email (str): The email of the user.

        Returns:
            str or None: Formatted last synced date if available, else None.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(email=email).first()
            if user:
                last_synced = user.last_synced
                if last_synced:
                    formatted_date = last_synced.strftime("%d/%m/%y %H:%M")
                    return formatted_date
            session.close()
            return None

    def drop_all_tables(self):
        """Drop all tables in the database.

        **Warning**: Use this method with caution, as it will delete all data."""
        try:
            model.Base.metadata.drop_all(self.engine)  # Drop all tables associated with the Base
            print("All tables dropped successfully.")
        except Exception as ex:
            print(f"Failed to drop all tables: {ex}")

    def create_tables(self):
        """Create all tables defined in the models."""
        model.Base.metadata.create_all(self.engine)
        print("Tables created successfully.")

    def check_admin_status(self, username):
        """Check if a user is an admin.

        Args:
            username (str): The email of the user.

        Returns:
            bool: True if the user is an admin, False otherwise.
        """
        user = self.get_user(username)
        if user:
            if user.is_admin:
                return True
            else:
                return False

    def load_all_users(self):
        """Load all users from the database.

        Returns:
            list: A list of all user objects.
        """
        with self.Session() as session:
            all_users = session.query(model.User).all()
            session.close()
            return all_users

    def approve_user(self, username):
        """Approve a user by setting their authorized status to True.

        Args:
            username (str): The email of the user to approve.
        """

        with self.Session() as session:
            user = session.query(model.User).filter_by(email=username).first()
            if user:
                user.is_authorised = True
            print(user)
            print(user.is_authorised)
            session.commit()
            session.close()

    def reject_user(self, username):
        """Reject a user by setting their authorized status to False.

        Args:
            username (str): The email of the user to reject.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(email=username).first()
            user.is_authorised = False
            session.commit()
            session.close()

    def sync_all_user_accounts(self):
        """Synchronise all user accounts between local and online databases."""
        users = self.local_user_db.get_all_users()
        session = self.Session()  # Create a session for all user syncing
        try:
            for local_user in users:
                check_user = session.query(model.User).filter_by(email=local_user.email).first()
                new_user = model.User(email=local_user.email, username=local_user.username, password=local_user.password, last_synced=local_user.last_synced, is_authorised=local_user.is_authorised, is_admin=local_user.is_admin, is_synced=local_user.is_synced)
                new_user.password = local_user.password

                if not check_user:
                    session.add(new_user)
                else:
                    print("User already exists")
                    if check_user.is_authorised != new_user.is_authorised:
                        check_user.is_authorised = new_user.is_authorised

                    if check_user.is_admin != new_user.is_admin:
                        check_user.is_admin = new_user.is_admin

            session.commit()  # Commit after syncing all users
            print("All users synced successfully.")
        except Exception as ex:
            session.rollback()  # Rollback the transaction in case of error
            print(f"Error syncing users: {ex}")
        finally:
            session.close()  # Ensure session is closed after all operations

    def get_all_users(self):
        """Retrieve all users from the database.

        This method creates a new session to query the User model,
        fetching all user records stored in the database. It then
        closes the session to free resources.

        Returns:
            list: A list of User objects representing all users in the database.
        """
        session = self.Session()
        users = session.query(model.User).all()
        session.close()
        return users

    def get_distinct_animals(self):
        """Retrieve distinct animal types from the database.

        This method creates a new session to query the Photo model,
        fetching all distinct animal entries. It ensures that only unique
        animal types are returned. The session is closed afterward.

        Returns:
            list: A list of unique animal types as strings.
        """
        session = self.Session()
        animals = session.query(model.Photo.animal).distinct().all()
        session.close()
        return [animal[0] for animal in animals]

    def get_animals_by_filter(self, images, selected_animal):
        """Filter images by the selected animal type.

        This method filters the provided images based on the specified
        animal type. For each image, it queries the Photo model to
        check if the animal associated with the thumbnail matches the
        selected animal. If there’s a match, the image is added to the
        filtered list.

        Args:
            images (list): A list of tuples containing image thumbnails to filter.
            selected_animal (str): The animal type to filter images by.

        Returns:
            list: A list of tuples containing filtered image thumbnails
            that match the selected animal type.
        """
        session = self.Session()
        filtered_animals = []
        for image in images:
            get_animal = session.query(model.Photo).filter_by(thumbnail = image[0]).first()
            if get_animal.animal == selected_animal:
                filtered_animals.append((get_animal.thumbnail,))
        session.close()
        return filtered_animals

