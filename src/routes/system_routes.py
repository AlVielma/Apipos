"""System / diagnostics routes."""
from flask import Blueprint
from flask_cors import cross_origin

from src.controllers import system_controller

system_bp = Blueprint('system', __name__)


@system_bp.route('/health', methods=['GET'])
@cross_origin()
def health():
    return system_controller.health_controller()
