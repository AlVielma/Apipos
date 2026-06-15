"""System controller: thin try/catch wrapper over the system service."""
from flask import jsonify

from src.services import system_service
from src.utils.response import error_response


def health_controller():
    try:
        result = system_service.get_health()
        code = 200 if result.get("status") == "success" else 400
        return jsonify(result), code
    except Exception as e:
        return jsonify(error_response(str(e))), 500
