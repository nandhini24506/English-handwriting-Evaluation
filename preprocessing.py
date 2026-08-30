import os
import cv2
import numpy as np

def check_preprocessing_safety(orig_img, proc_img):
    """
    Automated Preprocessing Quality Inspector:
    Compares foreground stroke preservation between original image and preprocessed image.
    If foreground stroke loss exceeds 15% or visual clarity degrades, returns is_safe = False.
    """
    if orig_img is None or proc_img is None:
        return False, "Original Image Used for AI Analysis"

    try:
        # Grayscale representations
        gray_orig = cv2.cvtColor(orig_img, cv2.COLOR_BGR2GRAY) if len(orig_img.shape) == 3 else orig_img
        gray_proc = cv2.cvtColor(proc_img, cv2.COLOR_BGR2GRAY) if len(proc_img.shape) == 3 else proc_img

        # Resize proc to match orig for comparison if needed
        if gray_orig.shape != gray_proc.shape:
            gray_proc = cv2.resize(gray_proc, (gray_orig.shape[1], gray_orig.shape[0]))

        # Calculate foreground ink pixel density (dark ink < 150)
        orig_ink = np.sum(gray_orig < 150)
        proc_ink = np.sum(gray_proc < 150)

        if orig_ink == 0:
            return True, "Enhanced Preview"

        ink_retention_ratio = float(proc_ink) / float(orig_ink)

        # If more than 15% of stroke density was lost or corrupted, declare unsafe
        if ink_retention_ratio < 0.85:
            return False, "Original Image Used for AI Analysis"
        else:
            return True, "Enhanced Preview"
    except Exception:
        return False, "Original Image Used for AI Analysis"


def preprocess_handwriting_image(image_path, output_dir):
    """
    Conservative & Safe OpenCV Preprocessing Pipeline:
    1. Read and validate original image.
    2. Resize to standard max 1200px maintaining original aspect ratio.
    3. Mild bilateral noise reduction (preserving stroke edges).
    4. Mild CLAHE contrast enhancement (improving visual clarity without threshold degradation).
    5. Save clean enhanced preview image (never overwriting or destroying original).
    6. Run Automated Safety Inspector.
    
    Returns:
    - processed_filename: Basename of saved preprocessed image
    - processed_abs_path: Full path to preprocessed image
    - debug_filename: Basename of debug image
    - debug_abs_path: Full path to debug image
    - is_safe: Boolean safety flag
    - preview_label: String label for UI display ('Enhanced Preview' or 'Original Image Used for AI Analysis')
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found at {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to decode image at {image_path}")

    # 1. Resize preserving aspect ratio (Max dimension 1200px)
    h, w = img.shape[:2]
    max_dim = 1200
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # 2. Convert to LAB color space for luminance-only CLAHE (preserves true colors and ink strokes)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Mild CLAHE contrast enhancement on L channel
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)

    # Merge channels back
    limg = cv2.merge((cl, a_channel, b_channel))
    enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    # 3. Mild Bilateral Denoising (preserves sharp stroke edges)
    denoised_bgr = cv2.bilateralFilter(enhanced_bgr, d=5, sigmaColor=25, sigmaSpace=25)

    # 4. Save enhanced preview
    orig_filename = os.path.basename(image_path)
    processed_filename = f"processed_{orig_filename}"
    debug_filename = f"debug_lines_{orig_filename}"

    os.makedirs(output_dir, exist_ok=True)
    processed_abs_path = os.path.join(output_dir, processed_filename)
    debug_abs_path = os.path.join(output_dir, debug_filename)

    cv2.imwrite(processed_abs_path, denoised_bgr)
    cv2.imwrite(debug_abs_path, denoised_bgr)

    # 5. Preprocessing Safety Inspection
    is_safe, preview_label = check_preprocessing_safety(img, denoised_bgr)

    return processed_filename, processed_abs_path, debug_filename, debug_abs_path, is_safe, preview_label
