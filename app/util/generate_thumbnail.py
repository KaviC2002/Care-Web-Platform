import os
import cv2

def generate_thumbnail(image_path, thumbnail_dir, thumbnail_size=(150, 150)):
    """Generates a thumbnail for each image, taking up less memory and space"""
    image = cv2.imread(image_path)
    thumbnail = cv2.resize(image, thumbnail_size, interpolation=cv2.INTER_AREA)

    if not os.path.exists(thumbnail_dir):
        os.makedirs(thumbnail_dir)

    filename = os.path.basename(image_path)
    thumbnail_path = os.path.join(thumbnail_dir, filename)

    cv2.imwrite(thumbnail_path, thumbnail)

    return thumbnail_path