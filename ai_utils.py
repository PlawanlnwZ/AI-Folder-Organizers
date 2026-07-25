import json
import os
import keyring
from dotenv import load_dotenv
 
load_dotenv()

SERVICE_NAME = "AIFolderOrganizer"
KEY_NAME = "api_key"

def get_saved_api_key():
    """Retrieves the stored API key from Windows Credential Manager / Keychain."""
    return keyring.get_password(SERVICE_NAME, KEY_NAME)

def save_api_key(api_key):
    """Saves the API key securely into Windows Credential Manager / Keychain."""
    keyring.set_password(SERVICE_NAME, KEY_NAME, api_key.strip())

def delete_api_key():
    """Deletes the saved API key if requested."""
    try:
        keyring.delete_password(SERVICE_NAME, KEY_NAME)
    except keyring.errors.PasswordDeleteError:
        pass

TYPHOON_API_URL = "https://api.opentyphoon.ai/v1/chat/completions"
TYPHOON_MODEL = "typhoon-v2.5-30b-a3b-instruct"
TYPHOON_API_KEY = os.environ.get("TYPHOON_API_KEY")

APP_DATA_DIR = get_app_data_dir()
MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_PATH = os.path.join(APP_DATA_DIR, MODEL_FILENAME)
MEMORY_FILE = os.path.join(APP_DATA_DIR, "memory.json")

# Global LLM instance initialized after check
llm = None

def ensure_model_exists(status_callback=None):
    """Checks for the model in AppData and downloads it if missing."""
    global llm
    if not os.path.exists(MODEL_PATH):
        if status_callback:
            status_callback("Downloading Qwen AI Model (~1 GB)... Please wait.")
        
        hf_hub_download(
            repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
            filename=MODEL_FILENAME,
            local_dir=APP_DATA_DIR,
            disable_tqdm=True  # <--- Disables terminal progress bar attempt
        )

    if status_callback:
        status_callback("Loading AI Model into memory...")

    if llm is None:
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            verbose=False
        )

def ask_ai(prompt):
    if llm is None:
        raise RuntimeError("LLM is not initialized.")
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.3,
    )
    return response["choices"][0]["message"]["content"]

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def format_memory(memory):
    return "\n".join(
        [f"{m['original']} -> {m['category']}" for m in memory[-10:]]
    )

def analyze_file(filename, content=""):
    memory = load_memory()
    history = format_memory(memory)

    prompt = f"""
    You are an intelligent file organization agent.

    Your job is to organize files consistently and logically.

    Previous decisions:
    {history}

    Now analyze this file:

    Filename: {filename}
    Content: {content}

    Think step-by-step:
    1. What type of file is this?
    2. What is its purpose?
    3. What would be a consistent category based on past decisions?
    
    Then decide:

    Category: <category>

    Return ONLY:
    Category: ...
    """

    result = ask_ai(prompt)

    category = "Other"
    for line in result.split("\n"):
        line = line.strip().lower()
        if line.startswith("category:"):
            category = line.split("category:")[1].strip()

    memory.append({
        "original": filename,
        "category": category,
    })

    save_memory(memory)

    return category