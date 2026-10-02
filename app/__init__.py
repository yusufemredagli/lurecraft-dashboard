import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import configurations
from .database import init_db
from .routes import api_bp, pages_bp


def create_app(config_name=None):
    selected = config_name or os.environ.get("APP_ENV", "development")
    if selected not in configurations:
        raise ValueError("APP_ENV development veya production olmalıdır.")

    app = Flask(__name__)
    app.config.from_object(configurations[selected])
    app.json.ensure_ascii = False

    CORS(
        app,
        resources={r"/api/.*": {"origins": app.config["CORS_ORIGINS"]}},
        methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Key"],
    )

    with app.app_context():
        init_db(app)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify(basari=True, durum="aktif")

    @app.errorhandler(HTTPException)
    def http_hatasi(error):
        messages = {
            400: "İstek biçimi geçersiz.",
            401: "Bu işlem için yetkiniz yok.",
            404: "İstenen adres bulunamadı.",
            405: "Bu adres için kullanılan yöntem desteklenmiyor.",
            413: "Gönderilen veri izin verilen boyutu aşıyor.",
            415: "İçerik türü application/json olmalıdır.",
        }
        message = messages.get(error.code, "İstek tamamlanamadı.")
        return jsonify(basari=False, hata=message), error.code

    @app.errorhandler(500)
    def sunucu_hatasi(error):
        return jsonify(
            basari=False,
            hata="İşlem tamamlanamadı. Lütfen tekrar deneyin.",
        ), 500

    return app
