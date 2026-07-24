import os
import shutil
try:
    from typhoon_ocr import ocr_document
except ImportError:
    ocr_document = None


def get_files_in_folder(path):
    """Get all files from a specific folder."""
    if not os.path.exists(path):
        return []
    all_items = [os.path.join(path, f) for f in os.listdir(path)]
    return [f for f in all_items if os.path.isfile(f)]


def extract_text_from_image(path):
    if ocr_document is None:
        return ""
    try:
        return ocr_document(path)
    except Exception as e:
        print(f"OCR failed for {path}: {e}")
        return ""


def move_file(old_path, category, base_dir):
    """Move file to organized category folder within base_dir."""
    category_path = os.path.join(base_dir, "organized_files", category)
    os.makedirs(category_path, exist_ok=True)

    original_filename = os.path.basename(old_path)
    new_path = os.path.join(category_path, original_filename)

    # Handle duplicate filenames
    counter = 1
    name, ext = os.path.splitext(original_filename)
    while os.path.exists(new_path):
        new_filename = f"{name}_{counter}{ext}"
        new_path = os.path.join(category_path, new_filename)
        counter += 1

    shutil.move(old_path, new_path)
    return new_path
