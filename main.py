import os
import time
from ai_utils import analyze_file
from file_utils import (
    get_all_files,
    extract_text_from_image,
    move_file
)
from config import SUPPORTED_IMAGE_TYPES


def process_file(file_path):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    content = ""

    # If image → extract text
    if ext in SUPPORTED_IMAGE_TYPES:
        content = extract_text_from_image(file_path)

    new_name, category = analyze_file(filename, content)

    move_file(file_path, new_name, category)


def main():
    while True:
        files = get_all_files()

        for file in files:
            if os.path.isfile(file):
                try:
                    process_file(file)
                except Exception as e:
                    print(f"Error processing {file}: {e}")

        print("Waiting for new files...")
        time.sleep(60) 


if __name__ == "__main__":
    main()