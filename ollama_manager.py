# ollama_manager.py
import requests
import subprocess
import sys
import time
from pathlib import Path
import logging

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

OLLAMA_URL = "http://localhost:11434/"

def is_ollama_running():
    try:
        response = requests.get(OLLAMA_URL, timeout=2)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False

def start_ollama():
    ollama_path = find_ollama_executable()
    if not ollama_path:
        logging.error("Ollama not found in configured paths")
        return False

    try:
        cmd = [ollama_path, "serve"] if ' ' not in str(ollama_path) else f'"{ollama_path}" serve'
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startup_info(),
            shell=True if ' ' in str(ollama_path) else False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        for _ in range(30):
            if is_ollama_running():
                return True
            time.sleep(1)
        return False

    except Exception as e:
        logging.exception("Failed to start Ollama")
        return False

def startup_info():
    startupinfo = subprocess.STARTUPINFO()
    if sys.platform == 'win32':
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo

def find_ollama_executable():
    for path in OLLAMA_PATHS.get(sys.platform, []):
        if path.exists():
            return path
    return None

def check_model_installed(model):
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        return any(m["name"] == model for m in response.json()["models"])
    except Exception:
        logging.exception(f"Failed to check if model '{model}' is installed")
        return False

def initialize_service():
    return is_ollama_running() or start_ollama()
