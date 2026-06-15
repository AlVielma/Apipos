"""Entry point: starts the Flask API in a background thread and the tray icon.

The application logic is organized in layers under ./src:
  - routes/       -> endpoint definitions
  - controllers/  -> thin try/catch wrappers that call the services
  - services/     -> business logic + standardized responses
  - utils/        -> shared helpers (response shape)

Set APIPOS_NO_TRAY=1 to run the API in the foreground without the tray icon
(useful for testing, e.g. on a headless machine or while debugging).
"""
import os
import threading

from src.app import create_app
from src.config import FLASK_PORT


def run_flask_app():
    app = create_app()
    app.run(host='127.0.0.1', port=FLASK_PORT, use_reloader=False)


def main():
    # Headless mode: run the API in the foreground (blocks here, stays alive).
    if os.getenv('APIPOS_NO_TRAY') == '1':
        print(f"Apipos running (headless) on http://127.0.0.1:{FLASK_PORT}")
        run_flask_app()
        return

    # Start the Flask app in a daemon thread so it stops when the tray exits.
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Start the wxPython tray icon on the main thread (keeps the process alive).
    from src.tray import start_tray
    start_tray()


if __name__ == "__main__":
    main()
