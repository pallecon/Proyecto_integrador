import os
import sys
from django.http import HttpResponse
from django.urls import path
import mysql.connector
from django.conf import settings
import django
from django.core.management import execute_from_command_line
from django.shortcuts import redirect

def crear_conexion(host_name, user_name, user_password, db_name):
    conexion = None
    try:
        conexion = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
    except mysql.connector.Error as err:
        print(f"Error: '{err}'")
    return conexion

def etapas_titulacion_view(request):
    mensaje_error = ""
    etapas = []
    etapa = None
    mostrar_formulario_agregar = False

    id_etapa = request.GET.get("id_etapa") or request.POST.get("id_etapa")
    accion = request.GET.get("accion") or request.POST.get("accion")

    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    cursor = conexion.cursor()

    cursor.execute("SELECT id_modalidad, nombre_modalidad FROM Modalidades_Graduacion")
    modalidades = cursor.fetchall()

    if request.method == "POST" and request.POST.get("agregar") == "1":
        nombre_etapa = request.POST.get("nombre_etapa")
        descripcion = request.POST.get("descripcion")
        id_modalidad = request.POST.get("id_modalidad")
        try:
            cursor.execute("""
                INSERT INTO Etapas_Titulacion (nombre_etapa, descripcion, id_modalidad)
                VALUES (%s, %s, %s)
            """, (nombre_etapa, descripcion, id_modalidad))
            conexion.commit()
            cursor.close()
            conexion.close()
            return redirect("/")
        except Exception as e:
            mensaje_error = f"Error al añadir: {e}"

    if request.method == "POST" and request.POST.get("editar") == "1":
        id_etapa = request.POST.get("id_etapa")
        nombre_etapa = request.POST.get("nombre_etapa")
        descripcion = request.POST.get("descripcion")
        id_modalidad = request.POST.get("id_modalidad")
        try:
            cursor.execute("""
                UPDATE Etapas_Titulacion
                SET nombre_etapa=%s, descripcion=%s, id_modalidad=%s
                WHERE id_etapa=%s
            """, (nombre_etapa, descripcion, id_modalidad, id_etapa))
            conexion.commit()
            cursor.close()
            conexion.close()
            return redirect("/")
        except Exception as e:
            mensaje_error = f"Error al editar: {e}"

    if request.method == "POST" and request.POST.get("eliminar") == "1":
        id_etapa = request.POST.get("id_etapa")
        try:
            cursor.execute("DELETE FROM Etapas_Titulacion WHERE id_etapa=%s", (id_etapa,))
            conexion.commit()
        except Exception as e:
            mensaje_error = f"Error al eliminar: {e}"

    if accion == "agregar":
        mostrar_formulario_agregar = True

    if id_etapa and not mostrar_formulario_agregar:
        cursor.execute("""
            SELECT id_etapa, nombre_etapa, descripcion, id_modalidad
            FROM Etapas_Titulacion
            WHERE id_etapa = %s
        """, (id_etapa,))
        etapa = cursor.fetchone()
        if not etapa:
            mensaje_error = "Etapa no encontrada."
    else:
        cursor.execute("""
            SELECT e.id_etapa, e.nombre_etapa, e.descripcion, m.nombre_modalidad
            FROM Etapas_Titulacion e
            JOIN Modalidades_Graduacion m ON e.id_modalidad = m.id_modalidad
        """)
        etapas = cursor.fetchall()
    cursor.close()
    conexion.close()

    def opciones_modalidad_html(selected=None):
        opciones = ""
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
        <title>Etapas de Titulación</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                font-family: 'Poppins', Arial, sans-serif;
                background: linear-gradient(135deg, #b3e0ff 0%, #e3f7ff 100%);
                color: #003366;
                min-height: 100vh;
            }}
            .top-bar {{
                width: 100%;
                text-align: left;
                margin-bottom: 10px;
            }}
            .btn.salir {{
                background: linear-gradient(90deg, #1976d2 0%, #2196f3 100%);
                color: #fff;
                margin-bottom: 30px;
                margin-left: 10px;
                border: none;
                border-radius: 12px;
                padding: 13px 32px;
                font-size: 1.08em;
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0 4px 16px #2196f355;
                transition: background 0.2s, transform 0.2s;
                display: inline-block;
                letter-spacing: 1px;
            }}
            .btn.salir:hover {{
                background: linear-gradient(90deg, #2196f3 0%, #1976d2 100%);
                color: #fff;
                transform: scale(1.05);
            }}
            .container {{
                max-width: 950px;
                margin: 48px auto 32px auto;
                background: #fff;
                border-radius: 24px;
                box-shadow: 0 10px 40px 0 #2196f344, 0 2px 8px #b3e0ff44;
                padding: 48px 36px 36px 36px;
                position: relative;
                animation: fadeIn 1s;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(40px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            h2 {{
                text-align: center;
                color: #1976d2;
                margin-bottom: 32px;
                font-size: 2.3em;
                font-weight: 900;
                letter-spacing: 2px;
                text-shadow: 0 2px 18px #b3e0ff44;
            }}
            table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                margin-bottom: 32px;
                border-radius: 18px;
                overflow: hidden;
                background: #e3f7ff;
                box-shadow: 0 2px 16px #2196f322;
            }}
            th {{
                background: linear-gradient(90deg, #1976d2 0%, #2196f3 100%);
                color: #fff;
                padding: 16px 10px;
                font-size: 1.13em;
                font-weight: 700;
                border: none;
                letter-spacing: 1px;
            }}
            td {{
                padding: 15px 10px;
                background: #e3f7ff;
                text-align: center;
                font-size: 1.05em;
                border-bottom: 1px solid #b3e0ff;
                transition: background 0.2s;
                color: #003366;
            }}
            tr:last-child td {{
                border-bottom: none;
            }}
            tr:nth-child(even) td {{
                background-color: #b3e0ff;
            }}
            tr:hover td {{
                background-color: #90caf9;
            }}
            .detalle {{
                background: #fafdff;
                padding: 32px 28px 22px 28px;
                border-radius: 18px;
                box-shadow: 0 4px 24px #2196f322;
                margin-bottom: 32px;
                max-width: 600px;
                margin-left: auto;
                margin-right: auto;
                animation: fadeInDown 0.7s;
            }}
            @keyframes fadeInDown {{
                from {{ opacity:0; transform:translateY(-40px); }}
                to {{ opacity:1; transform:translateY(0); }}
            }}
            .detalle label {{
                font-weight: 700;
                display: block;
                margin-bottom: 7px;
                color: #1976d2;
                font-size: 1.13em;
                letter-spacing: 0.5px;
            }}
            .detalle input[type="text"],
            .detalle textarea,
            .detalle select {{
                width: 100%;
                padding: 13px;
                margin-bottom: 18px;
                border: 1.5px solid #90caf9;
                border-radius: 10px;
                font-size: 1.05em;
                background: #fafdff;
                transition: border 0.2s, box-shadow 0.2s;
                color: #003366;
                box-shadow: 0 2px 8px #90caf933;
            }}
            .detalle input[type="text"]:focus,
            .detalle textarea:focus,
            .detalle select:focus {{
                border: 1.5px solid #1976d2;
                outline: none;
                box-shadow: 0 0 0 2px #b3e0ff55;
            }}
            .btn, .add-btn {{
                display: inline-block;
                padding: 14px 36px;
                background: linear-gradient(90deg, #1976d2 0%, #2196f3 100%);
                color: white;
                text-decoration: none;
                border-radius: 14px;
                font-weight: bold;
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 16px #2196f355;
                transition: transform 0.2s, background 0.2s, box-shadow 0.2s;
                text-align: center;
                font-size: 1.13em;
                margin-bottom: 18px;
                margin-right: 10px;
            }}
            .btn:hover, .add-btn:hover {{
                background: linear-gradient(90deg, #2196f3 0%, #1976d2 100%);
                transform: scale(1.06);
                box-shadow: 0 8px 32px #2196f355;
            }}
            .btn.cancel {{
                background: #e3f7ff;
                color: #1976d2;
                border: 1.5px solid #90caf9;
                margin-left: 10px;
            }}
            .btn.cancel:hover {{
                background: #b3e0ff;
                color: #1976d2;
            }}
            .btn.delete {{
                background: #e74c3c;
                color: #fff;
                padding: 9px 22px;
                font-size: 1em;
                margin-top: 4px;
                border-radius: 8px;
                font-weight: 700;
                box-shadow: none;
            }}
            .btn.delete:hover {{
                background: #c0392b;
            }}
            .add-btn {{
                margin-bottom: 28px;
                margin-top: 10px;
                font-size: 1.13em;
                font-weight: bold;
                background: linear-gradient(90deg, #2196f3 0%, #1976d2 100%);
                animation: pulse 1.2s infinite alternate;
            }}
            @keyframes pulse {{
                from {{ box-shadow: 0 0 0 0 #90caf933; }}
                to {{ box-shadow: 0 0 16px 8px #2196f333; }}
            }}
            .table-actions a, .table-actions form {{
                display: inline-block;
                margin: 0 2px;
            }}
            .table-actions a {{
                color: #1976d2;
                font-weight: 700;
                text-decoration: underline;
                cursor: pointer;
                font-size: 1.07em;
            }}
            .table-actions a:hover {{
                color: #2196f3;
            }}
            .error-msg {{
                background: #e74c3c;
                color: white;
                padding: 16px;
                text-align: center;
                border-radius: 12px;
                margin-bottom: 24px;
                font-weight: 600;
                box-shadow: 0 4px 12px #e74c3c33;
                font-size: 1.13em;
                letter-spacing: 0.5px;
            }}
            /* Responsive */
            @media (max-width: 900px) {{
                .container {{ padding: 18px 4vw 18px 4vw; }}
                h2 {{ font-size: 1.5em; }}
                table, th, td {{ font-size: 1em; }}
            }}
            @media (max-width: 600px) {{
                .container {{ padding: 8px 2vw 8px 2vw; }}
                .detalle {{ padding: 12px 6px 8px 6px; }}
                th, td {{ padding: 7px 2px; font-size: 0.97em; }}
                .btn, .add-btn {{ font-size: 1em; padding: 8px 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">
            <a href="/menu" class="btn salir">&#8592; Salir</a>
        </div>
        <div class="container">
            <h2>Etapas de Titulación</h2>
    '''
    if mensaje_error:
        html += f'<div class="error-msg">{mensaje_error}</div>'
    elif mostrar_formulario_agregar:
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="agregar" value="1">
            <p><label>Nombre de la Etapa:</label>
                <input type="text" name="nombre_etapa" required>
            </p>
            <p><label>Descripción:</label>
                <textarea name="descripcion" required></textarea>
            </p>
            <p><label>Modalidad:</label>
                <select name="id_modalidad" required>
                    {opciones_modalidad_html()}
                </select>
            </p>
            <button type="submit" class="btn">Añadir</button>
            <button type="button" class="btn cancel" onclick="window.history.back();">Cancelar</button>
        </form>
        '''
    elif etapa:
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="editar" value="1">
            <input type="hidden" name="id_etapa" value="{etapa[0]}">
            <p><label>ID Etapa:</label> {etapa[0]}</p>
            <p><label>Nombre de la Etapa:</label>
                <input type="text" name="nombre_etapa" value="{etapa[1]}" required>
            </p>
            <p><label>Descripción:</label>
                <textarea name="descripcion" required>{etapa[2]}</textarea>
            </p>
            <p><label>Modalidad:</label>
                <select name="id_modalidad" required>
                    {opciones_modalidad_html(etapa[3])}
                </select>
            </p>
            <button type="submit" class="btn">Guardar Cambios</button>
            <button type="button" class="btn cancel" onclick="window.history.back();">Cancelar</button>
        </form>
        '''
    else:
        html += '''
        <a href="?accion=agregar" class="add-btn">+ Añadir Nueva Etapa</a>
        <form method="post">
        <table>
            <thead>
                <tr>
                    <th>ID Etapa</th>
                    <th>Nombre Etapa</th>
                    <th>Descripción</th>
                    <th>Modalidad</th>
                    <th colspan="2">Acciones</th>
                </tr>
            </thead>
            <tbody>
        '''
        for e in etapas:
            html += f'''
            <tr>
                <td>{e[0]}</td>
                <td>{e[1]}</td>
                <td>{e[2]}</td>
                <td>{e[3]}</td>
                <td class="table-actions">
                    <a href="?id_etapa={e[0]}">Editar</a>
                </td>
                <td class="table-actions">
                    <form method="post" style="display:inline;" onsubmit="return confirm('¿Seguro que deseas eliminar esta etapa?');">
                        <input type="hidden" name="eliminar" value="1">
                        <input type="hidden" name="id_etapa" value="{e[0]}">
                        <button type="submit" class="btn delete">Eliminar</button>
                    </form>
                </td>
            </tr>
            '''
        html += '''
            </tbody>
        </table>
        </form>
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
            MIDDLEWARE = [],
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
            USE_TZ = True,
            TIME_ZONE = 'America/La_Paz',
        )
    django.setup()
    urlpatterns = [
        path('', etapas_titulacion_view),
        path('etapas_titulacion', etapas_titulacion_view), 
        path('etapas_titulacion/', etapas_titulacion_view),
    ]

    from django.urls import include
    settings.ROOT_URLCONF = __name__

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    execute_from_command_line([sys.argv[0], "runserver", "8000"])