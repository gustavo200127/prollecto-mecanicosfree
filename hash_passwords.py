# hash_passwords.py
from app import app
from models import db, Usuario
from werkzeug.security import generate_password_hash

def is_hashed(pw: str) -> bool:
    if not pw:
        return False
    return pw.startswith("pbkdf2:")  # detecta hashes generados por werkzeug

with app.app_context():
    usuarios = Usuario.query.all()
    updated = 0
    for u in usuarios:
        pw = u.contrasena or ""
        if not is_hashed(pw):
            # transforma el password plano en hash
            u.contrasena = generate_password_hash(pw, method="pbkdf2:sha256", salt_length=8)
            updated += 1
    if updated:
        db.session.commit()
    print(f"Usuarios actualizados (hasheados): {updated}")
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["contrasena"]
        user = Usuario.query.filter_by(correoElectronico=correo).first()
        if user and user.check_password(password):
            flash("Login correcto", "success")
            # setear sesión, etc.
            return redirect(url_for("lista_usuarios"))
        flash("Credenciales inválidas", "danger")
    return render_template("login.html")
