from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import mysql.connector

routes = Blueprint("routes", __name__)

# --------------------------
# Conexión a la BD
# --------------------------
def conectar_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="mecanicosfree"
    )

# --------------------------
# INICIO
# --------------------------
@routes.route("/")
def inicio():
    return render_template("index.html")

# --------------------------
# CATÁLOGO
# --------------------------
@routes.route("/catalogo")
def catalogo():
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # Productos con nombre del taller
    cursor.execute("""
        SELECT p.*, u.nombre_usu AS taller
        FROM producto p
        JOIN usuario u ON p.id_usutaller = u.numdocumento
    """)
    productos = cursor.fetchall()

    # Servicios con nombre del taller
    cursor.execute("""
        SELECT s.*, u.nombre_usu AS taller
        FROM servicio s
        JOIN usuario u ON s.id_usutaller = u.numdocumento
    """)
    servicios = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("catalogo.html", productos=productos, servicios=servicios)


# --------------------------
# LOGIN USUARIO (cliente / taller)
# --------------------------
@routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correoElectronico")
        contrasena = request.form.get("contrasena")

        conn = conectar_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.numdocumento, u.nombre_usu, u.correoElectronico, r.tipoRol
            FROM usuario u
            JOIN rol r ON u.numdocumento = r.numdocumento
            WHERE u.correoElectronico=%s AND u.contrasena=%s
        """, (correo, contrasena))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session["usuario"] = {
                "numdocumento": usuario["numdocumento"],
                "nombre_usu": usuario["nombre_usu"],
                "correoElectronico": usuario["correoElectronico"],
                "rol": usuario["tipoRol"]
            }
            flash("Inicio de sesión exitoso ✅", "success")

            if usuario["tipoRol"] == "taller":
                return redirect(url_for("routes.perfil_taller"))
            else:
                return redirect(url_for("routes.perfil_cliente"))
        else:
            flash("Correo o contraseña incorrectos ❌", "danger")

    return render_template("login.html")

# --------------------------
# PERFIL CLIENTE
# --------------------------
@routes.route("/perfil_cliente")
def perfil_cliente():
    if "usuario" not in session or session["usuario"]["rol"] != "cliente":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))
    return render_template("perfil_cliente.html", usuario=session["usuario"])

# --------------------------
# PERFIL TALLER
# --------------------------
@routes.route("/perfil_taller")
def perfil_taller():
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))
    return render_template("perfil_taller.html", usuario=session["usuario"])

# --------------------------
# LOGOUT USUARIO
# --------------------------
@routes.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Sesión de usuario cerrada ✅", "info")
    return redirect(url_for("routes.login"))

# --------------------------
# LISTA DE USUARIOS (ADMIN)
# --------------------------
@routes.route("/usuarios")
def usuarios():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    page = request.args.get("page", 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM usuario")
    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT u.numdocumento, u.nombre_usu, u.correoElectronico, r.tipoRol
        FROM usuario u
        LEFT JOIN rol r ON u.numdocumento = r.numdocumento
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    usuarios = cursor.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        page=page,
        total_pages=total_pages
    )

# --------------------------
# REGISTRAR USUARIO (PÚBLICO)
# --------------------------
@routes.route("/usuarios/registrar", methods=["GET", "POST"])
def registrar_usuario():
    if request.method == "POST":
        numdocumento = request.form["numdocumento"]
        nombre_usu = request.form["nombre_usu"]
        correoElectronico = request.form["correoElectronico"]
        contrasena = request.form["contrasena"]

        conn = conectar_db()
        cursor = conn.cursor(dictionary=True)

        # Verificar si ya existe documento o correo
        cursor.execute(
            "SELECT * FROM usuario WHERE numdocumento=%s OR correoElectronico=%s",
            (numdocumento, correoElectronico)
        )
        existente = cursor.fetchone()

        if existente:
            flash("El documento o correo ya está registrado ❌", "danger")
            conn.close()
            return redirect(url_for("routes.registrar_usuario"))

        # Insertar usuario
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuario (numdocumento, nombre_usu, correoElectronico, contrasena) VALUES (%s, %s, %s, %s)",
            (numdocumento, nombre_usu, correoElectronico, contrasena)
        )
        conn.commit()

        # Asignar rol automáticamente
        rol = request.form.get("rol", "cliente")
        if rol == "taller":
            rol = "pendiente_taller"  # Para que un admin luego lo apruebe
        else:
            rol = "cliente"

        cursor.execute(
            "INSERT INTO rol (numdocumento, tipoRol) VALUES (%s, %s)",
            (numdocumento, rol)
        )
        conn.commit()
        conn.close()

        flash("Usuario registrado con éxito ✅", "success")
        return redirect(url_for("routes.login"))  # Enviar al login después del registro

    return render_template("registrar_usuario.html")

# --------------------------
# LOGIN ADMIN
# --------------------------
@routes.route("/admin/login", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        correo = request.form.get("correoElectronico")
        contrasena = request.form.get("contrasena")

        conn = conectar_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.numdocumento, u.nombre_usu, u.correoElectronico
            FROM usuario u
            JOIN rol r ON u.numdocumento = r.numdocumento
            WHERE u.correoElectronico=%s AND u.contrasena=%s AND r.tipoRol='admin'
        """, (correo, contrasena))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session["admin"] = {
                "numdocumento": admin["numdocumento"],
                "nombre_usu": admin["nombre_usu"],
                "correoElectronico": admin["correoElectronico"]
            }
            flash("Inicio de sesión como administrador ✅", "success")
            return redirect(url_for("routes.admin_dashboard"))
        else:
            flash("Credenciales inválidas o no eres administrador ❌", "danger")

    return render_template("admin_login.html")

# --------------------------
# PANEL ADMIN
# --------------------------
@routes.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id_rol, r.numdocumento, u.nombre_usu, u.correoElectronico
        FROM rol r
        JOIN usuario u ON r.numdocumento = u.numdocumento
        WHERE r.tipoRol = 'pendiente_taller'
    """)
    solicitudes = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", solicitudes=solicitudes)

# --------------------------
# LOGOUT ADMIN
# --------------------------
@routes.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Sesión de administrador cerrada ✅", "info")
    return redirect(url_for("routes.login_admin"))

# --------------------------
# APROBAR / RECHAZAR TALLER
# --------------------------
@routes.route("/admin/taller/aprobar/<numdocumento>")
def aprobar_taller(numdocumento):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE rol SET tipoRol = 'taller' WHERE numdocumento = %s", (numdocumento,))
    conn.commit()
    conn.close()

    flash("Taller aprobado ✅", "success")
    return redirect(url_for("routes.admin_dashboard"))

@routes.route("/admin/taller/rechazar/<numdocumento>")
def rechazar_taller(numdocumento):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE rol SET tipoRol = 'cliente' WHERE numdocumento = %s", (numdocumento,))
    conn.commit()
    conn.close()

    flash("Taller rechazado ❌", "info")
    return redirect(url_for("routes.admin_dashboard"))

# --------------------------
# EDITAR USUARIO (ADMIN)
# --------------------------
@routes.route("/usuarios/editar/<numdocumento>", methods=["GET", "POST"])
def editar_usuario(numdocumento):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE numdocumento = %s", (numdocumento,))
    usuario = cursor.fetchone()

    if not usuario:
        flash("Usuario no encontrado ❌", "danger")
        conn.close()
        return redirect(url_for("routes.usuarios"))

    if request.method == "POST":
        nombre_usu = request.form["nombre_usu"]
        correoElectronico = request.form["correoElectronico"]
        contrasena = request.form.get("contrasena")
        contrasena2 = request.form.get("contrasena2")

        if contrasena or contrasena2:
            if contrasena != contrasena2:
                flash("Las contraseñas no coinciden ❌", "danger")
                return redirect(url_for("routes.editar_usuario", numdocumento=numdocumento))
            cursor.execute(
                "UPDATE usuario SET nombre_usu=%s, correoElectronico=%s, contrasena=%s WHERE numdocumento=%s",
                (nombre_usu, correoElectronico, contrasena, numdocumento)
            )
        else:
            cursor.execute(
                "UPDATE usuario SET nombre_usu=%s, correoElectronico=%s WHERE numdocumento=%s",
                (nombre_usu, correoElectronico, numdocumento)
            )

        conn.commit()
        conn.close()
        flash("Usuario actualizado ✅", "success")
        return redirect(url_for("routes.usuarios"))

    conn.close()
    return render_template("editar_usuario.html", usuario=usuario)

# --------------------------
# ELIMINAR USUARIO (ADMIN)
# --------------------------
@routes.route("/usuarios/eliminar/<numdocumento>", methods=["GET", "POST"])
def eliminar_usuario(numdocumento):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rol WHERE numdocumento = %s", (numdocumento,))
    cursor.execute("DELETE FROM usuario WHERE numdocumento = %s", (numdocumento,))
    conn.commit()
    conn.close()

    flash("Usuario eliminado ✅", "success")
    return redirect(url_for("routes.usuarios"))

# --------------------------
# ADMIN - PRODUCTOS
# --------------------------
@routes.route("/admin/productos")
def admin_productos():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    return render_template("admin_productos.html")

# --------------------------
# ADMIN - SERVICIOS
# --------------------------
@routes.route("/admin/servicios")
def admin_servicios():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    return render_template("admin_servicios.html")

# --------------------------
# AGREGAR SERVICIO (TALLER)
# --------------------------
@routes.route("/agregar_servicio", methods=["GET", "POST"])
def agregar_servicio():
    if "usuario" not in session or session["usuario"].get("rol") != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        tipo_servicio = request.form["tipo_servicio"]
        precio = request.form["precio"]
        disponibilidad = request.form["disponibilidad"]

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO servicio (tipo_servicio, precio, disponibilidad, id_usutaller)
            VALUES (%s, %s, %s, %s)
        """, (tipo_servicio, precio, disponibilidad, session["usuario"]["numdocumento"]))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Servicio agregado correctamente ✅", "success")
        return redirect(url_for("routes.perfil_taller"))

    return render_template("agregar_servicio.html")


# --------------------------
# AGREGAR PRODUCTO (TALLER)
# --------------------------
@routes.route("/productos/agregar", methods=["GET", "POST"])
def agregar_producto():
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        tipo_producto = request.form.get("tipo_producto")
        marca_producto = request.form.get("marca_producto")
        precio_producto = request.form.get("precio_producto")
        stock_producto = request.form.get("stock_producto")

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO producto (id_usutaller, tipo_producto, marca_producto, precio_producto, stock_producto, publicado)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            session["usuario"]["numdocumento"],  # el taller dueño del producto
            tipo_producto,
            marca_producto,
            precio_producto,
            stock_producto,
            "publicado"  # por defecto, lo dejamos publicado
        ))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Producto agregado con éxito ✅", "success")
        return redirect(url_for("routes.perfil_taller"))

    return render_template("agregar_producto.html")

