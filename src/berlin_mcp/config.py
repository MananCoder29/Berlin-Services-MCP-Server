import logging
import os
import tempfile
from pathlib import Path
import subprocess

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("berlin_mcp")

def _get_base_dir() -> Path:
    """Determine the base directory for data and filled forms."""
    is_cloud = bool(os.environ.get("PORT"))
    
    local_dir = Path.cwd()
    try:
        # Test write access
        test_file = local_dir / ".write_test"
        if not is_cloud:
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()
            return local_dir
    except (IOError, OSError):
        pass
    
    # Fallback to system temp directory
    temp_base = Path(tempfile.gettempdir()) / "berlin_mcp"
    temp_base.mkdir(parents=True, exist_ok=True)
    return temp_base

BASE_DATA_DIR = _get_base_dir()
IS_CLOUD = bool(os.environ.get("PORT"))

# Improved Remote/Cloud Detection
HAS_OPEN_CMD = subprocess.run(["which", "open"], capture_output=True).returncode == 0
IS_TEMP_DIR = str(BASE_DATA_DIR).startswith(tempfile.gettempdir())
IS_REMOTE = IS_CLOUD or (not HAS_OPEN_CMD and IS_TEMP_DIR)

logger.info(f"Using base storage directory: {BASE_DATA_DIR} (Cloud: {IS_CLOUD}, Remote: {IS_REMOTE})")

# Paths
CACHE_DIR = BASE_DATA_DIR / ".cache"
FORMS_CACHE_DIR = CACHE_DIR / "forms"
FILLED_FORMS_DIR = BASE_DATA_DIR / "filled_forms"
DEDUPE_FILE = BASE_DATA_DIR / "recent_fills_v2.json"
CACHE_FILE = CACHE_DIR / "berlin_services.json"

# Ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
FORMS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
FILLED_FORMS_DIR.mkdir(parents=True, exist_ok=True)

# Constants
BASE_URL = "https://service.berlin.de/export/dienstleistungen/json/"
CACHE_DURATION_SECONDS = 3600

# Performance Profiles
CONFIG = {
    "deflate": IS_REMOTE,       # Compress only for remote to save bandwidth
    "appearance": IS_REMOTE    # Enhanced rendering only for remote (CPU heavy)
}
