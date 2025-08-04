import socket
import uuid
import platform
import psutil
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

from Module.DB_FullHouse.DB import get_db_connection

app = Flask(__name__,
            template_folder='Module/views',
            static_folder='Module/static')
app.secret_key = 'TU_CLAVE_SECRETA_LARGA_Y_ALEATORIA_AQUI'

def get_divices_info():
    ip_address = socket.gethostbyname(socket.gethostname())
    print(f"ip-address:{ip_address}")
    return {
        "cpu_usage":psutil.cpu_percent(interval=1),
        "ip-address":ip_address,
        "ram_usage":psutil.virtual_memory().percent,
        "mac_address":':'.join(['{:02x}'.format((uuid.getnode()>>ele)&0xef)for ele in range (0,48,8)])
    }

@app.route('/divice_info',methods=['GET'])
def divice_info():
    return jsonify(get_divices_info())

@app.route('/')
@app.route('/index.html')
def show_index():
    username = session.get('username', 'Invitado')
    return render_template('index.html', username=username)

@app.route('/register', methods=['GET'])
def show_register_form():
    return render_template('Registro.html')

@app.route('/register', methods=['POST'])
def register_user():
    full_name = request.form['nombre']
    email = request.form['email']
    username = request.form['usuario']
    password = request.form['password']
    confirm_password = request.form['confirmar']

    if password != confirm_password:
        return "Las contraseñas no coinciden. <a href='/register'>Volver al registro</a>"

    hashed_password = generate_password_hash(password)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id FROM Users WHERE email = %s OR username = %s", (email, username))
        if cursor.fetchone():
            return "El email o nombre de usuario ya está registrado. <a href='/register'>Volver al registro</a>"

        sql = "INSERT INTO Users (full_name, username, email, password_hash) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (full_name, username, email, hashed_password))
        conn.commit()
        return redirect(url_for('show_login_form'))
    except mysql.connector.Error as err:
        print(f"Error al registrar usuario: {err}")
        if conn: conn.rollback()
        return "Error al registrar usuario. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/login', methods=['GET'])
def show_login_form():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_user():
    email = request.form['email']
    password = request.form['password']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, password_hash, username FROM Users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('show_index'))
        else:
            return "Email o contraseña incorrectos. <a href='/login'>Volver a intentar</a>"
    except mysql.connector.Error as err:
        print(f"Error al iniciar sesión: {err}")
        return "Error al iniciar sesión. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('show_login_form'))

@app.route('/create_group', methods=['GET'])
def show_create_group_form():
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))
    return render_template('CrearGrupo.html')

@app.route('/create_group', methods=['POST'])
def create_group():
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))

    name = request.form['nombreGrupo']
    description = request.form['descripcionGrupo']
    image_file = request.files.get('imagenGrupo')
    
    image_url = url_for('static', filename='images/' + image_file.filename) if image_file and image_file.filename else 'https://via.placeholder.com/400x200'
    
    category = request.form['categoria']
    privacy_type = request.form['privacidad']
    creator_user_id = session['user_id']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
        INSERT INTO Grupos (name, description, image_url, category, privacy_type, creator_user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (name, description, image_url, category, privacy_type, creator_user_id))
        new_group_id = cursor.lastrowid

        sql_member = "INSERT INTO GroupMembers (user_id, group_id, role) VALUES (%s, %s, %s)"
        cursor.execute(sql_member, (creator_user_id, new_group_id, 'admin'))
        conn.commit()
        return redirect(url_for('show_grupos_usuario'))
    except mysql.connector.Error as err:
        print(f"Error al crear grupo: {err}")
        if conn: conn.rollback()
        return "Error al crear el grupo. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/gruposusuario.html')
def show_grupos_usuario():
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))

    user_id = session['user_id']
    my_groups = []
    explore_groups = []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql_my_groups = """
        SELECT g.* FROM Grupos g
        JOIN GroupMembers gm ON g.group_id = gm.group_id
        WHERE gm.user_id = %s
        ORDER BY g.name
        """
        cursor.execute(sql_my_groups, (user_id,))
        my_groups = cursor.fetchall()

        sql_explore_groups = """
        SELECT g.* FROM Grupos g
        LEFT JOIN GroupMembers gm ON g.group_id = gm.group_id AND gm.user_id = %s
        WHERE gm.user_id IS NULL AND g.privacy_type = 'publico'
        ORDER BY g.name
        """
        cursor.execute(sql_explore_groups, (user_id,))
        explore_groups = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error al cargar grupos: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return render_template('GruposUsuario.html', my_groups=my_groups, explore_groups=explore_groups)

@app.route('/join_group/<int:group_id>', methods=['POST'])
def join_group(group_id):
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))
    
    user_id = session['user_id']
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM GroupMembers WHERE user_id = %s AND group_id = %s", (user_id, group_id))
        if cursor.fetchone():
            return "Ya eres miembro de este grupo."

        sql = "INSERT INTO GroupMembers (user_id, group_id) VALUES (%s, %s)"
        cursor.execute(sql, (user_id, group_id))
        conn.commit()
        
        return redirect(url_for('show_group_details', group_id=group_id))
    except mysql.connector.Error as err:
        print(f"Error al unirse al grupo: {err}")
        if conn: conn.rollback()
        return "Error al unirte al grupo. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/perfilconfig.html', methods=['GET'])
def show_perfil_config():
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))

    user_id = session['user_id']
    user_data = None
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT full_name, email, username, profile_picture_url FROM Users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Error al cargar datos del perfil: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('PerfilConfig.html', user=user_data)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))

    user_id = session['user_id']
    full_name = request.form['nombre']
    email = request.form['email']
    username = request.form['usuario']
    new_password = request.form.get('nuevaPassword')
    confirm_password = request.form.get('confirmarPassword')
    profile_picture_url = request.form.get('foto')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        updates = []
        params = []
        updates.append("full_name = %s")
        params.append(full_name)

        current_email = None
        current_username = None
        cursor.execute("SELECT email, username FROM Users WHERE user_id = %s", (user_id,))
        current_user_data = cursor.fetchone()
        if current_user_data:
            current_email = current_user_data[0]
            current_username = current_user_data[1]

        if email and email != current_email:
            cursor.execute("SELECT user_id FROM Users WHERE email = %s AND user_id != %s", (email, user_id))
            if cursor.fetchone():
                return "El email ya está en uso por otra cuenta. <a href='/perfilconfig.html'>Volver a configuración</a>"
            updates.append("email = %s")
            params.append(email)
            
        if username and username != current_username:
            cursor.execute("SELECT user_id FROM Users WHERE username = %s AND user_id != %s", (username, user_id))
            if cursor.fetchone():
                return "El nombre de usuario ya está en uso. <a href='/perfilconfig.html'>Volver a configuración</a>"
            updates.append("username = %s")
            params.append(username)
            session['username'] = username

        if profile_picture_url:
            updates.append("profile_picture_url = %s")
            params.append(profile_picture_url)

        if new_password:
            if new_password != confirm_password:
                return "La nueva contraseña y su confirmación no coinciden. <a href='/perfilconfig.html'>Volver a configuración</a>"
            hashed_new_password = generate_password_hash(new_password)
            updates.append("password_hash = %s")
            params.append(hashed_new_password)

        if not updates:
            return redirect(url_for('show_perfil_config'))

        sql = "UPDATE Users SET " + ", ".join(updates) + " WHERE user_id = %s"
        params.append(user_id)
        cursor.execute(sql, tuple(params))
        conn.commit()
        return redirect(url_for('show_perfil_config'))
    except mysql.connector.Error as err:
        print(f"Error al actualizar perfil: {err}")
        if conn: conn.rollback()
        return "Error al actualizar perfil. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/grupo/<int:group_id>')
def show_group_details(group_id):
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))

    group_data = None
    posts = []
    is_member = False
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Grupos WHERE group_id = %s", (group_id,))
        group_data = cursor.fetchone()

        if not group_data: return "Grupo no encontrado."

        cursor.execute("SELECT 1 FROM GroupMembers WHERE user_id = %s AND group_id = %s", (session['user_id'], group_id))
        if cursor.fetchone(): is_member = True

        if group_data['privacy_type'] == 'privado' and not is_member:
            return "No tienes acceso a este grupo privado."

        sql_posts = """
        SELECT p.*, u.username, u.profile_picture_url
        FROM Posts p
        JOIN Users u ON p.user_id = u.user_id
        WHERE p.group_id = %s
        ORDER BY p.post_date DESC
        """
        cursor.execute(sql_posts, (group_id,))
        posts = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error al cargar detalles del grupo: {err}")
        return "Error al cargar detalles del grupo. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    return render_template('DentroGrupo.html', group=group_data, posts=posts, group_id=group_id, is_member=is_member)

@app.route('/grupo/<int:group_id>/crearpubli.html', methods=['GET'])
def show_create_post_form(group_id):
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))
    
    conn = None
    cursor = None
    is_member = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM GroupMembers WHERE user_id = %s AND group_id = %s", (session['user_id'], group_id))
        is_member = cursor.fetchone()
        if not is_member:
            return "No puedes publicar en un grupo del que no eres miembro."
    except mysql.connector.Error as err:
        print(f"Error al verificar membresía: {err}")
        return "Error al verificar membresía. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    return render_template('CrearPubli.html', group_id=group_id)

@app.route('/grupo/<int:group_id>/create_post', methods=['POST'])
def create_post(group_id):
    if 'user_id' not in session:
        return redirect(url_for('show_login_form'))
    
    user_id = session['user_id']
    content_text = request.form['contenidoPost']
    image_file = request.files.get('imagenPost')
    image_url = None
    if image_file and image_file.filename:
        image_url = url_for('static', filename='images/' + image_file.filename)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM GroupMembers WHERE user_id = %s AND group_id = %s", (user_id, group_id))
        if not cursor.fetchone():
            return "No tienes permiso para publicar en este grupo."

        sql = "INSERT INTO Posts (group_id, user_id, content_text) VALUES (%s, %s, %s)"
        cursor.execute(sql, (group_id, user_id, content_text))
        post_id = cursor.lastrowid
        
        if image_url:
            sql_image = "INSERT INTO PostImages (post_id, image_url) VALUES (%s, %s)"
            cursor.execute(sql_image, (post_id, image_url))
            
        conn.commit()
        return redirect(url_for('show_group_details', group_id=group_id))
    except mysql.connector.Error as err:
        print(f"Error al crear publicación: {err}")
        if conn: conn.rollback()
        return "Error al crear la publicación. Inténtalo de nuevo."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)