import os
import shutil
from typhoon_ocr import ocr_document


def get_downloads_path():
    return os.path.expanduser("~/OneDrive/Documents/examplemessifolder")


def get_all_files():
    path = get_downloads_path()
    return [os.path.join(path, f) for f in os.listdir(path)]


def extract_text_from_image(path):
    try:
        return ocr_document(path)
    except Exception as e:
        print(f"OCR failed for {path}: {e}")
        return ""


def move_file(old_path, new_name, category):
    base_dir = os.path.abspath("organized_files")
    category_path = os.path.join(base_dir, category)

    os.makedirs(category_path, exist_ok=True)

    ext = os.path.splitext(old_path)[1]
    new_path = os.path.join(category_path, new_name + ext)

    shutil.move(old_path, new_path)

    print(f"Moved: {old_path} → {new_path}")