import os
import cv2
import numpy as np
from ultralytics import YOLO

def draw_bounding_box(image, bbox, confidence):
    x1, y1, x2, y2 = list(map(round, bbox))
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 25)

    label = f"Conf: {confidence:.3f}"
    
    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 5, 2)
    
    text_x = x1
    text_y = y1 - 10 if y1 - 10 > 10 else y1 + 20
    
    cv2.rectangle(image, (text_x, text_y - h - 5), (text_x + w, text_y + 5), (0, 0, 255), -1)
    cv2.putText(image, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 10)
    
    return image

def crop_image(image, bbox):
    x1, y1, x2, y2 = list(map(round, bbox))
    return image[y1:y2, x1:x2, :]

def make_inference_detection(yolo, image):
    prediction = yolo(image)[0]
    class_dict = prediction.names
    array_of_confidences = prediction.boxes.conf.numpy()
    array_of_labels = prediction.boxes.cls.numpy()

    if len(array_of_confidences) == 0:
        return None, None, None, None

    max_conf_index = np.argmax(array_of_confidences)
    max_conf, label = array_of_confidences[max_conf_index], class_dict[int(array_of_labels[max_conf_index])]
    bounding_box = prediction.boxes.xyxy.numpy()[0]

    image_with_box = draw_bounding_box(image.copy(), bounding_box, max_conf)
    image_with_crop = crop_image(image, bounding_box)

    return image_with_box, image_with_crop, label, max_conf

def main(images):
    DEVICE = "cpu"

    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'detection_model', 'best_50.pt'))
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"The model file '{model_path}' does not exist.")

    yolo = YOLO(model_path).to(DEVICE)
    image_with_boxes = []

    for image in images:
        bbox_image, cropped_image, label, confidence = make_inference_detection(yolo, image)
        if bbox_image is not None:
            image_with_boxes.append((bbox_image, cropped_image, label, confidence))

    return image_with_boxes
