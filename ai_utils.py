import requests
import json
import os
from dotenv import load_dotenv
 
load_dotenv()

TYPHOON_API_URL = "https://api.opentyphoon.ai/v1/chat/completions"
TYPHOON_MODEL = "typhoon-v2.5-30b-a3b-instruct"
TYPHOON_API_KEY = os.environ.get("TYPHOON_API_KEY")

MEMORY_FILE = "memory.json"


def ask_ai(prompt):
    if not TYPHOON_API_KEY:
        raise RuntimeError(
            "TYPHOON_API_KEY environment variable is not set. "
            "Get an API key from https://playground.opentyphoon.ai and set it in .env files, e.g.:\n"
            "TYPHOON_API_KEY=your_key_here"
        )

    response = requests.post(
        TYPHOON_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TYPHOON_API_KEY}",
        },
        json={
            "model": TYPHOON_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 512,
            "temperature": 0.3,
            "stream": False,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


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