import socket
import uuid
import platform
import psutil
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from login.controller.auth_controller import authenticate_user
import sys
from os.path import dirname, join, abspath

# Añade el directorio del proyecto al PATH de Python
project_dir = dirname(dirname(abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Ahora puedes importar desde login
from login.controller.auth_controller import authenticate_user

app = Flask(__name__, template_folder='views')
app.secret_key = 'admin123'

# Configuración de rutas estáticas
app.static_folder = 'static'

def get_devices_info():
    ip_address = socket.gethostbyname(socket.gethostname())
    return {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "ip_address": ip_address,
        "ram_usage": psutil.virtual_memory().percent,
        "mac_address": ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 48, 8)][::-1]),
        "system": platform.system(),
        "platform": platform.platform()
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if authenticate_user(request.form['username'], request.form['password']):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Credenciales inválidas")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', device_data=get_devices_info())

@app.route('/device_info')
def device_info():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    return jsonify(get_devices_info())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

