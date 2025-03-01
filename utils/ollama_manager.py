import shutil

import requests
import subprocess
import sys
import time
import json
import logging
import socket
import psutil
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Configuration constants
OLLAMA_PATHS = {
    'win32': [
        Path(r"C:\Program Files\Ollama\ollama.exe"),
        Path(r"C:\Users\Taylor\AppData\Local\Programs\Ollama\ollama app.exe")
    ],
    'darwin': [Path("/Applications/Ollama.app/Contents/MacOS/ollama")],
    'linux': [Path("/usr/bin/ollama")]
}

OLLAMA_URL = "http://localhost:11434/"
OLLAMA_PORT = 11434
API_TIMEOUT = 240
STARTUP_TIMEOUT = 120
MINIMUM_MODEL_COUNT = 1


def is_ollama_running() -> bool:
    """Check if Ollama service is running using port check."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', OLLAMA_PORT)) == 0


def safe_process_check() -> bool:
    """Safely check for Ollama processes."""
    try:
        for proc in psutil.process_iter(['name']):
            try:
                if 'ollama' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except Exception as e:
        logger.debug(f"Process check error: {str(e)}")
        return False


def start_ollama() -> bool:
    """Start Ollama service with improved error handling."""
    try:
        if is_ollama_running() or safe_process_check():
            logger.info("Ollama service already running")
            return True

        ollama_path = find_ollama_executable()
        if not ollama_path:
            logger.error("Ollama executable not found")
            return False

        startup_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        subprocess.Popen(
            [str(ollama_path), "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=startup_flags
        )

        # Wait for service to become available
        start_time = time.time()
        while (time.time() - start_time) < STARTUP_TIMEOUT:
            if is_ollama_running():
                logger.info("Ollama service started successfully")
                return True
            time.sleep(1)

        logger.error("Ollama failed to start within timeout")
        return False

    except Exception as e:
        logger.error(f"Critical failure during startup: {str(e)}")
        return False


def find_ollama_executable() -> Optional[Path]:
    """Locate Ollama executable with fallback to PATH."""
    for path in OLLAMA_PATHS.get(sys.platform, []):
        expanded = path.expanduser()
        if expanded.exists():
            logger.debug(f"Found Ollama at {expanded}")
            return expanded

    # Fallback to system PATH
    which_ollama = shutil.which('ollama')
    if which_ollama:
        logger.debug(f"Found Ollama in PATH: {which_ollama}")
        return Path(which_ollama)

    logger.warning("Ollama executable not found")
    return None


def get_installed_models(retries: int = 3) -> List[str]:
    """Retrieve installed models with enhanced reliability."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                f"http://localhost:{OLLAMA_PORT}/api/tags",
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", []) if m.get("name")]
        except requests.RequestException as e:
            logger.warning(f"Model fetch failed (attempt {attempt}): {str(e)}")
            time.sleep(1)
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Invalid API response: {str(e)}")
            break
    return []


def initialize_service() -> bool:
    """Initialize service with comprehensive checks."""
    if not start_ollama():
        logger.error("""
        Failed to initialize Ollama. Verify:
        1. Ollama is installed (https://ollama.ai)
        2. Added to system PATH
        3. No firewall blocking port 11434
        """)
        return False

    if len(get_installed_models()) < MINIMUM_MODEL_COUNT:
        logger.error(f"No models installed. Run 'ollama pull <model>' first")
        return False

    return True


def generate_with_retry(
        prompt: str,
        model: str,
        retries: int = 3,
        temperature: float = 0.7,
        top_p: float = 0.9
) -> Optional[Dict[str, Any]]:
    """Generate text with comprehensive error handling and retries."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "num_ctx": 4096  # Increased context window
                    }
                },
                timeout=API_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Non-JSON response received")

            if "response" not in result:
                raise ValueError("Missing 'response' field in API result")

            if not result["response"].strip():
                raise ValueError("Empty response from model")

            return result

        except requests.RequestException as e:
            logger.warning(f"API request failed (attempt {attempt}/{retries}): {str(e)}")
            time.sleep(1 * attempt)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Response validation failed: {str(e)}")
            if attempt == retries:
                break
            time.sleep(1 * attempt)

    logger.error(f"Generation failed after {retries} attempts")
    return None


def cleanup_processes() -> None:
    """Terminate Ollama processes safely."""
    try:
        for proc in psutil.process_iter(['name']):
            try:
                if 'ollama' in proc.info['name'].lower():
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.debug(f"Cleanup error: {str(e)}")
