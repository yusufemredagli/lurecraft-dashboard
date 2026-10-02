import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g


class DatabaseError(Exception):
    pass


DURUMLAR = ("yeni", "iletisim", "teklif", "tamamlandi", "iptal")


def get_db():
    if "db" not in g:
        try:
            address = current_app.config["DATABASE_URL"]
            if address.startswith("sqlite:///"):
                address = address[len("sqlite:///"):]
            if not address or "://" in address or address == ":memory:":
                raise ValueError("Geçerli bir SQLite dosya yolu gerekli.")

            db_path = Path(address).expanduser()
            if not db_path.is_absolute():
                db_path = Path(current_app.root_path).parent / db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)

            connection = sqlite3.connect(str(db_path), timeout=10)
            connection.row_factory = sqlite3.Row
            g.db = connection
        except (sqlite3.Error, OSError, ValueError) as error:
            raise DatabaseError(
                "Veritabanı bağlantısı kurulamadı."
            ) from error
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        try:
            connection.close()
        except sqlite3.Error:
            current_app.logger.warning(
                "Veritabanı bağlantısı kapatılamadı."
            )


def _kolonlari_hazirla(connection):
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(leads)").fetchall()
    }
    additions = {
        "durum": "TEXT NOT NULL DEFAULT 'yeni'",
        "notlar": "TEXT NOT NULL DEFAULT ''",
        "kaynak": "TEXT NOT NULL DEFAULT 'web'",
        "guncelleme_tarihi": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(
                f"ALTER TABLE leads ADD COLUMN {name} {definition}"
            )
    connection.execute(
        "UPDATE leads SET guncelleme_tarihi = tarih "
        "WHERE guncelleme_tarihi = '' OR guncelleme_tarihi IS NULL"
    )


def init_db(app):
    app.teardown_appcontext(close_db)
    connection = get_db()
    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isim TEXT NOT NULL,
                    telefon TEXT NOT NULL,
                    mesaj TEXT DEFAULT '',
                    tarih TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    durum TEXT NOT NULL DEFAULT 'yeni',
                    notlar TEXT NOT NULL DEFAULT '',
                    kaynak TEXT NOT NULL DEFAULT 'web',
                    guncelleme_tarihi TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            _kolonlari_hazirla(connection)
    except sqlite3.Error as error:
        raise DatabaseError("Veritabanı hazırlanamadı.") from error


def lead_ekle(isim, telefon, mesaj="", kaynak="wix"):
    connection = get_db()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO leads (isim, telefon, mesaj, kaynak) "
                "VALUES (?, ?, ?, ?)",
                (isim, telefon, mesaj, kaynak),
            )
        return cursor.lastrowid
    except sqlite3.Error as error:
        raise DatabaseError("İletişim kaydı oluşturulamadı.") from error


def tum_leadler(durum="", arama="", limit=200):
    try:
        query = (
            "SELECT id, isim, telefon, mesaj, tarih, durum, notlar, "
            "kaynak, guncelleme_tarihi FROM leads WHERE 1=1"
        )
        params = []
        if durum:
            query += " AND durum = ?"
            params.append(durum)
        if arama:
            needle = f"%{arama}%"
            query += (
                " AND (isim LIKE ? OR telefon LIKE ? OR mesaj LIKE ? "
                "OR notlar LIKE ?)"
            )
            params.extend([needle, needle, needle, needle])
        query += " ORDER BY tarih DESC, id DESC LIMIT ?"
        params.append(limit)
        rows = get_db().execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as error:
        raise DatabaseError("İletişim kayıtları alınamadı.") from error


def lead_guncelle(lead_id, durum=None, notlar=None):
    updates = []
    params = []
    if durum is not None:
        updates.append("durum = ?")
        params.append(durum)
    if notlar is not None:
        updates.append("notlar = ?")
        params.append(notlar)
    if not updates:
        return None
    updates.append("guncelleme_tarihi = ?")
    params.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    params.append(lead_id)
    try:
        connection = get_db()
        with connection:
            cursor = connection.execute(
                f"UPDATE leads SET {', '.join(updates)} WHERE id = ?",
                params,
            )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, isim, telefon, mesaj, tarih, durum, notlar, "
            "kaynak, guncelleme_tarihi FROM leads WHERE id = ?",
            (lead_id,),
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as error:
        raise DatabaseError("İletişim kaydı güncellenemedi.") from error


def dashboard_ozeti():
    try:
        row = get_db().execute(
            """
            SELECT
                COUNT(*) AS toplam,
                SUM(CASE WHEN durum = 'yeni' THEN 1 ELSE 0 END) AS yeni,
                SUM(CASE WHEN durum = 'tamamlandi' THEN 1 ELSE 0 END) AS tamamlandi,
                SUM(CASE WHEN date(tarih) = date('now') THEN 1 ELSE 0 END) AS bugun,
                SUM(CASE WHEN datetime(tarih) >= datetime('now', '-7 day') THEN 1 ELSE 0 END) AS son7gun
            FROM leads
            """
        ).fetchone()
        result = dict(row)
        return {key: int(value or 0) for key, value in result.items()}
    except sqlite3.Error as error:
        raise DatabaseError("Dashboard özeti alınamadı.") from error
