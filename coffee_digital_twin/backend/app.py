from flask import Flask, jsonify
from flask_cors import CORS

from api.advice_api import advice_bp
from api.farmop_api import farmop_bp
from api.model_api import model_bp
from api.plot_api import plot_bp
from api.result_api import result_bp
from config import DEBUG, HOST, PORT, ensure_dirs
from database.init_db import init_db


def create_app():
    ensure_dirs()
    init_db()

    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(plot_bp)
    app.register_blueprint(farmop_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(result_bp)
    app.register_blueprint(advice_bp)

    @app.get("/api/ping")
    def ping():
        return jsonify({"status": "ok", "message": "coffee digital twin backend is running"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"status": "error", "message": "API not found"}), 404

    @app.errorhandler(Exception)
    def server_error(error):
        return jsonify({"status": "error", "message": str(error)}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
