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
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join("static", "uploads"))
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16MB por petición
