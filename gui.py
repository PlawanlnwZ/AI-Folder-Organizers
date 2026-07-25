import sys
import os

# Redirect standard output and error streams when compiled with --noconsole
if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import os
import sys
import queue
from ai_utils import ensure_model_exists, analyze_file, save_memory
from config import SUPPORTED_IMAGE_TYPES
from file_utils_gui import get_files_in_folder, extract_text_from_image, move_file

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FileOrganizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("File Organizer")
        self.geometry("850x620")
        self.minsize(700, 500)

        # Set Window Titlebar Icon if icon file exists
        icon_p = resource_path("logo.ico")
        if os.path.exists(icon_p):
            self.iconbitmap(icon_p)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("dark-blue")

        # --- State ---
        self.target_folder = ctk.StringVar(value="")
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()

        # Show Loading Screen first
        self._build_loading_ui()

        # Start loading the AI model in the background
        threading.Thread(target=self._init_ai_backend, daemon=True).start()

    def _build_loading_ui(self):
        self.loading_frame = ctk.CTkFrame(self)
        self.loading_frame.pack(fill="both", expand=True)

        self.loading_label = ctk.CTkLabel(
            self.loading_frame, 
            text="Initializing AI Engine...", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.loading_label.pack(pady=(180, 20))

        self.progress_bar = ctk.CTkProgressBar(self.loading_frame, mode="indeterminate", width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()

    def _update_loading_status(self, text):
        self.after(0, lambda: self.loading_label.configure(text=text))

    def _init_ai_backend(self):
        try:
            ensure_model_exists(status_callback=self._update_loading_status)
            self.after(0, self._on_ai_ready)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Initialization Error", f"Failed to load AI model: {e}"))

    def _on_ai_ready(self):
        self.loading_frame.destroy()
        self._build_ui()
        self._process_log_queue()
        self._log("AI Engine Ready.")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Title Frame
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(25, 5))
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_frame,
            text="🗂️ File Organizer",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_frame,
            text="AI-powered folder monitoring & automatic file sorting",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Folder Selection
        folder_card = ctk.CTkFrame(self)
        folder_card.grid(row=1, column=0, sticky="ew", padx=25, pady=(20, 10))
        folder_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            folder_card,
            text="Target Folder",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 4))

        inner = ctk.CTkFrame(folder_card, fg_color="transparent")
        inner.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 12))
        inner.grid_columnconfigure(0, weight=1)

        self.folder_entry = ctk.CTkEntry(
            inner,
            textvariable=self.target_folder,
            placeholder_text="Choose a folder to watch…",
            height=38,
            font=ctk.CTkFont(size=13),
        )
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            inner,
            text="Browse",
            width=100,
            height=38,
            command=self._browse_folder,
        ).grid(row=0, column=1)

        # Controls
        ctrl_card = ctk.CTkFrame(self)
        ctrl_card.grid(row=2, column=0, sticky="ew", padx=25, pady=(0, 10))

        self.start_btn = ctk.CTkButton(
            ctrl_card,
            text="▶ Start Monitoring",
            width=170,
            height=38,
            command=self._toggle_monitoring,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.start_btn.pack(side="left", padx=(15, 10), pady=12)

        self.clear_btn = ctk.CTkButton(
            ctrl_card,
            text="🗑 Clear Memory",
            width=170,
            height=38,
            command=self._clear_memory,
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.clear_btn.pack(side="left", padx=(0, 15), pady=12)

        self.status_label = ctk.CTkLabel(
            ctrl_card,
            text="Status: Idle",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.status_label.pack(side="right", padx=15)

        # Log Console
        log_card = ctk.CTkFrame(self)
        log_card.grid(row=3, column=0, sticky="nsew", padx=25, pady=(0, 20))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            log_card,
            text="Activity Log",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.log_box = ctk.CTkTextbox(
            log_card,
            wrap="word",
            font=ctk.CTkFont(family="SF Mono", size=12),
            state="disabled",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 12))

    def _browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.target_folder.set(folder)
            self._log(f"Folder selected: {folder}")

    def _log(self, message):
        self.log_queue.put(message)

    def _process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", f'[{time.strftime("%H:%M:%S")}] {msg}\n')
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._process_log_queue)

    def _toggle_monitoring(self):
        if self.is_monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        folder = self.target_folder.get().strip()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Invalid Path", "The selected folder does not exist.")
            return

        self.is_monitoring = True
        self.stop_event.clear()
        self.start_btn.configure(
            text="⏹ Stop Monitoring",
            fg_color="#ef4444",
            hover_color="#dc2626",
        )
        self.status_label.configure(text="Status: Monitoring…", text_color="#10b981")
        self._log("Monitoring started.")

        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(folder,), daemon=True
        )
        self.monitor_thread.start()

    def _stop_monitoring(self):
        self.is_monitoring = False
        self.stop_event.set()
        self.start_btn.configure(
            text="▶ Start Monitoring",
            fg_color="#10b981",
            hover_color="#059669",
        )
        self.status_label.configure(text="Status: Idle", text_color="gray")
        self._log("Monitoring stopped.")

    def _monitor_loop(self, folder):
        processed = set()
        while not self.stop_event.is_set():
            try:
                files = get_files_in_folder(folder)
                for file_path in files:
                    if self.stop_event.is_set():
                        break
                    if file_path in processed:
                        continue
                    if os.path.isfile(file_path):
                        try:
                            self._process_file(file_path, folder)
                            processed.add(file_path)
                        except Exception as e:
                            self._log(f"Error processing {os.path.basename(file_path)}: {e}")

                if not self.stop_event.is_set():
                    time.sleep(5)
            except Exception as e:
                self._log(f"Monitor loop error: {e}")
                time.sleep(5)

    def _process_file(self, file_path, base_dir):
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        content = ""

        if ext in SUPPORTED_IMAGE_TYPES:
            self._log(f"OCR  → {filename}")
            content = extract_text_from_image(file_path)

        self._log(f"AI   → categorizing {filename}")
        category = analyze_file(filename, content)

        new_path = move_file(file_path, category, base_dir)
        self._log(f'Done → moved to "{category}"')

    def _clear_memory(self):
        try:
            save_memory([])
            self._log("Memory cleared.")
            messagebox.showinfo("Success", "AI memory has been cleared.")
        except Exception as e:
            self._log(f"Clear memory failed: {e}")
            messagebox.showerror("Error", f"Failed to clear memory: {e}")


if __name__ == "__main__":
    app = FileOrganizerApp()
    app.mainloop()