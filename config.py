import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()


class Config:
    # 🔐 Seguridad general
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")

    # 🔗 Conexión base de datos (para mysql.connector)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "mecanicosfree")

    # 🔗 SQLAlchemy (solo si lo usas; opcional)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ⚡ Seguridad login
    MAX_INTENTOS = int(os.getenv("MAX_INTENTOS", 3))               # Intentos fallidos permitidos
    TIEMPO_BLOQUEO_MIN = int(os.getenv("TIEMPO_BLOQUEO_MIN", 5))   # Minutos de bloqueo

    # 📂 Subida de imágenes
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # carpeta base del proyecto
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        os.path.join(BASE_DIR, "static", "uploads")
    )
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "jfif", "webp"}

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB

    # 📧 Configuración de correo (si piensas enviar mails)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
