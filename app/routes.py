import hmac
import re
from functools import wraps

from flask import Blueprint, current_app, jsonify, render_template, request

from .database import (
    DURUMLAR,
    DatabaseError,
    dashboard_ozeti,
    lead_ekle,
    lead_guncelle,
    tum_leadler,
)
from .services.ai_service import AIServiceError, ai_service


pages_bp = Blueprint("pages", __name__)
api_bp = Blueprint("api", __name__)


def _json_oku():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Geçerli bir JSON nesnesi gönderin.")
    return data


def _metin_oku(data, field, limit, required=True):
    value = data.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} alanı metin olmalıdır.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} alanı zorunludur.")
    if len(value) > limit:
        raise ValueError(
            f"{field} alanı en fazla {limit} karakter olabilir."
        )
    return value


def _gecmis_oku(data):
    history = data.get("gecmis", [])
    if not isinstance(history, list) or len(history) > 20:
        raise ValueError("gecmis alanı en fazla 20 mesajlık liste olmalıdır.")

    cleaned = []
    for item in history:
        if not isinstance(item, dict):
            raise ValueError("Sohbet geçmişinin biçimi geçersiz.")
        role = item.get("role")
        if role not in ("user", "assistant"):
            raise ValueError("Geçmişte yalnızca user ve assistant olabilir.")
        content = _metin_oku(item, "content", 4000)
        cleaned.append({"role": role, "content": content})
    return cleaned


def _hata(message, status):
    return jsonify(basari=False, hata=message), status


def _admin_gerekli(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get("ADMIN_API_KEY", "").strip()
        provided = request.headers.get("X-Admin-Key", "").strip()
        if not expected:
            return _hata("Yönetim API anahtarı yapılandırılmamış.", 503)
        if not provided or not hmac.compare_digest(provided, expected):
            return _hata("Bu işlem için yetkiniz yok.", 401)
        return func(*args, **kwargs)

    return wrapped


@pages_bp.get("/")
def index():
    return render_template("index.html")


@pages_bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@api_bp.post("/sohbet")
def sohbet():
    try:
        data = _json_oku()
        mesaj = _metin_oku(data, "mesaj", 2000)
        gecmis = _gecmis_oku(data)
        cevap = ai_service.yanit_uret(mesaj, gecmis)
    except ValueError as error:
        return _hata(str(error), 400)
    except AIServiceError as error:
        return _hata(str(error), 503)
    return jsonify(basari=True, cevap=cevap)


@api_bp.post("/leads")
def lead_kaydet():
    try:
        data = _json_oku()
        isim = _metin_oku(data, "isim", 100)
        telefon = _metin_oku(data, "telefon", 25)
        mesaj = _metin_oku(data, "mesaj", 2000, required=False)
        kaynak = _metin_oku(data, "kaynak", 40, required=False) or "wix"
        digits = re.sub(r"\D", "", telefon)
        if (
            not re.fullmatch(r"\+?[0-9 ()-]+", telefon)
            or not 7 <= len(digits) <= 15
        ):
            raise ValueError("Geçerli bir telefon numarası yazın.")
        lead_id = lead_ekle(isim, telefon, mesaj, kaynak)
    except ValueError as error:
        return _hata(str(error), 400)
    except DatabaseError:
        return _hata("Talebiniz kaydedilemedi. Lütfen tekrar deneyin.", 500)
    return jsonify(
        basari=True,
        id=lead_id,
        mesaj="İletişim talebiniz kaydedildi.",
    ), 201


@api_bp.get("/admin/ozet")
@_admin_gerekli
def admin_ozet():
    try:
        ozet = dashboard_ozeti()
    except DatabaseError:
        return _hata("Dashboard özeti alınamadı.", 500)
    return jsonify(basari=True, ozet=ozet)


@api_bp.get("/admin/leads")
@_admin_gerekli
def admin_leadleri_listele():
    durum = request.args.get("durum", "").strip().lower()
    arama = request.args.get("arama", "").strip()
    if durum and durum not in DURUMLAR:
        return _hata("Geçersiz durum filtresi.", 400)
    if len(arama) > 100:
        return _hata("Arama ifadesi en fazla 100 karakter olabilir.", 400)
    try:
        leads = tum_leadler(durum=durum, arama=arama)
    except DatabaseError:
        return _hata("Kayıtlar alınamadı. Lütfen tekrar deneyin.", 500)
    return jsonify(basari=True, leads=leads)


@api_bp.patch("/admin/leads/<int:lead_id>")
@_admin_gerekli
def admin_lead_guncelle(lead_id):
    try:
        data = _json_oku()
        durum = None
        notlar = None
        if "durum" in data:
            durum = _metin_oku(data, "durum", 20).lower()
            if durum not in DURUMLAR:
                raise ValueError("Geçersiz lead durumu.")
        if "notlar" in data:
            notlar = _metin_oku(data, "notlar", 2000, required=False)
        if durum is None and notlar is None:
            raise ValueError("Güncellenecek alan gönderilmedi.")
        lead = lead_guncelle(lead_id, durum=durum, notlar=notlar)
        if lead is None:
            return _hata("İletişim kaydı bulunamadı.", 404)
    except ValueError as error:
        return _hata(str(error), 400)
    except DatabaseError:
        return _hata("Kayıt güncellenemedi.", 500)
    return jsonify(basari=True, lead=lead)
