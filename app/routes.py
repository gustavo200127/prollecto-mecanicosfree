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

    cursor.execute("""
        SELECT p.*, u.nombre_usu AS taller
        FROM producto p
        JOIN usuario u ON p.id_usutaller = u.numdocumento
    """)
    productos = cursor.fetchall()

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

        cursor.execute(
            "SELECT * FROM usuario WHERE numdocumento=%s OR correoElectronico=%s",
            (numdocumento, correoElectronico)
        )
        existente = cursor.fetchone()

        if existente:
            flash("El documento o correo ya está registrado ❌", "danger")
            conn.close()
            return redirect(url_for("routes.registrar_usuario"))

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuario (numdocumento, nombre_usu, correoElectronico, contrasena) VALUES (%s, %s, %s, %s)",
            (numdocumento, nombre_usu, correoElectronico, contrasena)
        )
        conn.commit()

        rol = request.form.get("rol", "cliente")
        if rol == "taller":
            rol = "pendiente_taller"   # 👈 ahora queda en revisión
        else:
            rol = "cliente"

        cursor.execute(
            "INSERT INTO rol (numdocumento, tipoRol) VALUES (%s, %s)",
            (numdocumento, rol)
        )
        conn.commit()
        conn.close()

        flash("Usuario registrado con éxito ✅", "success")
        return redirect(url_for("routes.login"))

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

@routes.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # Total de usuarios
    cursor.execute("SELECT COUNT(*) AS total FROM usuario")
    total_usuarios = cursor.fetchone()["total"]

    # Total de talleres (rol = 'taller')
    cursor.execute("SELECT COUNT(*) AS total FROM rol WHERE tipoRol = 'taller'")
    total_talleres = cursor.fetchone()["total"]

    # Total de productos
    cursor.execute("SELECT COUNT(*) AS total FROM producto")
    total_productos = cursor.fetchone()["total"]

    # Total de servicios
    cursor.execute("SELECT COUNT(*) AS total FROM servicio")
    total_servicios = cursor.fetchone()["total"]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_usuarios=total_usuarios,
        total_talleres=total_talleres,
        total_productos=total_productos,
        total_servicios=total_servicios
    )

# --------------------------
# LOGOUT ADMIN
# --------------------------
@routes.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Sesión de administrador cerrada ✅", "info")
    return redirect(url_for("routes.login_admin"))

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

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, u.nombre_usu AS taller
        FROM producto p
        JOIN usuario u ON p.id_usutaller = u.numdocumento
    """)
    productos = cursor.fetchall()
    conn.close()

    return render_template("admin_productos.html", productos=productos)

# --------------------------
# ADMIN - SERVICIOS
# --------------------------
@routes.route("/admin/servicios")
def admin_servicios():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.*, u.nombre_usu AS taller
        FROM servicio s
        JOIN usuario u ON s.id_usutaller = u.numdocumento
    """)
    servicios = cursor.fetchall()
    conn.close()

    return render_template("admin_servicios.html", servicios=servicios)

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
            session["usuario"]["numdocumento"],
            tipo_producto,
            marca_producto,
            precio_producto,
            stock_producto,
            "publicado"
        ))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Producto agregado con éxito ✅", "success")
        return redirect(url_for("routes.perfil_taller"))

    return render_template("agregar_producto.html")

# --------------------------
# AGREGAR VEHÍCULO (CLIENTE)
# --------------------------
@routes.route("/agregar_vehiculo", methods=["GET", "POST"])
def agregar_vehiculo():
    if "usuario" not in session or session["usuario"].get("rol") != "cliente":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        tipo_vehiculo = request.form["tipo_vehiculo"]
        modelo_vehiculo = request.form["modelo_vehiculo"]

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vehiculos (tipo_vehiculo, modelo_vehiculo, id_usucliente)
            VALUES (%s, %s, %s)
        """, (tipo_vehiculo, modelo_vehiculo, session["usuario"]["numdocumento"]))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Vehículo registrado correctamente ✅", "success")
        return redirect(url_for("routes.perfil_cliente"))

    return render_template("agregar_vehiculo.html")

# --------------------------
# ADMIN - PUBLICACIONES
# --------------------------
@routes.route("/admin/publicaciones")
def admin_publicaciones():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    tipo = request.args.get("tipo")
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT rp.id_registro, rp.tipo, rp.id_referencia,
               DATE_FORMAT(rp.fecha_registro, '%d-%m-%Y %H:%i:%s') AS fecha_registro,
               rp.estado,
               u.nombre_usu AS taller, u.correoElectronico
        FROM registro_publicaciones rp
        JOIN usuario u ON rp.id_usutaller = u.numdocumento
        WHERE 1=1
    """
    params = []

    if tipo and tipo != "todos":
        query += " AND rp.tipo = %s"
        params.append(tipo)

    if fecha_inicio:
        query += " AND rp.fecha_registro >= %s"
        params.append(fecha_inicio + " 00:00:00")

    if fecha_fin:
        query += " AND rp.fecha_registro <= %s"
        params.append(fecha_fin + " 23:59:59")

    query += " ORDER BY rp.fecha_registro DESC"

    cursor.execute(query, params)
    registros = cursor.fetchall()
    conn.close()

    return render_template("admin_publicaciones.html", registros=registros, tipo=tipo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

# --------------------------
# ADMIN - VER DETALLE PRODUCTO
# --------------------------
@routes.route("/admin/producto/<int:id_producto>")
def admin_ver_producto(id_producto):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, u.nombre_usu AS taller, u.correoElectronico
        FROM producto p
        JOIN usuario u ON p.id_usutaller = u.numdocumento
        WHERE p.id_producto = %s
    """, (id_producto,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        flash("Producto no encontrado ❌", "danger")
        return redirect(url_for("routes.admin_publicaciones"))

    return render_template("admin_ver_producto.html", producto=producto)

# --------------------------
# ADMIN - VER DETALLE SERVICIO
# --------------------------
@routes.route("/admin/servicio/<int:id_servicio>")
def admin_ver_servicio(id_servicio):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.*, u.nombre_usu AS taller, u.correoElectronico
        FROM servicio s
        JOIN usuario u ON s.id_usutaller = u.numdocumento
        WHERE s.id_servicio = %s
    """, (id_servicio,))
    servicio = cursor.fetchone()
    conn.close()

    if not servicio:
        flash("Servicio no encontrado ❌", "danger")
        return redirect(url_for("routes.admin_publicaciones"))

    return render_template("admin_ver_servicio.html", servicio=servicio)

    # --------------------------
# ADMIN - SOLICITUDES DE TALLER
# --------------------------
@routes.route("/admin/solicitudes_taller")
def solicitudes_taller():
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.numdocumento, u.nombre_usu, u.correoElectronico, r.tipoRol
        FROM usuario u
        JOIN rol r ON u.numdocumento = r.numdocumento
        WHERE r.tipoRol = 'pendiente_taller'
    """)
    solicitudes = cursor.fetchall()
    conn.close()

    return render_template("admin_solicitudes_taller.html", solicitudes=solicitudes)


# --------------------------
# ADMIN - ACEPTAR TALLER
# --------------------------
@routes.route("/admin/solicitudes_taller/aceptar/<int:numdocumento>")
def aceptar_taller(numdocumento):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE rol SET tipoRol = 'taller' WHERE numdocumento = %s", (numdocumento,))
    conn.commit()
    conn.close()

    flash("Taller aprobado con éxito ✅", "success")
    return redirect(url_for("routes.solicitudes_taller"))


# --------------------------
# ADMIN - RECHAZAR TALLER
# --------------------------
@routes.route("/admin/solicitudes_taller/rechazar/<int:numdocumento>")
def rechazar_taller(numdocumento):
    if "admin" not in session:
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor()
    # eliminamos el rol y el usuario
    cursor.execute("DELETE FROM rol WHERE numdocumento = %s", (numdocumento,))
    cursor.execute("DELETE FROM usuario WHERE numdocumento = %s", (numdocumento,))
    conn.commit()
    conn.close()

    flash("Solicitud de taller rechazada ❌", "info")
    return redirect(url_for("routes.solicitudes_taller"))



# --------------------------
# AGREGAR PRODUCTO AL CARRITO (permitir cliente o taller)
# --------------------------
@routes.route("/carrito/agregar/<int:id_producto>", methods=["POST"])
def carrito_agregar(id_producto):
    # permitir compras a clientes y talleres
    if "usuario" not in session or session["usuario"]["rol"] not in ["cliente", "taller"]:
        flash("Debes iniciar sesión como cliente o taller para comprar ❌", "danger")
        return redirect(url_for("routes.login"))

    # cantidad enviada desde el formulario
    try:
        cantidad = int(request.form.get("cantidad", 1))
    except (ValueError, TypeError):
        cantidad = 1

    if cantidad <= 0:
        flash("La cantidad debe ser mayor a 0 ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id_producto, tipo_producto, marca_producto, precio_producto, stock_producto
        FROM producto
        WHERE id_producto=%s
    """, (id_producto,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        flash("Producto no encontrado ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    if producto.get("stock_producto", 0) < cantidad:
        flash(f"Solo hay {producto['stock_producto']} unidades disponibles ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    # Inicializar carrito si no existe
    if "carrito" not in session:
        session["carrito"] = []

    # Revisar si ya está en el carrito -> aumentar cantidad
    for item in session["carrito"]:
        if item.get("tipo") == "producto" and item.get("id_producto") == producto["id_producto"]:
            if item["cantidad"] + cantidad > producto["stock_producto"]:
                flash(f"No puedes agregar más de {producto['stock_producto']} unidades ❌", "danger")
                return redirect(url_for("routes.catalogo"))
            item["cantidad"] += cantidad
            break
    else:
        session["carrito"].append({
            "tipo": "producto",
            "id_producto": producto["id_producto"],
            "nombre": f"{producto['tipo_producto']} - {producto['marca_producto']}",
            "precio": float(producto["precio_producto"]),
            "cantidad": cantidad
        })

    session.modified = True
    flash(f"{cantidad} unidad(es) agregada(s) al carrito 🛒", "success")
    return redirect(url_for("routes.catalogo"))


# --------------------------
# AGREGAR SERVICIO AL CARRITO (1 en 1)
# --------------------------
@routes.route("/carrito/agregar_servicio/<int:id_servicio>", methods=["POST"])
def carrito_agregar_servicio(id_servicio):
    if "usuario" not in session or session["usuario"]["rol"] not in ["cliente", "taller"]:
        flash("Debes iniciar sesión como cliente o taller para pedir un servicio ❌", "danger")
        return redirect(url_for("routes.login"))

    # Los servicios SIEMPRE se agregan de 1 en 1
    cantidad = 1  

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id_servicio, tipo_servicio, precio, disponibilidad
        FROM servicio
        WHERE id_servicio=%s
    """, (id_servicio,))
    servicio = cursor.fetchone()
    conn.close()

    if not servicio:
        flash("Servicio no encontrado ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    if servicio.get("disponibilidad") != 1:
        flash("Este servicio no está disponible ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    if "carrito" not in session:
        session["carrito"] = []

    # Revisar si ya está en el carrito -> sumar 1
    for item in session["carrito"]:
        if item.get("tipo") == "servicio" and item.get("id_servicio") == servicio["id_servicio"]:
            item["cantidad"] += 1
            break
    else:
        session["carrito"].append({
            "tipo": "servicio",
            "id_servicio": servicio["id_servicio"],
            "nombre": servicio["tipo_servicio"],
            "precio": float(servicio["precio"]),
            "cantidad": 1
        })

    session.modified = True
    flash("Servicio agregado al carrito 🛒", "success")
    return redirect(url_for("routes.catalogo"))


# --------------------------
# VER CARRITO
# --------------------------
@routes.route("/carrito")
def carrito_ver():
    carrito = session.get("carrito", [])
    total = sum(item["precio"] * item["cantidad"] for item in carrito) if carrito else 0
    return render_template("carrito.html", carrito=carrito, total=total)


# --------------------------
# ELIMINAR ITEM DEL CARRITO (producto o servicio)
# --------------------------
@routes.route("/carrito/eliminar/<tipo>/<int:id_item>")
def carrito_eliminar(tipo, id_item):
    if "carrito" in session:
        if tipo == "producto":
            session["carrito"] = [
                item for item in session["carrito"]
                if not (item.get("tipo") == "producto" and item.get("id_producto") == id_item)
            ]
        elif tipo == "servicio":
            session["carrito"] = [
                item for item in session["carrito"]
                if not (item.get("tipo") == "servicio" and item.get("id_servicio") == id_item)
            ]
        session.modified = True
        flash("Item eliminado del carrito ❌", "info")
    return redirect(url_for("routes.carrito_ver"))


@routes.route("/carrito/finalizar", methods=["GET", "POST"])
def finalizar_compra():
    if "usuario" not in session or session["usuario"]["rol"] not in ["cliente", "taller"]:
        flash("Debes iniciar sesión como cliente o taller para comprar ❌", "danger")
        return redirect(url_for("routes.login"))

    # Validar que cliente tenga vehículo
    if session["usuario"]["rol"] == "cliente":
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM vehiculos WHERE id_usucliente = %s",
            (session["usuario"]["numdocumento"],)
        )
        tiene_vehiculo = cursor.fetchone()[0]
        conn.close()

        if tiene_vehiculo == 0:
            flash("Debes registrar un vehículo antes de realizar compras 🚗❌", "danger")
            return redirect(url_for("routes.agregar_vehiculo"))

    carrito = session.get("carrito", [])
    if not carrito:
        flash("Tu carrito está vacío 🛒", "info")
        return redirect(url_for("routes.catalogo"))

    conn = conectar_db()
    cursor = conn.cursor()

    try:
        id_cliente = session["usuario"]["numdocumento"]

        # 👉 solo soportamos UN producto por compra en este flujo
        for item in carrito:
            if item.get("tipo") == "producto":
                cursor.execute("""
                    INSERT INTO compra (taller_produc, producto_selec, cantidad, direccion_entrega, id_usucliente)
                    VALUES (
                        (SELECT u.nombre_usu FROM usuario u JOIN producto p ON u.numdocumento = p.id_usutaller WHERE p.id_producto=%s),
                        %s, %s, %s, %s
                    )
                """, (
                    item["id_producto"],
                    item["id_producto"],
                    item["cantidad"],
                    "Sin dirección",  # puedes pedir dirección en el formulario
                    id_cliente
                ))

        conn.commit()
        flash("Compra registrada ✅. Esperando confirmación del taller.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Ocurrió un error al finalizar la compra: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    # limpiar carrito
    session.pop("carrito", None)
    session.modified = True

    return redirect(url_for("routes.perfil_cliente"))


# --------------------------
# RUTAS PARA FACTURAS (USUARIO)
# --------------------------
@routes.route("/mis_facturas")
def mis_facturas():
    if "usuario" not in session:
        flash("Debes iniciar sesión para ver tus facturas", "warning")
        return redirect(url_for("routes.login"))

    id_usuario = session["usuario"]["numdocumento"]
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.id_factura, f.fecha_emision, f.total
        FROM factura f
        WHERE f.id_cliente = %s
        ORDER BY f.fecha_emision DESC
    """, (id_usuario,))
    facturas = cursor.fetchall()
    conn.close()
    return render_template("mis_facturas.html", facturas=facturas)


@routes.route("/factura/<int:id_factura>")
def ver_factura(id_factura):
    # Solo el cliente dueño de la factura (o admin) puede verla
    if "usuario" not in session:
        flash("Debes iniciar sesión para ver la factura", "warning")
        return redirect(url_for("routes.login"))

    id_usuario = session["usuario"]["numdocumento"]
    is_admin = "admin" in session

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # verificar que la factura pertenezca al usuario (o permitir admin)
    cursor.execute("SELECT id_cliente FROM factura WHERE id_factura = %s", (id_factura,))
    fila = cursor.fetchone()
    if not fila:
        conn.close()
        flash("Factura no encontrada ❌", "danger")
        return redirect(url_for("routes.mis_facturas"))

    if fila["id_cliente"] != id_usuario and not is_admin:
        conn.close()
        flash("No tienes permiso para ver esta factura ❌", "danger")
        return redirect(url_for("routes.mis_facturas"))

    # obtener detalles (productos y servicios)
    cursor.execute("""
        SELECT d.id_detalle,
               d.id_producto, p.tipo_producto AS producto_nombre, p.marca_producto,
               d.id_servicio, s.tipo_servicio AS servicio_nombre,
               d.cantidad, d.precio_unitario, d.subtotal
        FROM detalle_factura d
        LEFT JOIN producto p ON d.id_producto = p.id_producto
        LEFT JOIN servicio s ON d.id_servicio = s.id_servicio
        WHERE d.id_factura = %s
    """, (id_factura,))
    detalles = cursor.fetchall()

    # obtener encabezado
    cursor.execute("SELECT id_factura, id_cliente, fecha_emision, total FROM factura WHERE id_factura = %s", (id_factura,))
    factura = cursor.fetchone()

    conn.close()
    return render_template("ver_factura.html", factura=factura, detalles=detalles)

# --------------------------
# PETICIONES DE COMPRA (TALLER)
# --------------------------
@routes.route("/taller/peticiones")
def ver_peticiones_taller():
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    id_taller = session["usuario"]["numdocumento"]

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT pc.id_peticion, c.id_compra, u.nombre_usu AS cliente, p.tipo_producto, c.cantidad, pc.estado, pc.fecha
        FROM peticion_compra pc
        JOIN compra c ON pc.id_compra = c.id_compra
        JOIN usuario u ON c.id_usucliente = u.numdocumento
        JOIN producto p ON c.producto_selec = p.id_producto
        WHERE pc.id_taller = %s
        ORDER BY pc.fecha DESC
    """, (id_taller,))
    peticiones = cursor.fetchall()
    conn.close()

    return render_template("peticiones_taller.html", peticiones=peticiones)


@routes.route("/peticiones/<int:id_peticion>/confirmar", methods=["POST"])
def confirmar_peticion(id_peticion):
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    estado = request.form.get("estado")  # aprobada o rechazada
    if estado not in ["aprobada", "rechazada"]:
        flash("Estado inválido ❌", "danger")
        return redirect(url_for("routes.ver_peticiones_taller"))

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE peticion_compra SET estado = %s WHERE id_peticion = %s", (estado, id_peticion))
    conn.commit()
    conn.close()

    flash(f"Petición {estado} con éxito ✅", "success")
    return redirect(url_for("routes.ver_peticiones_taller"))
