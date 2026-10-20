import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, **extra):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra


def _response(status: int, code: str, message: str, **extra):
    body = {"error": {"code": code, "message": message, **extra}}
    return jsonify(body), status


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        return _response(e.status, e.code, e.message, **e.extra)

    @app.errorhandler(413)
    def _too_large(_e):
        mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return _response(413, "file_too_large", f"Ukuran file melebihi batas {mb} MB.")

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        return _response(e.code or 500, (e.name or "error").lower().replace(" ", "_"), e.description or e.name)

    @app.errorhandler(Exception)
    def _unhandled(e: Exception):
        log.exception("Unhandled error")
        return _response(500, "internal_error", "Terjadi kesalahan pada server.")
