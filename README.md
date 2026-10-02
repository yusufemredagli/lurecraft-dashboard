# LureCraft Akıllı Satış Asistanı

Yusuf Emre Dağlı - Python ile Ürün Geliştirme

Bu proje SmartLead AI yönergesindeki mimariyle hazırlanmıştır. Ziyaretçi sohbet eder, isim ve telefonuyla iletişim talebi bırakır; yönetim ekranı kayıtları listeler. İşletme bilgileri `BUSINESS_CONTEXT` içinde, marka metinleri HTML ve Wix arayüzlerinde bulunur. Veri ve servis katmanları farklı işletmeler için yeniden kullanılabilir.

## Kurulum

Python 3.9 veya üzeri gerekir. Bu paketin çalışması Python 3.12 ile kontrol edilmiştir. Terminali `smartlead_ai` klasöründe açın.

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

PowerShell etkinleştirmeyi engellerse sanal ortamın Python'unu doğrudan kullanabilirsiniz:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe run.py
```

macOS veya Linux:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Tarayıcı adresleri:

- Karşılama: http://127.0.0.1:5000
- Yönetim: http://127.0.0.1:5000/dashboard
- Sağlık kontrolü: http://127.0.0.1:5000/health

ZIP paketindeki `.env` boş anahtarlarla hazırlanmıştır. GitHub üzerinden indirirseniz `.env.example` dosyasını `.env` adıyla kopyalayın. Gizli dosyalar dosya yöneticinizde görünmeyebilir.

## Yapılandırma

| Ayar | Kullanım |
| --- | --- |
| `APP_ENV` | Yerelde `development`, Render'da `production` |
| `SECRET_KEY` | Gizli ve rastgele değer; boşken süreç için rastgele üretilir |
| `DATABASE_URL` | Varsayılan `sqlite:///leads.db`; SQLite dosyasının yolu |
| `GROQ_API_KEY` | Kendi Groq anahtarınız; boşsa demo modu |
| `AI_PROVIDER` | Yönerge gereği `groq` |
| `BUSINESS_CONTEXT` | `config.py` içindeki LureCraft talimatı; istenirse ortam değişkeniyle değiştirilebilir |
| `CORS_ORIGINS` | Virgülle ayrılan izinli origin adresleri; URL yolu içermez |
| `HOST`, `PORT` | Yerel geliştirme sunucusunun adresi ve portu |

`SECRET_KEY` üretmek için:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Üretilen değeri `.env` içindeki `SECRET_KEY=` alanına yazın. Groq anahtarını da aynı dosyaya ekleyin. Değişikliklerden sonra sunucuyu yeniden başlatın. İşletim sistemi veya Render ortamında tanımlı değerler `.env` değerlerinden önceliklidir.

Groq modeli yönergedeki `llama-3.1-8b-instant` değeridir. Canlı yanıt, hesabınızın API ve model erişimine bağlıdır. API anahtarı yoksa dönen sabit mesaj açıkça demo olduğunu belirtir.

## Dosyaların sorumluluğu

| Dosya | Sorumluluk |
| --- | --- |
| `config.py` | `.env`, `Config`, geliştirme/üretim sınıfları ve seçim sözlüğü |
| `app/database.py` | SQLite bağlantısı, tablo oluşturma, kayıt ekleme ve listeleme; bütün SQL burada |
| `app/services/ai_service.py` | `AIService`, Groq isteği, demo yanıtı ve `AIServiceError` |
| `app/routes.py` | İki Blueprint, istek doğrulama, katman çağrıları ve JSON yanıtları |
| `app/__init__.py` | `create_app()`, CORS, veritabanı başlangıcı, Blueprint kaydı ve `/health` |
| `run.py` | Giriş noktası; `app = create_app()` |
| `app/templates/index.html` | Solda marka/tanıtım, sağda buzlu cam sohbet, altta form: Z-Pattern |
| `app/templates/dashboard.html` | İsim solda olacak biçimde kayıt listesi: F-Pattern |

Kodlarda isteğiniz gereği yorum satırı veya açıklama docstring'i yoktur. SQL ve işletme talimatındaki çok satırlı metinler çalıştırılan/veri olarak kullanılan dizgelerdir.

## API sözleşmesi

| Metot | Yol | Başarılı yanıt |
| --- | --- | --- |
| GET | `/` | Karşılama HTML'i |
| GET | `/dashboard` | Yönetim HTML'i |
| GET | `/health` | `{"basari": true, "durum": "aktif"}` |
| POST | `/api/sohbet` | `{"basari": true, "cevap": "..."}` |
| POST | `/api/leads` | HTTP 201; `basari`, `id`, `mesaj` |
| GET | `/api/leads` | `{"basari": true, "leads": [...]}` |

Sohbet isteği:

```json
{
  "mesaj": "Ürünler nasıl kişiselleştirilir?",
  "gecmis": [
    {"role": "user", "content": "Merhaba"},
    {"role": "assistant", "content": "Merhaba, nasıl yardımcı olabilirim?"}
  ]
}
```

`gecmis` verilmezse boş liste kullanılır. En fazla 20 geçmiş mesaj kabul edilir. İstemci sistem rolü gönderemez. Yeni mesaj geçmişe önceden eklenmez; servis sistem talimatı, geçmiş ve yeni kullanıcı mesajını bu sırayla birleştirir. Geçmiş, yalnızca açık sayfanın belleğinde tutulur; SQLite'a yazılmaz.

İletişim talebi isteği:

```json
{"isim": "Demo Kullanıcı", "telefon": "05000000000", "mesaj": "Özel tasarım hakkında bilgi istiyorum."}
```

İsim ve telefon zorunlu, mesaj isteğe bağlıdır. Telefon 7-15 rakam içerir; başta `+`, boşluk, parantez ve tire kabul edilir. Bunlar biçim kontrolleridir, numaranın gerçekten kullanılabildiğini doğrulamaz.

Hata yanıtı `{"basari": false, "hata": "..."}` biçimindedir. Eksik/geçersiz veri 400, AI hatası 503, veritabanı hatası 500 döner. 64 KiB üzerindeki istekler 413 ile reddedilir. Dış servis hataları `try/except` ile ele alınır; teknik hata ayrıntıları kullanıcıya verilmez. SQL değerleri `?` parametreleriyle aktarılır.

## Yerel kontrol

1. `/health` adresinde `durum: aktif` yanıtını görün.
2. Karşılama ekranından soru sorun. Anahtarsız kurulumda demo yanıtı görünmelidir.
3. Yalnızca örnek isim ve telefonla bir talep kaydedin.
4. `/dashboard` ve `/api/leads` adreslerinde kaydı görün.
5. Eksik `mesaj` içeren `/api/sohbet` isteğinin 400 döndüğünü kontrol edin.

Tarayıcının geliştirici konsolunda örnek API kontrolü:

```javascript
fetch('/api/sohbet', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mesaj: 'LureCraft nedir?', gecmis: []})
}).then(response => response.json()).then(console.log)
```

## GitHub, Render ve Wix

GitHub deposunun kökünde bu `smartlead_ai` klasörünün içeriği bulunmalıdır. `run.py` depo kökünde olur. Paket dışındaki `wix` klasörü, Velo'ya kopyalanacak destek dosyalarıdır.

`.gitignore`, `.env`, sanal ortamları ve SQLite dosyalarını dışlar. `.env.example` paylaşılabilir ve gerçek anahtar içermez. Push işleminden önce `git status` ile `.env` dosyasının izlenmediğini kontrol edin.

Render Build Command:

```bash
pip install -r requirements.txt
```

Render Start Command:

```bash
gunicorn run:app
```

Render ortamına `APP_ENV=production`, `GROQ_API_KEY`, `SECRET_KEY`, `DATABASE_URL` ve `CORS_ORIGINS` ekleyin. Wix'in yayımlanmış origin adresini `CORS_ORIGINS` listesine ekleyin. Örneğin bir Wix adresindeki `/site-adi` bölümünü origin'e koymayın; yalnızca `https://kullanici.wixsite.com` kısmı kullanılır. Özel alan adı varsa onun origin'ini kullanın.

SQLite kayıtlarının Render yeniden başlatmalarında korunması için kalıcı disk gerekir. Disk `/var/data` yoluna bağlandıysa `DATABASE_URL=sqlite:////var/data/leads.db` kullanın. Render'ın varsayılan geçici dosya sistemindeki kayıtlar yeniden başlatma/yayınlama sırasında kaybolabilir. Kalıcı disk için Render'ın güncel plan koşullarını kontrol edin.

Wix sayfalarını `../wix/KURULUM.md` dosyasındaki ID'lerle kurun. Her iki `.js` dosyasındaki `API_URL` değerini gerçek HTTPS Render adresinizle değiştirin.

Bu yönerge MVP'sinde giriş/rol doğrulaması tanımlanmamıştır; `/dashboard` ve `GET /api/leads` kimlik doğrulaması içermez. Bu sürümü örnek verilerle değerlendirin. Gerçek müşteri verileriyle yayına çıkmadan önce yönetim ekranı ve liste API'sine yetkilendirme eklenmelidir; CORS ve Wix sayfasını gizlemek tek başına erişim kontrolü değildir.

## Demo anlatımı

Önce sağlık kontrolünü, sonra sohbeti, ardından örnek talep kaydını ve yönetim listesini gösterin. `routes.py` dosyasının istekleri karşıladığını, SQL'in `database.py` içinde ve Groq çağrısının `ai_service.py` içinde olduğunu açıklayın. Servis kesildiğinde neden 503 döndüğünü ve SQL parametrelerinin neden ayrı gönderildiğini anlatın.

## Başvurulan belgeler

- Kullanıcının sağladığı `SmartLead_AI_Proje_Yonergesi(2).pdf`, modüller A-H.
- Kullanıcının sağladığı `Python Komutları(2).pdf`, fonksiyonlar, sınıflar ve `try/except` bölümleri.
- [Flask kurulumu](https://flask.palletsprojects.com/en/stable/installation/)
- [Groq API uyumluluğu](https://console.groq.com/docs/openai)
- [Wix Fetch](https://dev.wix.com/docs/velo/apis/wix-fetch/introduction)
- [Render kalıcı diskler](https://render.com/docs/disks)

## Gelişmiş dashboard (v2)

Bu sürümde yönetim ekranı yalnızca listeleme yapmaz. Aşağıdaki özellikler eklendi:

- Toplam lead, yeni lead, bugün, son 7 gün ve tamamlanan lead KPI'ları
- İsim / telefon / mesaj / yönetim notunda arama
- Lead durumuna göre filtreleme
- Lead satış durumu yönetimi: `yeni`, `iletisim`, `teklif`, `tamamlandi`, `iptal`
- Her lead için yönetim notu
- Mevcut SQLite veritabanında eksik dashboard kolonlarını otomatik ekleyen migration
- Korumalı yönetim API'si
- Wix Studio için `Permissions.Admin` kullanan backend web module
- Wix Secrets Manager üzerinden API URL ve admin anahtarı kullanımı

### Yeni yönetim API uçları

| Metot | Yol | Açıklama |
| --- | --- | --- |
| GET | `/api/admin/ozet` | KPI değerleri |
| GET | `/api/admin/leads` | Lead listesi, `durum` ve `arama` query parametreleri desteklenir |
| PATCH | `/api/admin/leads/<id>` | Durum ve yönetim notunu günceller |

Bu uçlar `X-Admin-Key` header'ı bekler. Anahtar `ADMIN_API_KEY` ortam değişkeninden alınır.

Doğrudan Flask `/dashboard` ekranı test / yerel yönetim için anahtarı tarayıcıdan ister ve yalnızca `sessionStorage` içinde tutar. Wix'te anahtar frontend'e verilmez; `wix/yonetimBackend.web.js` Secrets Manager üzerinden backend tarafında kullanır.
