import json
import os
from llama_cpp import Llama


MODEL_PATH = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MEMORY_FILE = "memory.json"

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    verbose=False  
)


def ask_ai(prompt):
    response = llm.create_chat_completion(
        messages=[
            {"role": "user", "content": prompt}
        ],
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