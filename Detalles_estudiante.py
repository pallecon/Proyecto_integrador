import os
import sys
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path
import mysql.connector
from django.conf import settings
import django
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def crear_conexion(host_name, user_name, user_password, db_name):
    """Crea y retorna una conexión a la base de datos MySQL. Devuelve None si ocurre un error."""
    try:
        return mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
    except mysql.connector.Error as err:
        logger.error(f"Error conexión MySQL: {err}")
        return None

def obtener_modalidades():
    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    modalidades = []
    if conexion:
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT id_modalidad, nombre_modalidad FROM Modalidades_Graduacion")
            modalidades = cursor.fetchall()
        except Exception as e:
            logger.error(f"Error obtener modalidades: {e}")
        cursor.close()
        conexion.close()
    return modalidades

def obtener_estudiantes():
    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    estudiantes = []
    if conexion:
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT id_estudiante, nombre FROM Estudiantes")
            estudiantes = cursor.fetchall()
        except Exception as e:
            logger.error(f"Error obtener estudiantes: {e}")
        cursor.close()
        conexion.close()
    return estudiantes

def detalles_estudiantes_view(request):
    mensaje_error = ""
    detalles = []
    detalle = None
    mostrar_formulario_agregar = False

    id_detalle = request.GET.get("id_detalle") or request.POST.get("id_detalle")
    accion = request.GET.get("accion") or request.POST.get("accion")
    eliminar_id = request.GET.get("eliminar_id")

    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    cursor = conexion.cursor() if conexion else None

    if eliminar_id and cursor:
        try:
            cursor.execute("DELETE FROM Detalle_estudiante WHERE id_detalle=%s", (eliminar_id,))
            conexion.commit()
        except Exception as e:
            mensaje_error = f"Error al eliminar: {e}"

    modalidades = obtener_modalidades()
    estudiantes = obtener_estudiantes()

    if request.method == "POST" and request.POST.get("agregar") == "1" and cursor:
        id_estudiante = request.POST.get("id_estudiante")
        observaciones = request.POST.get("observaciones")
        id_modalidad = request.POST.get("id_modalidad")
        estado_pago = request.POST.get("estado_pago")
        try:
            cursor.execute("""
                INSERT INTO Detalle_estudiante (id_estudiante, observaciones, id_modalidad, estado_pago)
                VALUES (%s, %s, %s, %s)
            """, (id_estudiante, observaciones, id_modalidad, estado_pago))
            conexion.commit()
            return HttpResponse('<script>window.history.back();</script>')
        except Exception as e:
            mensaje_error = f"Error al añadir: {e}"

    if request.method == "POST" and request.POST.get("editar") == "1" and cursor:
        id_detalle = request.POST.get("id_detalle")
        id_estudiante = request.POST.get("id_estudiante")
        observaciones = request.POST.get("observaciones")
        id_modalidad = request.POST.get("id_modalidad")
        estado_pago = request.POST.get("estado_pago")
        try:
            cursor.execute("""
                UPDATE Detalle_estudiante
                SET id_estudiante=%s, observaciones=%s, id_modalidad=%s, estado_pago=%s
                WHERE id_detalle=%s
            """, (id_estudiante, observaciones, id_modalidad, estado_pago, id_detalle))
            conexion.commit()
            return HttpResponse('<script>window.history.back();</script>')
        except Exception as e:
            mensaje_error = f"Error al editar: {e}"

    if accion == "agregar":
        mostrar_formulario_agregar = True

    if id_detalle and not mostrar_formulario_agregar and cursor:
        cursor.execute("""
            SELECT id_detalle, id_estudiante, observaciones, id_modalidad, estado_pago
            FROM Detalle_estudiante
            WHERE id_detalle = %s
        """, (id_detalle,))
        detalle = cursor.fetchone()
        if not detalle:
            mensaje_error = "Detalle de estudiante no encontrado."
    elif cursor:
        cursor.execute("""
            SELECT e.nombre, d.observaciones, m.nombre_modalidad, d.estado_pago, d.id_detalle
            FROM Detalle_estudiante d
            JOIN Estudiantes e ON d.id_estudiante = e.id_estudiante
            JOIN Modalidades_Graduacion m ON d.id_modalidad = m.id_modalidad
            ORDER BY d.id_detalle DESC
        """)
        detalles = cursor.fetchall()

    if cursor:
        cursor.close()
    if conexion:
        conexion.close()

    def opciones_estudiante_html(selected=None):
        opciones = '<option value="">-- Seleccione Estudiante --</option>'
        for e in estudiantes:
            if str(e[0]) == str(selected):
                opciones += f'<option value="{e[0]}" selected>{e[1]}</option>'
            else:
                opciones += f'<option value="{e[0]}">{e[1]}</option>'
        return opciones

    def opciones_modalidad_html(selected=None):
        opciones = '<option value="">-- Seleccione Modalidad --</option>'
        for m in modalidades:
            if str(m[0]) == str(selected):
                opciones += f'<option value="{m[0]}" selected>{m[1]}</option>'
            else:
                opciones += f'<option value="{m[0]}">{m[1]}</option>'
        return opciones

    estilos = '''
    <style>
    * { margin:0; padding:0; box-sizing:border-box; font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
    :root {
        --primary:#1a3a52; --accent:#2c5aa0; --muted:#546e7a; --bg:#e8e8e8;
        --card:#ffffff; --success:#4caf50; --danger:#f44336; --shadow:0 10px 30px rgba(0,0,0,0.1);
    }
    body { background: #e8e8e8; color:#1a3a52; padding:40px 12px; min-height:100vh; }
    .top-bar { display:flex; justify-content:space-between; align-items:center; gap:12px; width:100%; position:fixed; top:0; left:0; padding:18px 22px; background:#1a3a52; color:#fff; box-shadow:var(--shadow); z-index:1000; }
    .top-bar h1 { font-size:1.1rem; letter-spacing:1px; }
    .btn-menu { padding:12px 18px; background:#2c5aa0; color:#ffffff; border:none; border-radius:8px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:8px; box-shadow:0 4px 12px rgba(44,90,160,0.3); transition:all .2s ease; }
    .btn-menu:hover { transform:translateY(-2px); box-shadow:0 6px 16px rgba(44,90,160,0.5); background:#3d6fb8; }
    .container { max-width:1100px; margin:80px auto 0 auto; background:transparent; border-radius:14px; padding:0 12px; box-shadow:none; }
    h2 { color:#1a3a52; font-size:1.6rem; margin-bottom:18px; text-align:center; }
    .actions { display:flex; justify-content:flex-end; gap:12px; margin-bottom:24px; }
    table { width:100%; border-collapse:collapse; margin-top:0; background:var(--card); border-radius:14px; overflow:hidden; box-shadow:var(--shadow); }
    thead th { text-align:center; padding:16px 12px; background:#1a3a52; color:#ffffff; font-weight:700; border-radius:0; }
    tbody tr { background:#ffffff; transition:transform .15s ease, box-shadow .15s ease; border-radius:0; margin-bottom:0; border-bottom:1px solid #e0e0e0; }
    tbody tr:last-child { border-bottom:none; }
    tbody tr:hover { transform:none; box-shadow:none; background:#f5f9ff; }
    td { padding:14px 12px; text-align:center; color:#546e7a; font-weight:600; }
    td:first-child { color:#2c5aa0; font-weight:700; }
    .acciones a { margin:0 6px; padding:8px 10px; border-radius:8px; text-decoration:none; color:#fff; display:inline-block; }
    .editar { background:#2c5aa0; }
    .editar:hover { background:#3d6fb8; }
    .eliminar { background:#c62828; }
    .eliminar:hover { background:#e53935; }
    .detalle { max-width:720px; margin:16px auto; background:#ffffff; padding:20px; border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.1); border:1px solid #e0e0e0; }
    .detalle p { display:flex; gap:12px; align-items:center; margin-bottom:12px; }
    .detalle label { min-width:160px; font-weight:800; color:#2c5aa0; }
    .detalle select, .detalle input { flex:1; padding:10px 12px; border-radius:8px; border:1px solid #2c5aa0; background:#ffffff; color:#1a3a52; }
    .btn { padding:10px 16px; border:none; border-radius:8px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:8px; transition:all .2s ease; }
    .btn-primary { background:#2c5aa0; color:#fff; }
    .btn-primary:hover { background:#3d6fb8; }
    .btn-ghost { background:#d4d4d4; color:#2c5aa0; }
    .btn-ghost:hover { background:#c0c0c0; }
    .volver-btn { display:inline-block; margin-top:12px; width:100%; }
    .msg-error { background:#c62828; color:#fff; padding:12px; border-radius:10px; font-weight:700; text-align:center; margin-bottom:12px; }
    .msg-success { background:#2e7d32; color:#fff; padding:12px; border-radius:10px; font-weight:700; text-align:center; margin-bottom:12px; }
    @media (max-width:820px){ .detalle label{ min-width:120px;} .top-bar{ padding:12px; } }
    </style>
    '''

    html = f'''
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Detalle de Estudiante</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
        {estilos}
    </head>
    <body>
        <div class="top-bar">
            <button class="btn-menu" onclick="window.location.href='/menu'"><i class="fa fa-arrow-left"></i> Volver al Menú</button>
            <h1><i class="fa fa-graduation-cap"></i> Sistema - Detalle de Estudiante</h1>
        </div>

        <div class="container">
    '''

    if mensaje_error:
        html += f'<div class="msg-error"><i class="fa fa-exclamation-triangle"></i> {mensaje_error}</div>'

    html += '<div class="actions"><button class="btn-menu" onclick="window.location.href=\'?accion=agregar\'"><i class="fa fa-plus"></i> Crear Nuevo Registro</button></div>'

    if mostrar_formulario_agregar:
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="agregar" value="1">
            <p><label>Estudiante:</label>
                <select name="id_estudiante" required>{opciones_estudiante_html()}</select>
            </p>
            <p><label>Observaciones:</label>
                <select name="observaciones" required>
                    <option value="activo">activo</option>
                    <option value="no activo">no activo</option>
                </select>
            </p>
            <p><label>Modalidad:</label>
                <select name="id_modalidad" required>{opciones_modalidad_html()}</select>
            </p>
            <p><label>Estado de Pago:</label>
                <select name="estado_pago" required>
                    <option value="Pagado">Pagado</option>
                    <option value="No Pagado">No Pagado</option>
                </select>
            </p>
            <button type="submit" class="btn btn-primary volver-btn"><i class="fa fa-plus"></i> Añadir</button>
            <button type="button" class="btn btn-ghost volver-btn" onclick="window.history.back();"><i class="fa fa-arrow-left"></i> Volver</button>
        </form>
        '''
    elif detalle:
        # Mantener id_detalle oculto para poder editar, pero no mostrarlo en el formulario
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="editar" value="1">
            <input type="hidden" name="id_detalle" value="{detalle[0]}">
            <p><label>Estudiante:</label>
                <select name="id_estudiante" required>{opciones_estudiante_html(detalle[1])}</select>
            </p>
            <p><label>Observaciones:</label>
                <select name="observaciones" required>
                    <option value="activo" {'selected' if detalle[2]=='activo' else ''}>activo</option>
                    <option value="no activo" {'selected' if detalle[2]=='no activo' else ''}>no activo</option>
                </select>
            </p>
            <p><label>Modalidad:</label>
                <select name="id_modalidad" required>{opciones_modalidad_html(detalle[3])}</select>
            </p>
            <p><label>Estado de Pago:</label>
                <select name="estado_pago" required>
                    <option value="Pagado" {'selected' if detalle[4]=='Pagado' else ''}>Pagado</option>
                    <option value="No Pagado" {'selected' if detalle[4]=='No Pagado' else ''}>No Pagado</option>
                </select>
            </p>
            <button type="submit" class="btn btn-primary volver-btn"><i class="fa fa-save"></i> Guardar Cambios</button>
            <button type="button" class="btn btn-ghost volver-btn" onclick="window.history.back();"><i class="fa fa-arrow-left"></i> Volver</button>
        </form>
        '''
    else:
        html += '''
        <div style="overflow:auto; margin: 24px 0; padding: 0; background:transparent; border-radius:12px;">
            <table>
                <thead>
                    <tr>
                        <th>Estudiante</th><th>Observaciones</th><th>Modalidad</th><th>Estado de Pago</th><th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
        '''
     
        for d in detalles:
            html += f'''
            <tr onclick="window.location='?id_detalle={d[4]}'" style="cursor:pointer">
                <td>{d[0]}</td>
                <td>{d[1]}</td>
                <td>{d[2]}</td>
                <td>{d[3]}</td>
                <td class="acciones">
                    <a href="?id_detalle={d[4]}" class="editar" title="Editar" onclick="event.stopPropagation()"><i class="fa fa-pen"></i></a>
                    <a href="#" class="eliminar" title="Eliminar" onclick="event.stopPropagation(); if(confirm('¿Seguro que deseas eliminar este registro?')) window.location='?eliminar_id={d[4]}'"><i class="fa fa-trash"></i></a>
                </td>
            </tr>
            '''

        html += '''
                </tbody>
            </table>
        </div>
        '''

    html += '''
        </div>
    </body>
    </html>
    '''

    return HttpResponse(html)

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SECRET_KEY = 'secret-key'
    DEBUG = True

    if not settings.configured:
        settings.configure(
            DEBUG=DEBUG,
            SECRET_KEY=SECRET_KEY,
            ROOT_URLCONF=__name__,
            ALLOWED_HOSTS=['*'],
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.staticfiles',
            ],
            MIDDLEWARE=[],
            TEMPLATES=[
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [],
                    'APP_DIRS': True,
                    'OPTIONS': {
                        'context_processors': [
                            'django.template.context_processors.debug',
                            'django.template.context_processors.request',
                            'django.contrib.auth.context_processors.auth',
                            'django.contrib.messages.context_processors.messages',
                        ],
                    },
                },
            ],
            STATIC_URL='/static/',
            STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')],
            USE_TZ=True,
            TIME_ZONE='America/La_Paz',
        )

    django.setup()

    urlpatterns = [
        path('', detalles_estudiantes_view),
        path('detalle_estudiante/', detalles_estudiantes_view),
    ]

    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], "runserver", "8000"])
