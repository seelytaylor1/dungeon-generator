import random
import requests
import subprocess
import socket
import sys
import time
import json
import re
from pathlib import Path

# Dungeon configuration tables
DUNGEON_TABLES = {
    "history": [
        "Ancient fortress of a fallen empire",
        "Sacred temple to a forgotten deity",
        "Royal crypt complex for a disgraced dynasty",
        "Mining colony that delved too deep",
        "Wizard's arcane research facility",
        "Interdimensional nexus chamber"
    ],
    "purpose": [
        "Prison for otherworldly creatures",
        "Repository of forbidden knowledge",
        "Testing ground for experimental magic",
        "Harvesting station for soul energy",
        "Sanctuary during apocalyptic events",
        "Trading hub for planar entities"
    ],
    "ruin": [
        "Siege by an enemy kingdom",
        "Magical experiment gone wrong",
        "Leader succumbed to corruption",
        "Plague of flesh-warping magic",
        "Portal to the Far Realm opened",
        "Rebellion of created constructs"
    ]
}

# Updated Ollama paths with your custom location
OLLAMA_PATHS = {
    'win32': [
        Path(r"C:\Users\Taylor\AppData\Local\Programs\Ollama\ollama app.exe"),
        Path(r"C:\Program Files\Ollama\ollama.exe"),
    ],
    'darwin': [
        Path("/Applications/Ollama.app/Contents/MacOS/ollama")
    ],
    'linux': [
        Path("/usr/bin/ollama")
    ]
}

def is_ollama_running():
    """Check if Ollama API is responsive"""
    try:
        response = requests.get("http://localhost:11434/", timeout=2)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False

def find_ollama_executable():
    """Locate Ollama installation"""
    platform = sys.platform
    for path in OLLAMA_PATHS.get(platform, []):
        if path.exists():
            return path
    return None

def start_ollama():
    """Attempt to launch Ollama automatically"""
    print("🦙 Starting Ollama service...")

    ollama_path = find_ollama_executable()
    if not ollama_path:
        print("Error: Ollama not found! Please install from https://ollama.com/download")
        return False

    try:
        # Handle spaces in Windows path
        cmd = f'"{ollama_path}" serve' if ' ' in str(ollama_path) else [ollama_path, "serve"]

        startupinfo = subprocess.STARTUPINFO()
        if sys.platform == 'win32':
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            shell=True if ' ' in str(ollama_path) else False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        # Wait for service to start
        for _ in range(30):
            if is_ollama_running():
                print("✅ Ollama service ready!")
                return True
            time.sleep(1)

        print("Timeout: Ollama didn't start within 30 seconds")
        return False

    except Exception as e:
        print(f"Failed to start Ollama: {str(e)}")
        return False

def check_ollama_health():
    """Verify Ollama is fully operational"""
    try:
        # Basic connectivity check
        response = requests.get("http://localhost:11434/", timeout=5)
        if response.status_code != 200:
            return False, "Ollama responded with unexpected status"

        # Verify API endpoint
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama2", "prompt": "test"},
            timeout=10
        )

        if response.status_code == 404:
            return False, "API endpoint not found - update Ollama"
        if response.status_code == 400:
            return True, "API working (model missing is normal)"

        return True, "Ollama fully operational"

    except requests.ConnectionError:
        return False, "Ollama not running"
    except Exception as e:
        return False, f"Health check failed: {str(e)}"

def get_installed_models():
    """List installed models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        return [m["name"] for m in response.json()["models"]]
    except Exception:
        return []

def generate_dungeon_lore(model="deepseek-r1:1.5b"):
    """Generate lore with enhanced diagnostics"""
    # Check model installation
    installed_models = get_installed_models()
    if model not in installed_models:
        return f"Error: Model '{model}' not installed. Run 'ollama pull {model}' first"

    # Roll dungeon aspects
    history = random.choice(DUNGEON_TABLES["history"])
    purpose = random.choice(DUNGEON_TABLES["purpose"])
    ruin = random.choice(DUNGEON_TABLES["ruin"])

    # Create prompt
    prompt = f"""We're writing lore for a game of Shadowdark RPG. This game focuses on oldschool tabletop scenario's
     in a dark fantasy world. Combine these dungeon aspects into one paragraph of vivid lore:
    - History: {history}
    - Original Purpose: {purpose}
    - Cause of Ruin: {ruin}
    Paragraph:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            },
            timeout=60
        )
        response.raise_for_status()

        # Remove <think> tags and their content
        clean_lore = re.sub(r'<think>.*?</think>', '', response.json()["response"], flags=re.DOTALL)
        return clean_lore.strip()

    except Exception as e:
        return f"Error generating lore: {str(e)}"

def main():
    print("🧙♂️ Generating dungeon lore...")

    # First ensure we have basic connectivity
    if not is_ollama_running():
        print("  Starting Ollama service...")
        if not start_ollama():
            print("❌ Failed to start Ollama")
            return

    lore = generate_dungeon_lore()

    print("\n=== DUNGEON LORE ===")
    print(lore)

    # Save as Markdown with proper formatting
    with open("dungeon_lore.md", "w") as f:
        f.write(f"# Dungeon Lore\n\n")
        f.write(lore)
        f.write("\n\n## Dungeon Aspects")
        f.write("\n- **History**: " + random.choice(DUNGEON_TABLES["history"]))
        f.write("\n- **Original Purpose**: " + random.choice(DUNGEON_TABLES["purpose"]))
        f.write("\n- **Cause of Ruin**: " + random.choice(DUNGEON_TABLES["ruin"]))
    print("\n📄 Lore saved to dungeon_lore.md")


if __name__ == "__main__":
    print("🛠️ Diagnostic Checks:")
    print(f"- Ollama running: {is_ollama_running()}")
    print(f"- Installed models: {get_installed_models()}")

    # Run main process
    main()