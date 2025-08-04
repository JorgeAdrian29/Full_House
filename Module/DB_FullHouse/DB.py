import mysql.connector
import os

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DB'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            # Forzar el conector a usar TCP/IP en lugar de named pipes
            unix_socket=None,
            buffered=True
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error en la conexión a la base de datos: {err}")
        # Lanza la excepción para que sea manejada en app.py
        raise err