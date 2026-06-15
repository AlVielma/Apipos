import os
import sys


def resource_path(relative_path):
    """Get the absolute path to a resource, works for development and for PyInstaller executables."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# AppData directory used to persist the default/selected printer.
# Falls back to the user's home directory on non-Windows platforms.
APPDATA_DIR = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~'), 'Apipos')
PICKLE_FILE = os.path.join(APPDATA_DIR, 'selected_printer.pkl')

TRAY_TOOLTIP = 'Apipos'
TRAY_ICON = resource_path(os.path.join('assets', 'app-icon.png'))

FLASK_PORT = 50432
