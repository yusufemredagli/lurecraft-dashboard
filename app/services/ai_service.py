import logging

import requests

from config import Config


logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Yapay zekâ servisiyle ilgili kontrollü hatalar."""
    pass


class AIService:
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "openai/gpt-oss-20b"

    def __init__(self, ayarlar=None):
        self.ayarlar = ayarlar if ayarlar is not None else Config

    def _api_key(self):
        """
        Config içindeki Groq API anahtarını güvenli şekilde alır.
        """
        api_key = getattr(self.ayarlar, "GROQ_API_KEY", "")

        if api_key is None:
            return ""

        return str(api_key).strip()

    def _model(self):
        """
        Config içinde GROQ_MODEL tanımlıysa onu,
        tanımlı değilse varsayılan modeli kullanır.
        """
        model = getattr(
            self.ayarlar,
            "GROQ_MODEL",
            self.DEFAULT_MODEL
        )

        if not model:
            return self.DEFAULT_MODEL

        return str(model).strip()

    def _sistem_talimati(self):
        """
        LureCraft chatbot'un sistem talimatını döndürür.
        """
        context = getattr(
            self.ayarlar,
            "BUSINESS_CONTEXT",
            ""
        )

        if context:
            return str(context).strip()

        return (
            "Sen LureCraft için çalışan yardımcı bir yapay zekâ "
            "asistanısın. Kullanıcılara Türkçe, açık, doğru ve "
            "yardımcı cevaplar ver."
        )

    def _gecmisi_hazirla(self, gecmis):
        """
        Sohbet geçmişini Groq formatına uygun hale getirir.
        Hatalı kayıtları yok sayar.
        """
        temiz_gecmis = []

        if not isinstance(gecmis, list):
            return temiz_gecmis

        for kayit in gecmis:
            if not isinstance(kayit, dict):
                continue

            role = kayit.get("role")
            content = kayit.get("content")

            if role not in {"user", "assistant", "system"}:
                continue

            if not isinstance(content, str):
                continue

            content = content.strip()

            if not content:
                continue

            temiz_gecmis.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return temiz_gecmis

    def yanit_uret(self, mesaj, gecmis=None):
        """
        Kullanıcı mesajını Groq API'ye gönderir
        ve yapay zekâ cevabını döndürür.
        """

        if not isinstance(mesaj, str) or not mesaj.strip():
            raise AIServiceError(
                "Lütfen boş olmayan bir mesaj gönderin."
            )

        api_key = self._api_key()

        if not api_key:
            raise AIServiceError(
                "Groq API anahtarı tanımlanmamış. "
                ".env dosyasındaki GROQ_API_KEY değerini kontrol edin."
            )

        
        if api_key.startswith("AIza"):
            raise AIServiceError(
                "GROQ_API_KEY alanında Google/Gemini API anahtarı "
                "görünüyor. Groq Console üzerinden oluşturulmuş "
                "bir Groq API anahtarı kullanmalısınız."
            )

        messages = [
            {
                "role": "system",
                "content": self._sistem_talimati(),
            }
        ]

        messages.extend(
            self._gecmisi_hazirla(gecmis or [])
        )

        messages.append(
            {
                "role": "user",
                "content": mesaj.strip(),
            }
        )

        return self._groq_yaniti(
            messages=messages,
            api_key=api_key,
        )

    def _groq_yaniti(self, messages, api_key):
        """
        Groq Chat Completions API'ye isteği gönderir.
        """

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": self._model(),
            "messages": messages,
            "temperature": 0.5,
            "max_completion_tokens": 600,
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=(10, 60),
            )
        
        except requests.Timeout as error:
            logger.exception("Groq API zaman aşımı.")

            raise AIServiceError(
                "Yapay zekâ yanıtı zaman aşımına uğradı. "
                "Lütfen tekrar deneyin."
            ) from error

        except requests.ConnectionError as error:
            logger.exception("Groq API bağlantı hatası.")

            raise AIServiceError(
                "Groq sunucusuna bağlanılamadı. "
                "İnternet bağlantısını kontrol edin."
            ) from error

        except requests.RequestException as error:
            logger.exception(
                "Groq API isteği sırasında beklenmeyen hata."
            )

            raise AIServiceError(
                "Yapay zekâ servisine istek gönderilirken "
                "bir bağlantı hatası oluştu."
            ) from error

        # HTTP hata kodlarını ayrı ayrı ele alıyoruz.
        if response.status_code == 401:
            logger.error(
                "Groq API kimlik doğrulama hatası: %s",
                response.text,
            )

            raise AIServiceError(
                "Groq API anahtarı geçersiz veya aktif değil. "
                "GROQ_API_KEY değerini kontrol edin."
            )

        if response.status_code == 403:
            logger.error(
                "Groq API erişim hatası: %s",
                response.text,
            )

            raise AIServiceError(
                "Groq API erişimi reddedildi. "
                "API anahtarınızın yetkilerini kontrol edin."
            )

        if response.status_code == 404:
            logger.error(
                "Groq API/model bulunamadı: %s",
                response.text,
            )

            raise AIServiceError(
                "Kullanılan Groq modeli veya API adresi bulunamadı."
            )

        if response.status_code == 429:
            logger.error(
                "Groq API rate limit: %s",
                response.text,
            )

            raise AIServiceError(
                "Groq kullanım limiti aşıldı. "
                "Lütfen kısa süre sonra tekrar deneyin."
            )

        if 400 <= response.status_code < 500:
            logger.error(
                "Groq istemci hatası [%s]: %s",
                response.status_code,
                response.text,
            )

            raise AIServiceError(
                f"Groq API isteği reddetti. "
                f"HTTP hata kodu: {response.status_code}"
            )

        if response.status_code >= 500:
            logger.error(
                "Groq sunucu hatası [%s]: %s",
                response.status_code,
                response.text,
            )

            raise AIServiceError(
                "Groq servisinde geçici bir sunucu problemi var. "
                "Lütfen tekrar deneyin."
            )

        try:
            data = response.json()

        except ValueError as error:
            logger.error(
                "Groq geçersiz JSON döndürdü: %s",
                response.text,
            )

            raise AIServiceError(
                "Yapay zekâ servisinden geçerli bir yanıt alınamadı."
            ) from error

        try:
            answer = data["choices"][0]["message"]["content"]

        except (KeyError, IndexError, TypeError) as error:
            logger.error(
                "Groq yanıt formatı beklenenden farklı: %s",
                data,
            )

            raise AIServiceError(
                "Yapay zekâ servisinin yanıt formatı geçersiz."
            ) from error

        if not isinstance(answer, str) or not answer.strip():
            logger.error(
                "Groq boş yanıt döndürdü: %s",
                data,
            )

            raise AIServiceError(
                "Yapay zekâ boş bir yanıt döndürdü. "
                "Lütfen tekrar deneyin."
            )

        return answer.strip()


ai_service = AIService()