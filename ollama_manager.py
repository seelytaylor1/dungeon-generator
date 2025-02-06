# ollama_manager.py
import requests
import subprocess
import sys
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
import psutil  # Required for process management

logger = logging.getLogger(__name__)


def check_model_installed(model: str) -> bool:
    """Legacy compatibility wrapper"""
    return validate_model_config(model)

# Configuration constants
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
API_TIMEOUT = 45  # Increase timeout for complex generations
STARTUP_TIMEOUT = 45
MINIMUM_MODEL_COUNT = 1  # Fail if no models installed

def is_ollama_running(retries: int = 3) -> bool:
    """Check if Ollama service is responsive with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            if response.status_code == 200:
                return True
            logger.debug(f"Ollama API responded with HTTP {response.status_code}")
        except requests.RequestException as e:
            logger.debug(f"Connection attempt {attempt}/{retries} failed: {str(e)}")
        time.sleep(1 * attempt)
    return False

def start_ollama() -> bool:
    """Start Ollama service with comprehensive process management."""
    try:
        # Check for existing processes
        for proc in psutil.process_iter(['name', 'exe']):
            if any('ollama' in part.lower() for part in [proc.info['name'], str(proc.info['exe'])]):
                logger.info("Found existing Ollama process")
                return True

        # Locate executable
        ollama_path = find_ollama_executable()
        if not ollama_path:
            logger.error("No Ollama executable found")
            return False

        # Start new process
        process = subprocess.Popen(
            [str(ollama_path), "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=get_startup_info(),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        # Wait for service initialization
        start_time = time.time()
        while (time.time() - start_time) < STARTUP_TIMEOUT:
            if is_ollama_running(retries=1):
                logger.info("Ollama service started successfully")
                return True
            time.sleep(1)

        # Cleanup if timeout
        logger.warning("Startup timeout reached - terminating process")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return False

    except Exception as e:
        logger.exception("Critical failure during Ollama startup")
        return False

def get_startup_info() -> subprocess.STARTUPINFO:
    """Get platform-specific startup configuration."""
    startupinfo = subprocess.STARTUPINFO()
    if sys.platform == 'win32':
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo

def find_ollama_executable() -> Optional[Path]:
    """Locate Ollama executable with path validation."""
    for path in OLLAMA_PATHS.get(sys.platform, []):
        expanded_path = path.expanduser()
        if expanded_path.exists():
            logger.debug(f"Found Ollama executable at {expanded_path}")
            return expanded_path
    logger.warning("No valid Ollama executable found in configured paths")
    return None

def get_installed_models(retries: int = 3) -> List[str]:
    """Retrieve list of installed models with robust error handling."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                f"{OLLAMA_URL}/api/tags",
                timeout=API_TIMEOUT
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            valid_models = [m["name"] for m in models if m.get("name")]

            if not valid_models:
                logger.error("No valid models found in Ollama response")

            return valid_models

        except requests.RequestException as e:
            logger.warning(f"Model list fetch failed (attempt {attempt}/{retries}): {str(e)}")
            time.sleep(1 * attempt)
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Invalid API response format: {str(e)}")
            break

    logger.error("Failed to retrieve installed models after multiple attempts")
    return []

def validate_model_config(model: str) -> bool:
    """Validate model configuration with detailed diagnostics."""
    if not model.strip():
        logger.error("Empty model name in configuration")
        return False

    if ':' not in model:
        logger.warning(f"Model specification '{model}' missing version tag")

    installed_models = get_installed_models()

    if not installed_models:
        logger.error("No models installed - use 'ollama pull <model>' first")
        return False

    if model not in installed_models:
        logger.error(f"Model '{model}' not found in installed models: {', '.join(installed_models)}")
        return False

    return True

def initialize_service() -> bool:
    """Initialize Ollama service with full verification."""
    if is_ollama_running():
        logger.info("Ollama service already running")
        if len(get_installed_models()) >= MINIMUM_MODEL_COUNT:
            return True
        logger.error("No valid models found despite running service")
        return False

    logger.info("Starting Ollama service...")
    if not start_ollama():
        return False

    # Verify functional service
    for _ in range(10):
        if len(get_installed_models()) >= MINIMUM_MODEL_COUNT:
            return True
        time.sleep(1)

    logger.error("Service started but no models detected")
    return False

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
    """Clean up any lingering Ollama processes."""
    for proc in psutil.process_iter(['name', 'exe']):
        if any('ollama' in part.lower() for part in [proc.info['name'], str(proc.info['exe'])]):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                pass
