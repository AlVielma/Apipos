"""Generic, standardized service responses.

Every service returns a dict with this exact shape so controllers can stay thin:

    {
        "status": "success" | "error",
        "data": T | None,
        "message": "specific message"
    }
"""


def success_response(data=None, message=""):
    return {"status": "success", "data": data, "message": message}


def error_response(message, data=None):
    return {"status": "error", "data": data, "message": message}
