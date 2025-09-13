from .extensions import db

class Rol(db.Model):
    __tablename__ = "rol"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

    usuarios = db.relationship("Usuario", backref="rol", lazy=True)


class Usuario(db.Model):
    __tablename__ = "usuario"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)

    rol_id = db.Column(db.Integer, db.ForeignKey("rol.id"), nullable=False)
