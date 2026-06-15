"""Persistence of the default/selected printer in the AppData folder."""
import os
import pickle

from src.config import APPDATA_DIR, PICKLE_FILE


def ensure_appdata_directory():
    """Ensure the AppData directory exists."""
    if not os.path.exists(APPDATA_DIR):
        os.makedirs(APPDATA_DIR)


def save_selected_printer(printer_name):
    """Save the selected printer to a pickle file in the AppData folder."""
    ensure_appdata_directory()
    with open(PICKLE_FILE, 'wb') as f:
        pickle.dump(printer_name, f)


def load_selected_printer():
    """Load the selected printer from the pickle file, if it exists and is valid."""
    if os.path.exists(PICKLE_FILE):
        try:
            with open(PICKLE_FILE, 'rb') as f:
                return pickle.load(f)
        except (EOFError, pickle.UnpicklingError):
            print("Pickle file is empty or corrupted. Returning None.")
            return None
    return None
