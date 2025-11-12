import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '/73588144/',
    'database': 'proyecto',
    'port': 3306,
}

def crear_conexion(host, usuario, contraseña, base_datos):
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='/73588144/',
            database='proyecto'
        )
        if conexion.is_connected():
            print("Conexión exitosa a la base de datos")
            return conexion
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

def cerrar_conexion(conexion):
    if conexion and conexion.is_connected():
        conexion.close()
        print("Conexión cerrada")