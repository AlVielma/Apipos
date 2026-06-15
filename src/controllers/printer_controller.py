"""Controllers: a single try/catch per action, call the service, send the response.

No business logic lives here. Services return the standardized response shape;
controllers only map it to an HTTP status code and serialize it.
"""
from flask import jsonify, request

from src.services import printer_service
from src.utils.response import error_response


def _respond(result):
    """Serialize a service result, deriving the HTTP status from its 'status' field."""
    code = 200 if result.get("status") == "success" else 400
    return jsonify(result), code


def list_printers_controller():
    try:
        result = printer_service.get_printers()
        return _respond(result)
    except Exception as e:
        return jsonify(error_response(str(e))), 500


def get_selected_printer_controller():
    try:
        result = printer_service.get_selected_printer()
        return _respond(result)
    except Exception as e:
        return jsonify(error_response(str(e))), 500


def set_selected_printer_controller():
    try:
        result = printer_service.set_selected_printer(request.get_json(silent=True))
        return _respond(result)
    except Exception as e:
        return jsonify(error_response(str(e))), 500


def print_controller():
    try:
        result = printer_service.print_job(request.get_json(silent=True))
        return _respond(result)
    except Exception as e:
        return jsonify(error_response(str(e))), 500


def open_withdrawer_controller():
    try:
        result = printer_service.open_drawer(request.get_json(silent=True))
        return _respond(result)
    except Exception as e:
        return jsonify(error_response(str(e))), 500


def print_test_controller():
    try:
        printer = request.args.get('printer')
        result = printer_service.print_test(printer)
        return _respond(result)
    except Exception as e:
        return jsonify(error_response(str(e))), 500
