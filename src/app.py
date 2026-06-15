"""Flask application factory."""
from flask import Flask
from flask_cors import CORS

from src.routes.printer_routes import printer_bp
from src.routes.system_routes import system_bp


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['CORS_HEADERS'] = 'Content-Type'
    app.register_blueprint(printer_bp)
    app.register_blueprint(system_bp)
    return app
