from datetime import datetime

import pytz
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Boolean, LargeBinary, Float
import bcrypt as s5_bcrypt
Base = declarative_base()

class User(Base):
    """Represents a user in the system.

    This class maps to the 'Users' table in the database and contains
    information about each user, including authentication and user
    management fields.

    Attributes:
        id (int): Unique identifier for the user (primary key).
        password (str): Hashed password of the user.
        email (str): Email address of the user.
        username (str): Username of the user (default is 'First').
        last_synced (datetime): Timestamp of the last synchronization (optional).
        is_authorised (bool): Indicates if the user is authorized (default is True).
        is_admin (bool): Indicates if the user has admin privileges (default is False).
        is_synced (bool): Indicates if the user has been synchronized (default is False).
        created_at (datetime): Timestamp of user creation.
        images (list): A list of associated Photo objects.
    """
    __tablename__ = 'Users'
    id = Column(Integer, primary_key=True)
    password = Column(String, nullable=False)
    email = Column(String, nullable=False)
    username = Column(String, nullable=False, default='First')  # Default value provided
    #last_name = Column(String, nullable=False, default='Last')  # Default value provided
    last_synced = Column(DateTime(timezone=True), default=None, nullable=True)
    is_authorised = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_synced = Column(Boolean, nullable=False, default = False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.timezone('Pacific/Auckland')), nullable=False)

    images = relationship('Photo', back_populates='user')
    def __repr__(self):
        return '<User(Name={firstname}, email={email})>'.format(firstname=self.username, email=self.email)

    #Set Password
    def set_password(self, password):
        """Set and hash the user's password.

        This method hashes the given password using bcrypt and
        stores the hashed password in the database.

        Args:
            password (str): The plaintext password to hash.
        """
        salt = s5_bcrypt.gensalt()
        self.password = s5_bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        """Check if the provided password matches the stored hashed password.

        Args:
            password (str): The plaintext password to check.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return s5_bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

class Photo(Base):
    """Represents a photo associated with a user.

    This class maps to the 'photos' table in the database and contains
    metadata about each photo, including user association, image data,
    and additional information.

    Attributes:
        user_id (int): Foreign key referencing the user who owns the photo.
        image_data (str): Raw image data or path to the image.
        description (str): Description of the photo (optional).
        is_synced (bool): Indicates if the photo has been synchronized (default is False).
        created_at (datetime): Timestamp of photo creation.
        confidence (float): Confidence score for image classification (optional).
        group_name (str): Name of the group the photo belongs to (optional).
        location (str): Geographical location where the photo was taken (optional).
        thumbnail (str): Path to the thumbnail image (optional).
        bbox (str): Bounding box coordinates for the image (optional).
        cropped (str): Path to the cropped version of the image (optional).
        name (str): Unique identifier for the photo (primary key).
        animal (str): Type of animal depicted in the photo (optional).

    """
    __tablename__ = 'photos'
    #id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('Users.id'), nullable=False)
    image_data = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_synced = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.timezone('Pacific/Auckland')), nullable=False)
    confidence = Column(Float, nullable=True)
    group_name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    bbox = Column(String, nullable=True)
    cropped = Column(String, nullable=True)
    name = Column(String, primary_key=True, nullable=False)
    animal = Column(String, nullable=True)


    user = relationship("User", back_populates="images")

    def __repr__(self):
        """Return a string representation of the Photo object."""
        return f"<Image(image_path='{self.image_data}', is_synced={self.is_synced})>"

