"""System / diagnostics business logic."""
import platform
import sys

from src.config import FLASK_PORT, APP_VERSION
from src.printers import get_backend
from src.utils.response import success_response


def get_health():
    """Report the OS and the active printer backend (useful per installer)."""
    backend = get_backend()
    data = {
        "status": "ok",
        "version": APP_VERSION,
        "os": platform.system(),            # 'Windows' | 'Darwin' | 'Linux'
        "platform": sys.platform,           # 'win32' | 'darwin' | ...
        "backend": type(backend).__name__,  # WindowsPrinterBackend | MacPrinterBackend
        "port": FLASK_PORT,
    }
    return success_response(data=data, message="Service is running.")
