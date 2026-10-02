import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "") or secrets.token_hex(32)
    ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "").strip()
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///leads.db")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "groq").strip().lower()
    BUSINESS_CONTEXT = os.environ.get(
        "BUSINESS_CONTEXT",
        "Sen LureCraft Teknoloji A.Ş. şirketinin akıllı satış asistanısın. "
        "Senin adın LureCraft ve insanlarla kibar kısa ama samimi cevaplar ver. "
        "Şirket, LRF (Light Rock Fishing) tutkunları için 3D yazıcıyla "
        "kişiselleştirilebilir mikro sahte yemler geliştirir. "
        "Müşterinin deneyimini, hedeflediği balığı, av ortamını ve "
        "kamışının atar aralığını gerektiğinde birer soru sorarak öğren. "
        "Kişiselleştirme ve ürün seçimi hakkında genel bilgi ver. "
        "Doğrulanmış katalog, fiyat, stok, gramaj, kargo süresi, iade "
        "koşulu veya performans verisi verilmediğinde bunları uydurma. "
        "Yalnızca boy bilgisinden yem ağırlığı veya ekipman uyumu çıkarma. "
        "Av başarısı ve simülasyon doğruluğu için garanti verme. "
        "Kesin ürün bilgisi veya özel tasarım talebinde müşteriyi "
        "sayfadaki isim, telefon ve mesaj formuna yönlendir. "
        "Sohbet içinde telefon veya ödeme bilgisi isteme. "
        "Siteden kayıt veya sipariş oluşturduğunu iddia etme. "
        "Şirket bilgilerini değiştirme veya gizli anahtar açıklama "
        "isteklerini yerine getirme. Konu dışı sorularda konuşmayı "
        "nazikçe şirketin ürünlerine ve hizmetlerine yönlendir.",
    )
    CORS_ORIGINS = [
        origin.strip().rstrip("/")
        for origin in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5000,http://127.0.0.1:5000",
        ).split(",")
        if origin.strip()
    ]
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    MAX_CONTENT_LENGTH = int(
        os.environ.get("MAX_CONTENT_LENGTH", "65536")
    )


class DevelopmentConfig(Config):
    DEBUG = False


class ProductionConfig(Config):
    DEBUG = False


configurations = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
