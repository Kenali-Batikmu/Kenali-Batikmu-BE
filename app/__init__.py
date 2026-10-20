import logging
from pathlib import Path

from flask import Flask, jsonify, request

from .config import Config
from .db import close_db, connect, init_db, seed_db
from .services.ml import load_classifier
from .errors import register_error_handlers
from .seed import seed_demo_users


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(level=logging.INFO)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db(app.config["DATABASE"])
        if app.config["AUTO_SEED"]:
            seed_db(app.config["DATABASE"])
        if app.config["SEED_DEMO_USERS"]:
            conn = connect(app.config["DATABASE"])
            try:
                seed_demo_users(conn)
            finally:
                conn.close()
        load_classifier()

    app.teardown_appcontext(close_db)
    register_error_handlers(app)

    from .routes import auth, modules, motifs, profile, scans

    for module in (auth, motifs, modules, scans, profile):
        app.register_blueprint(module.bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.before_request
    def _cors_preflight():
        if request.method == "OPTIONS":
            resp = app.make_default_options_response()
            origin = request.headers.get("Origin", "*")
            allowed = app.config["CORS_ORIGINS"]
            if not allowed or origin in allowed:
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                resp.headers["Access-Control-Max-Age"] = "86400"
            return resp

    @app.after_request
    def _cors(resp):
        origin = request.headers.get("Origin")
        allowed = app.config["CORS_ORIGINS"]
        # Jika CORS_ORIGINS kosong (dev), izinkan semua origin; jika diisi, hanya whitelist
        if origin and (not allowed or origin in allowed):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        elif not origin:
            # Request tanpa Origin (e.g. mobile native) — izinkan
            resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    return app
