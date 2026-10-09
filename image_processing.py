import os
import cv2


def process_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("The uploaded file is not a valid image.")

    height, width = image.shape[:2]
    largest_side = max(height, width)
    if largest_side > 1600:
        scale = 1600 / largest_side
        image = cv2.resize(image, None, fx=scale, fy=scale)

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    contrast = cv2.equalizeHist(grayscale)
    processed = cv2.GaussianBlur(contrast, (3, 3), 0)

    processed_path = os.path.splitext(image_path)[0] + "_processed.jpg"
    if not cv2.imwrite(processed_path, processed):
        raise ValueError("The processed image could not be saved.")
    return processed_path
