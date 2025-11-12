import os
import sys
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path
import mysql.connector
from django.conf import settings
import django

def crear_conexion(host_name, user_name, user_password, db_name):
    """Crea y retorna una conexión a la base de datos MySQL.
    Devuelve None si ocurre un error.
    """
    try:
        return mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
    except mysql.connector.Error as err:
        print(f"Error: '{err}'")
        return None

def obtener_modalidades():
    """Obtiene la lista de modalidades de la tabla Modalidades_Graduacion.
    Retorna una lista de tuplas (id_modalidad, nombre_modalidad).
    """
    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    modalidades = []
    if conexion:
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT id_modalidad, nombre_modalidad FROM Modalidades_Graduacion")
            modalidades = cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener modalidades: {e}")
        cursor.close()
        conexion.close()
    return modalidades

def obtener_estudiantes():
    """Obtiene la lista de estudiantes de la tabla Estudiantes.
    Retorna una lista de tuplas (id_estudiante, nombre).
    """
    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    estudiantes = []
    if conexion:
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT id_estudiante, nombre FROM Estudiantes")
            estudiantes = cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener estudiantes: {e}")
        cursor.close()
        conexion.close()
    return estudiantes

def detalles_estudiantes_view(request):
    """Vista principal que maneja listar, agregar, editar y eliminar detalles de estudiantes.
    Recibe un objeto request tipo Django y retorna HttpResponse con HTML.
    """
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
            return HttpResponse(
                '<script>window.history.back();</script>'
            )
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
            return HttpResponse(
                '<script>window.history.back();</script>'
            )
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
            SELECT d.id_detalle, e.nombre, d.observaciones, m.nombre_modalidad, d.estado_pago
            FROM Detalle_estudiante d
            JOIN Estudiantes e ON d.id_estudiante = e.id_estudiante
            JOIN Modalidades_Graduacion m ON d.id_modalidad = m.id_modalidad
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

    html = f'''
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Detalle de Estudiante</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
            }}
            body {{
                background: linear-gradient(120deg, #2196f3 0%, #e3f6fd 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 40px 10px 0 10px;
                color: #234;
                background-size: 200% 200%;
            }}
            .container {{
                background: rgba(255,255,255,0.97);
                max-width: 950px;
                width: 100%;
                border-radius: 22px;
                box-shadow: 0 12px 40px 0 rgba(33,150,243,0.13);
                padding: 36px 40px 30px 40px;
                margin-bottom: 40px;
                margin-top: 60px;
                position: relative;
                animation: fadeIn 1s;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(30px);}}
                to {{ opacity: 1; transform: translateY(0);}}
            }}
            h2 {{
                text-align: center;
                color: #1976d2;
                margin-bottom: 30px;
                font-weight: 800;
                letter-spacing: 1.5px;
                font-size: 2.2rem;
                text-shadow: 0 2px 8px #b3e5fc;
            }}
            table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0 10px;
                font-size: 1.05rem;
                margin-bottom: 20px;
            }}
            thead th {{
                background: linear-gradient(90deg, #1976d2 60%, #4fc3f7 100%);
                color: #fff;
                padding: 14px 15px;
                text-align: center;
                border-radius: 12px 12px 0 0;
                letter-spacing: 0.07em;
                font-weight: 700;
                font-size: 1.08em;
                box-shadow: 0 2px 8px #b3e5fc99;
            }}
            tbody tr {{
                background: #e3f6fd;
                transition: background 0.3s, box-shadow 0.3s;
                border-radius: 12px;
                cursor: pointer;
                box-shadow: 0 2px 8px #b3e5fc33;
            }}
            tbody tr:hover {{
                background: linear-gradient(90deg, #bbdefb 0%, #e3f6fd 100%);
                box-shadow: 0 6px 18px #4fc3f766;
            }}
            tbody td {{
                padding: 13px 15px;
                text-align: center;
                color: #1976d2;
                vertical-align: middle;
                font-weight: 500;
            }}
            .acciones a {{
                margin: 0 6px;
                padding: 7px 14px;
                border-radius: 8px;
                font-size: 1em;
                display: inline-block;
                transition: background 0.2s, color 0.2s;
                text-decoration: none;
            }}
            .acciones .editar {{
                background: #e3f2fd;
                color: #1976d2;
                border: 1px solid #1976d2;
            }}
            .acciones .editar:hover {{
                background: #1976d2;
                color: #fff;
            }}
            .acciones .eliminar {{
                background: #ffebee;
                color: #e53935;
                border: 1px solid #e53935;
            }}
            .acciones .eliminar:hover {{
                background: #e53935;
                color: #fff;
            }}
            .volver-btn, .detalle button[type="submit"] {{
                display: block;
                width: 100%;
                margin: 18px auto 0 auto;
                padding: 14px 0;
                text-align: center;
                background: linear-gradient(90deg, #1976d2 60%, #4fc3f7 100%);
                color: white;
                font-weight: 700;
                border-radius: 25px;
                box-shadow: 0 6px 20px #4fc3f766;
                text-decoration: none;
                border: none;
                font-size: 1.08em;
                letter-spacing: 1px;
                cursor: pointer;
                transition: background 0.3s, transform 0.2s, box-shadow 0.3s;
            }}
            .volver-btn:hover, .detalle button[type="submit"]:hover {{
                background: linear-gradient(90deg, #0d47a1 60%, #1976d2 100%);
                transform: translateY(-3px) scale(1.03);
                box-shadow: 0 10px 28px #1976d277;
            }}
            .detalle {{
                background: #fafdff;
                padding: 28px 32px;
                border-radius: 18px;
                box-shadow: 0 8px 24px rgba(33,150,243,0.10);
                max-width: 600px;
                margin: 0 auto 35px auto;
                animation: fadeIn 0.7s;
            }}
            .detalle p {{
                font-size: 1.13rem;
                margin-bottom: 18px;
                color: #1976d2;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .detalle label {{
                font-weight: 700;
                color: #1565c0;
                min-width: 140px;
                display: inline-block;
                font-size: 1.08rem;
            }}
            .detalle input[type="number"],
            .detalle input[type="text"],
            .detalle select {{
                padding: 10px 14px;
                border-radius: 8px;
                border: 1.5px solid #4fc3f7;
                font-size: 1em;
                background: #e3f6fd;
                transition: border-color 0.3s, box-shadow 0.3s;
                margin-left: 0;
                color: #1976d2;
                font-weight: 500;
                outline: none;
                box-shadow: 0 1px 4px #b3e5fc33;
            }}
            .detalle input:focus,
            .detalle select:focus {{
                border-color: #1976d2;
                box-shadow: 0 0 10px #4fc3f7;
                background: #bbdefb;
            }}
            .error-msg {{
                background: linear-gradient(90deg, #e53935 60%, #ffb3b3 100%);
                color: white;
                padding: 15px 20px;
                border-radius: 12px;
                box-shadow: 0 5px 15px #e5393555;
                font-weight: 700;
                text-align: center;
                max-width: 600px;
                margin: 20px auto;
                font-size: 1.08em;
                letter-spacing: 1px;
            }}
            .success-msg {{
                background: linear-gradient(90deg, #43a047 60%, #b2ffb3 100%);
                color: white;
                padding: 15px 20px;
                border-radius: 12px;
                box-shadow: 0 5px 15px #43a04755;
                font-weight: 700;
                text-align: center;
                max-width: 600px;
                margin: 20px auto;
                font-size: 1.08em;
                letter-spacing: 1px;
            }}
            @media (max-width: 700px) {{
                .container {{
                    padding: 18px 6px;
                }}
                .detalle {{
                    padding: 16px 6px;
                }}
                h2 {{
                    font-size: 1.3rem;
                }}
                thead th, tbody td {{
                    padding: 8px 4px;
                    font-size: 0.95rem;
                }}
            }}
            footer {{
                text-align: center;
                color: #1976d2;
                margin: 30px 0 10px 0;
                font-size: 1em;
                opacity: 0.7;
            }}
        </style>
    </head>
    <body>
        <button class="volver-btn" type="button" onclick="window.location.href='/menu'" style="position:fixed;top:24px;left:24px;max-width:140px;z-index:1000;">
            <i class="fa fa-arrow-left"></i> Salir
        </button>
        <div class="container">
            <h2><i class="fa fa-user-graduate"></i> Detalle de Estudiante</h2>
    '''
    if mensaje_error:
        html += f'<div class="error-msg"><i class="fa fa-exclamation-triangle"></i> {mensaje_error}</div>'
    elif mostrar_formulario_agregar:
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="agregar" value="1">
            <p><label>Estudiante:</label>
                <select name="id_estudiante" required>
                    {opciones_estudiante_html()}
                </select>
            </p>
            <p><label>Observaciones:</label>
                <select name="observaciones" required>
                    <option value="activo">activo</option>
                    <option value="no activo">no activo</option>
                </select>
            </p>
            <p><label>Modalidad:</label>
                <select name="id_modalidad" required>
                    {opciones_modalidad_html()}
                </select>
            </p>
            <p><label>Estado de Pago:</label>
                <select name="estado_pago" required>
                    <option value="Pagado">Pagado</option>
                    <option value="No Pagado">No Pagado</option>
                </select>
            </p>
            <button type="submit" class="volver-btn"><i class="fa fa-plus"></i> Añadir</button>
            <button type="button" class="volver-btn" style="background:#e3f2fd;color:#1976d2;margin-top:10px;" onclick="window.history.back();"><i class="fa fa-arrow-left"></i> Volver atrás</button>
        </form>
        '''
    elif detalle:
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="editar" value="1">
            <input type="hidden" name="id_detalle" value="{detalle[0]}">
            <p><label>ID Detalle:</label> {detalle[0]}</p>
            <p><label>Estudiante:</label>
                <select name="id_estudiante" required>
                    {opciones_estudiante_html(detalle[1])}
                </select>
            </p>
            <p><label>Observaciones:</label>
                <select name="observaciones" required>
                    <option value="activo" {'selected' if detalle[2]=='activo' else ''}>activo</option>
                    <option value="no activo" {'selected' if detalle[2]=='no activo' else ''}>no activo</option>
                </select>
            </p>
            <p><label>Modalidad:</label>
                <select name="id_modalidad" required>
                    {opciones_modalidad_html(detalle[3])}
                </select>
            </p>
            <p><label>Estado de Pago:</label>
                <select name="estado_pago" required>
                    <option value="Pagado" {'selected' if detalle[4]=='Pagado' else ''}>Pagado</option>
                    <option value="No Pagado" {'selected' if detalle[4]=='No Pagado' else ''}>No Pagado</option>
                </select>
            </p>
            <button type="submit" class="volver-btn"><i class="fa fa-save"></i> Guardar Cambios</button>
            <button type="button" class="volver-btn" style="background:#e3f2fd;color:#1976d2;margin-top:10px;" onclick="window.history.back();"><i class="fa fa-arrow-left"></i> Volver atrás</button>
        </form>
        '''
    else:
        html += '''
        <a href="?accion=agregar" class="volver-btn" style="margin-bottom:20px;max-width:220px;">
            <i class="fa fa-plus"></i> Añadir
        </a>
        <table>
            <thead>
                <tr>
                    <th>ID Detalle</th>
                    <th>Estudiante</th>
                    <th>Observaciones</th>
                    <th>Modalidad</th>
                    <th>Estado de Pago</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
        '''
        for d in detalles:
            html += f'''
            <tr onclick="window.location='?id_detalle={d[0]}'" style="cursor:pointer">
                <td>{d[0]}</td>
                <td>{d[1]}</td>
                <td>{d[2]}</td>
                <td>{d[3]}</td>
                <td>{d[4]}</td>
                <td class="acciones">
                    <a href="?id_detalle={d[0]}" class="editar" title="Editar" onclick="event.stopPropagation()">
                        <i class="fa fa-pen"></i>
                    </a>
                    <a href="#" class="eliminar" title="Eliminar" onclick="event.stopPropagation(); if(confirm('¿Seguro que deseas eliminar este registro?')) window.location='?eliminar_id={d[0]}'">
                        <i class="fa fa-trash"></i>
                    </a>
                </td>
            </tr>
            '''
        html += '''
            </tbody>
        </table>
        '''
    html += '''
        </div>
        <footer>
            <i class="fa fa-graduation-cap"></i> Sistema de Gestión de Detalles de Estudiantes &copy; 2025
        </footer>
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