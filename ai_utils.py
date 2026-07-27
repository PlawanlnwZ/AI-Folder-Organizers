import json
import os
import sys
import requests
import keyring


# ── Keyring & API Config ───────────────────────────────────────────────────
SERVICE_NAME = "AIFolderOrganizer"
KEY_NAME = "api_key"

TYPHOON_API_URL = "https://api.opentyphoon.ai/v1/chat/completions"
TYPHOON_MODEL = "typhoon-v2.5-30b-a3b-instruct"


def get_saved_api_key():
    """Retrieves stored API key from Windows Vault / Keychain, falling back to env."""
    key = keyring.get_password(SERVICE_NAME, KEY_NAME)
    if not key:
        key = os.environ.get("TYPHOON_API_KEY", "")
    return key


def save_api_key(api_key):
    """Saves the API key securely into Windows Credential Manager / Keychain."""
    keyring.set_password(SERVICE_NAME, KEY_NAME, api_key.strip())


def delete_api_key():
    """Deletes the saved API key if requested."""
    try:
        keyring.delete_password(SERVICE_NAME, KEY_NAME)
    except keyring.errors.PasswordDeleteError:
        pass


# ── App Data & Path Helpers ─────────────────────────────────────────────────
def get_app_data_dir():
    """Returns the user AppData directory for storing app memory."""
    if sys.platform == "win32":
        base_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base_dir = os.path.expanduser("~/.local/share")

    app_dir = os.path.join(base_dir, "AIFolderOrganizer")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


APP_DATA_DIR = get_app_data_dir()
MEMORY_FILE = os.path.join(APP_DATA_DIR, "memory.json")


# ── Online API Call ─────────────────────────────────────────────────────────
def ask_ai(prompt):
    """Sends prompt to OpenTyphoon API using the saved key."""
    api_key = get_saved_api_key()
    if not api_key:
        raise ValueError("API Key is missing. Please enter your API Key in the settings.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": TYPHOON_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.3,
    }

    response = requests.post(TYPHOON_API_URL, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        raise RuntimeError(f"API Error ({response.status_code}): {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"]


# ── Memory Storage ──────────────────────────────────────────────────────────
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def format_memory(memory):
    return "\n".join(
        [f"{m['original']} -> {m['category']}" for m in memory[-10:]]
    )


# ── Core Analysis Pipeline ──────────────────────────────────────────────────
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

    Return ONLY:
    Category: <category>
    """

    result = ask_ai(prompt)

    # Safely extract category string
    category = "Other"
    for line in result.split("\n"):
        line = line.strip()
        if line.lower().startswith("category:"):
            category = line.split(":", 1)[1].strip()
            break

    # Save to history memory
    memory.append({
        "original": filename,
        "category": category,
    })
    save_memory(memory)

    return category