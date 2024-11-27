import os

from app.databases import model
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

class UserDatabaseHelper:
    """A helper class for managing user database operations.

    This class handles user-related database functionalities such as
    adding users, retrieving user information, and managing user
    authentication using SQLite and SQLAlchemy.
    """
    def __init__(self):
        """Initializes the UserDatabaseHelperSQLAlchemy and sets up the database engine."""
        base_path = os.path.dirname(__file__)
        self.db_path = os.path.join(base_path, '..', 'databases', 'user_data.db')
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.create_user_table()
        self.Session = sessionmaker(bind=self.engine)

    def login(self, username, user_password):
        """Authenticates a user by checking their credentials.

                Args:
                    username (str): The email of the user attempting to log in.
                    user_password (str): The password provided by the user.

                Returns:
                    bool: True if login is successful, False otherwise.
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

    def get_user(self, username):
        """Retrieves a user from the database by username.

        Args:
            username (str): The email of the user to retrieve.

        Returns:
            model.User: The user object if found, None otherwise.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(email=username).first()
            if user:
                session.close()
                return user
            else:
                session.close()
                return None

    def create_user_table(self):
        """Creates the users table in the database using SQLAlchemy."""
        model.User.metadata.create_all(self.engine)

    def get_all_users(self):
        """Retrieves all users from the database.

        Returns:
            list: A list of all user objects in the database.
        """
        with self.Session() as session:
            users = session.query(model.User).all()
            session.close()
            return users

    def add_user(self, user):
        """Adds a new user to the database.

        Args:
            user (model.User): The user object to be added.
        """
        session = self.Session()
        try:
            check_user = session.query(model.User).filter_by(email=user.email).first()
            if check_user is None:
                session.add(user)
                session.commit()  # Commit the transaction here
                print("User added successfully.")
            else:
                print("User already exists.")
        except Exception as ex:
            session.rollback()  # Rollback the session in case of an error
            print(f"Error adding user: {ex}")
        finally:
            session.close()  # Ensure session is closed

    def check_username(self, username):
        """Checks if a username is already taken.

        Args:
            username (str): The username to check.

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

    def sync_user(self, users):
        """Synchronizes user data from a list of user objects.

        Args:
            users (list): A list of user objects to synchronize.
        """
        with self.Session() as session:
            for user in users:
                new_user = model.User(email=user.email, username=user.username, password=user.password, last_synced=user.last_synced, is_authorised=user.is_authorised, is_admin=user.is_admin, is_synced=user.is_synced)
                check_user = session.query(model.User).filter_by(email=user.email).first()
                if not check_user:
                    session.add(new_user)
                else:
                    print("User already exists")
                    if check_user.is_authorised != new_user.is_authorised:
                        check_user.is_authorised = new_user.is_authorised

                    if check_user.is_admin != new_user.is_admin:
                        check_user.is_admin = new_user.is_admin
            session.commit()
            session.close()

    def check_admin_status(self, username):
        """Checks if a user has admin status.

        Args:
            username (str): The email of the user to check.

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
        """Loads all users from the database.

        Returns:
            list: A list of all users in the database.
        """
        with self.Session() as session:
            all_users = session.query(model.User).all()
            session.close()
            return all_users

    def approve_user(self, username):
        """Approves a user by updating their authorization status.

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
        """Rejects a user by updating their authorization status.

        Args:
            username (str): The email of the user to reject.
        """
        with self.Session() as session:
            user = session.query(model.User).filter_by(email=username).first()
            user.is_authorised = False
            session.commit()
            session.close()

