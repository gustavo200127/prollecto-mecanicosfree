from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "usuario"

    numdocumento = db.Column(db.Integer, primary_key=True)
    nombre_usu = db.Column(db.String(100))
    correoElectronico = db.Column(db.String(100), unique=True)
    contrasena = db.Column(db.String(255))  # aquí guardaremos el hash

    def set_password(self, password: str):
        self.contrasena = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)

    def check_password(self, password: str) -> bool:
        if not self.contrasena:
            return False
        return check_password_hash(self.contrasena, password)

    def __repr__(self):
        return f"<Usuario {self.nombre_usu}>"
