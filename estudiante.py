
import os
import sys
from django.http import HttpResponse
from django.urls import path
import mysql.connector
from django.conf import settings
import django
from django.core.management import execute_from_command_line
from django.http import HttpResponse
def crear_conexion(host_name, user_name, user_password, db_name):
    """
    Crea una conexión a la base de datos MySQL.
    """
    conexion = None
    try:
        conexion = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("Conexión a MySQL exitosa")
    except mysql.connector.Error as err:
        print(f"Error: '{err}'")

    return conexion

def estudiante_view(request):
    mensaje_error = ""
    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    cursor = conexion.cursor()
    cursor.execute("SELECT id_modalidad, nombre_modalidad FROM Modalidades_Graduacion")
    modalidades = cursor.fetchall()

    if request.method == "POST":
        if request.POST.get("actualizar") == "1":
            id_estudiante = request.POST.get("id_estudiante")
            ci = request.POST.get("ci")
            ru = request.POST.get("ru")
            nombre = request.POST.get("nombre")
            apellidos = request.POST.get("apellidos")
            correo = request.POST.get("correo")
            estado = request.POST.get("estado")
            id_modalidad = request.POST.get("id_modalidad")
            cursor.execute("""
                UPDATE Estudiantes
                SET CI=%s, RU=%s, nombre=%s, apellidos=%s, correo=%s, estado=%s, id_modalidad=%s
                WHERE id_estudiante=%s
            """, (ci, ru, nombre, apellidos, correo, estado, id_modalidad, id_estudiante))
            conexion.commit()
        elif request.POST.get("eliminar") == "1":
            id_estudiante = request.POST.get("id_estudiante")
            cursor.execute("DELETE FROM Estudiantes WHERE id_estudiante=%s", (id_estudiante,))
            conexion.commit()
        else:
            ci = request.POST.get("ci")
            ru = request.POST.get("ru")
            nombre = request.POST.get("nombre")
            apellidos = request.POST.get("apellidos")
            correo = request.POST.get("correo")
            estado = request.POST.get("estado")
            id_modalidad = request.POST.get("id_modalidad")
            try:
                cursor.execute("""
                    INSERT INTO Estudiantes (CI, RU, nombre, apellidos, correo, estado, id_modalidad)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (ci, ru, nombre, apellidos, correo, estado, id_modalidad))
                conexion.commit()
            except mysql.connector.IntegrityError:
                mensaje_error = "Error: El CI ingresado ya existe."

    cursor.execute("""
        SELECT e.id_estudiante, e.CI, e.RU, e.nombre, e.apellidos, e.correo, e.estado, m.nombre_modalidad
        FROM Estudiantes e
        LEFT JOIN Modalidades_Graduacion m ON e.id_modalidad = m.id_modalidad
    """)
    estudiantes = cursor.fetchall()
    cursor.close()
    conexion.close()

    html = f'''
    <html>
    <head>
        <title>Lista de Estudiantes</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #1565c0 0%, #42a5f5 100%);
                margin: 0;
                padding: 0;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1100px;
                margin: 40px auto;
                background: rgba(255,255,255,0.98);
                border-radius: 28px;
                box-shadow: 0 16px 40px 0 rgba(21,101,192,0.16), 0 2px 8px rgba(0,0,0,0.07);
                padding: 48px 56px 56px 56px;
                position: relative;
                overflow: hidden;
            }}
            .container::before {{
                content: "";
                position: absolute;
                top: -80px; left: -80px;
                width: 300px; height: 300px;
                background: radial-gradient(circle, #42a5f5 0%, #1565c0 80%, transparent 100%);
                opacity: 0.13;
                z-index: 0;
            }}
            h2 {{
                text-align: center;
                color: #1565c0;
                margin-bottom: 32px;
                letter-spacing: 2px;
                font-weight: 900;
                font-size: 2.5rem;
                text-shadow: 0 4px 16px #90caf9;
                position: relative;
                z-index: 1;
            }}
            .action-buttons {{
                display: flex;
                justify-content: center;
                gap: 22px;
                margin-bottom: 36px;
                position: relative;
                z-index: 1;
            }}
            .action-buttons button {{
                padding: 16px 44px;
                font-size: 1.18em;
                border-radius: 14px;
                border: none;
                background: linear-gradient(90deg, #1565c0 60%, #42a5f5 100%);
                color: #fff;
                font-weight: 800;
                cursor: pointer;
                box-shadow: 0 2px 12px #90caf980;
                transition: background 0.2s, transform 0.1s, box-shadow 0.2s;
                letter-spacing: 1px;
            }}
            .action-buttons button:hover {{
                background: linear-gradient(90deg, #0d47a1 60%, #1976d2 100%);
                transform: translateY(-2px) scale(1.07);
                box-shadow: 0 8px 24px #90caf980;
            }}
            table {{
                border-collapse: separate;
                border-spacing: 0 10px;
                width: 100%;
                background: #f7fbff;
                border-radius: 18px;
                overflow: hidden;
                margin-bottom: 36px;
                box-shadow: 0 2px 16px #90caf930;
                position: relative;
                z-index: 1;
            }}
            th, td {{
                border: none;
                padding: 16px 12px;
                text-align: center;
            }}
            th {{
                background: linear-gradient(90deg, #1565c0 0%, #42a5f5 100%);
                color: #fff;
                font-size: 1.13em;
                letter-spacing: 0.7px;
                font-weight: 800;
            }}
            tr:nth-child(even) {{
                background: #e3f2fd;
            }}
            tr:hover td {{
                background: #bbdefb;
                transition: background 0.2s;
            }}
            .empty-msg {{
                text-align: center;
                color: #1976d2;
                font-size: 1.2em;
                margin: 30px 0 20px 0;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            form {{
                margin-top: 18px;
            }}
            #crear-form, #actualizar-form, #eliminar-form {{
                display: none;
                background: #e3f2fd;
                border-radius: 18px;
                box-shadow: 0 2px 12px #90caf950;
                padding: 32px 22px 22px 22px;
                margin: 0 auto 22px auto;
                max-width: 700px;
                position: relative;
                z-index: 2;
            }}
            #crear-form h3, #actualizar-form h3, #eliminar-form h3 {{
                color: #1565c0;
                margin-bottom: 20px;
                text-align: center;
                font-weight: 900;
                letter-spacing: 1.2px;
                font-size: 1.3em;
            }}
            #crear-form input, #crear-form select,
            #actualizar-form input, #actualizar-form select,
            #eliminar-form select {{
                margin: 9px 8px;
                padding: 12px 16px;
                border-radius: 9px;
                border: 1.5px solid #90caf9;
                font-size: 1.07em;
                background: #fff;
                transition: border 0.2s, box-shadow 0.2s;
                color: #1565c0;
                font-weight: 600;
            }}
            #crear-form input:focus, #actualizar-form input:focus, #crear-form select:focus, #actualizar-form select:focus {{
                border: 1.5px solid #1565c0;
                outline: none;
                box-shadow: 0 0 8px #42a5f580;
            }}
            #crear-form button, #actualizar-form button {{
                background: linear-gradient(90deg, #2ecc40 60%, #27ae60 100%);
                color: #fff;
                border: none;
                padding: 14px 36px;
                border-radius: 11px;
                font-size: 1.09em;
                font-weight: 800;
                margin-top: 16px;
                cursor: pointer;
                transition: background 0.2s, transform 0.1s;
                box-shadow: 0 2px 10px #27ae6040;
                letter-spacing: 0.7px;
            }}
            #crear-form button:hover, #actualizar-form button:hover {{
                background: linear-gradient(90deg, #27ae38 60%, #229954 100%);
                transform: scale(1.07);
            }}
            #eliminar-form button {{
                background: linear-gradient(90deg, #e74c3c 60%, #c0392b 100%);
                color: #fff;
                border: none;
                padding: 14px 36px;
                border-radius: 11px;
                font-size: 1.09em;
                font-weight: 800;
                margin-top: 16px;
                cursor: pointer;
                transition: background 0.2s, transform 0.1s;
                box-shadow: 0 2px 10px #c0392b40;
                letter-spacing: 0.7px;
            }}
            #eliminar-form button:hover {{
                background: linear-gradient(90deg, #c0392b 60%, #a93226 100%);
                transform: scale(1.07);
            }}
            .error-msg {{
                color: #fff;
                background: linear-gradient(90deg, #e74c3c 60%, #c0392b 100%);
                padding: 16px;
                border-radius: 12px;
                width: 95%;
                margin: 24px auto 0 auto;
                text-align: center;
                font-size: 1.17em;
                box-shadow: 0 2px 10px #c0392b40;
                font-weight: 800;
                letter-spacing: 0.7px;
            }}
            .form-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                justify-content: center;
            }}
            .form-row input, .form-row select {{
                flex: 1 1 180px;
                min-width: 120px;
            }}
            @media (max-width: 900px) {{
                .container {{ padding: 10px 2vw; }}
                table, th, td {{ font-size: 0.97em; }}
                #crear-form, #actualizar-form, #eliminar-form {{ max-width: 98vw; }}
            }}
            @media (max-width: 600px) {{
                .container {{ padding: 2vw 1vw; }}
                h2 {{ font-size: 1.3rem; }}
                .action-buttons button {{ padding: 10px 12px; font-size: 1em; }}
                #crear-form, #actualizar-form, #eliminar-form {{ padding: 10px 2vw; }}
                .form-row {{ flex-direction: column; gap: 0; }}
            }}
        </style>
        <script>
            function mostrarFormularioCrear() {{
                document.getElementById('crear-form').style.display = 'block';
                document.getElementById('actualizar-form').style.display = 'none';
                document.getElementById('eliminar-form').style.display = 'none';
                window.scrollTo(0, document.body.scrollHeight);
            }}
            function mostrarFormularioActualizar() {{
                document.getElementById('actualizar-form').style.display = 'block';
                document.getElementById('crear-form').style.display = 'none';
                document.getElementById('eliminar-form').style.display = 'none';
                window.scrollTo(0, document.body.scrollHeight);
            }}
            function mostrarFormularioEliminar() {{
                document.getElementById('eliminar-form').style.display = 'block';
                document.getElementById('crear-form').style.display = 'none';
                document.getElementById('actualizar-form').style.display = 'none';
                window.scrollTo(0, document.body.scrollHeight);
            }}
            function llenarFormularioActualizar() {{
                var select = document.getElementById('estudiante-select');
                var datos = select.value.split('|');
                document.getElementById('upd_id').value = datos[0];
                document.getElementById('upd_ci').value = datos[1];
                document.getElementById('upd_ru').value = datos[2];
                document.getElementById('upd_nombre').value = datos[3];
                document.getElementById('upd_apellidos').value = datos[4];
                document.getElementById('upd_correo').value = datos[5];
                document.getElementById('upd_estado').value = datos[6];

                // Seleccionar la modalidad correcta en el select
                var modalidadSelect = document.getElementById('upd_id_modalidad');
                for (var i = 0; i < modalidadSelect.options.length; i++) {{
                    if (modalidadSelect.options[i].text === datos[7]) {{
                        modalidadSelect.selectedIndex = i;
                        break;
                    }}
                }}
            }}
        </script>
    </head>
    <body>
    <button class="volver-btn" type="button" onclick="window.location.href='/menu'" 
        style="
            position:fixed;
            top:24px;
            left:24px;
            max-width:140px;
            z-index:1000;
            padding: 14px 0;
            width: 120px;
            background: linear-gradient(90deg, #1565c0 0%, #42a5f5 100%);
            color: white;
            font-weight: 800;
            border-radius: 28px;
            box-shadow: 0 8px 28px rgba(21,101,192,0.18);
            border: none;
            font-size: 1rem;
            letter-spacing: 0.04em;
            cursor: pointer;
            transition: background 0.3s, transform 0.2s, box-shadow 0.2s;
        "
        onmouseover="this.style.background='linear-gradient(90deg, #42a5f5 0%, #1565c0 100%)'; this.style.transform='translateY(-3px) scale(1.04)';"
        onmouseout="this.style.background='linear-gradient(90deg, #1565c0 0%, #42a5f5 100%)'; this.style.transform='none';"
    >Salir</button>
    <div class="container" style="margin-top:40px;">
        <h2>Lista de Estudiantes</h2>
        <div class="action-buttons">
            <button onclick="mostrarFormularioCrear()">Crear</button>
            <button onclick="mostrarFormularioActualizar()">Actualizar</button>
            <button onclick="mostrarFormularioEliminar()">Eliminar</button>
        </div>
        <table>
            <tr>
                <th>ID</th>
                <th>CI</th>
                <th>RU</th>
                <th>Nombre</th>
                <th>Apellidos</th>
                <th>Correo</th>
                <th>Estado</th>
                <th>Modalidad</th>
            </tr>
    '''
    if estudiantes:
        for e in estudiantes:
            html += f'''
                <tr>
                    <td>{e[0]}</td>
                    <td>{e[1]}</td>
                    <td>{e[2]}</td>
                    <td>{e[3]}</td>
                    <td>{e[4]}</td>
                    <td>{e[5]}</td>
                    <td>{e[6]}</td>
                    <td>{e[7] if e[7] else "-"}</td>
                </tr>
            '''
    else:
        html += '<tr><td colspan="8" class="empty-msg">No hay estudiantes registrados.</td></tr>'
    html += '''
        </table>
        <form id="crear-form" method="post" >
            <h3>Crear Nuevo Estudiante</h3>
            <div class="form-row">
                <input type="hidden" name="csrfmiddlewaretoken" value="">
                <input type="text" name="ci" placeholder="CI" required>
                <input type="text" name="ru" placeholder="RU" required>
                <input type="text" name="nombre" placeholder="Nombre" required>
                <input type="text" name="apellidos" placeholder="Apellidos" required>
            </div>
            <div class="form-row">
                <input type="email" name="correo" placeholder="Correo" required>
                <select name="estado" required>
                    <option value="">Estado</option>
                    <option value="activo">Activo</option>
                    <option value="inactivo">Inactivo</option>
                    <option value="egresado">Egresado</option>
                </select>
                <select name="id_modalidad" required>
                    <option value="">Modalidad</option>
    '''
    for m in modalidades:
        html += f'<option value="{m[0]}">{m[1]}</option>'
    html += '''
                </select>
            </div>
            <button type="submit">Guardar</button>
        </form>
    '''
    html += '''
        <form id="actualizar-form" method="post" >
            <h3>Actualizar Estudiante</h3>
            <div class="form-row">
                <input type="hidden" name="csrfmiddlewaretoken" value="">
                <select id="estudiante-select" onchange="llenarFormularioActualizar()" required>
                    <option value="">Seleccione un estudiante</option>
    '''
    for e in estudiantes:
        html += f'<option value="{e[0]}|{e[1]}|{e[2]}|{e[3]}|{e[4]}|{e[5]}|{e[6]}|{e[7]}">{e[3]} {e[4]} (ID:{e[0]}) - {e[7] if e[7] else "Sin modalidad"}</option>'
    html += '''
                </select>
            </div>
            <input type="hidden" name="actualizar" value="1">
            <input type="hidden" id="upd_id" name="id_estudiante">
            <div class="form-row">
                <input type="text" id="upd_ci" name="ci" placeholder="CI" required>
                <input type="text" id="upd_ru" name="ru" placeholder="RU" required>
                <input type="text" id="upd_nombre" name="nombre" placeholder="Nombre" required>
                <input type="text" id="upd_apellidos" name="apellidos" placeholder="Apellidos" required>
            </div>
            <div class="form-row">
                <input type="email" id="upd_correo" name="correo" placeholder="Correo" required>
                <select id="upd_estado" name="estado" required>
                    <option value="">Estado</option>
                    <option value="activo">Activo</option>
                    <option value="inactivo">Inactivo</option>
                    <option value="egresado">Egresado</option>
                </select>
                <select id="upd_id_modalidad" name="id_modalidad" required>
                    <option value="">Modalidad</option>
    '''
    for m in modalidades:
        html += f'<option value="{m[0]}">{m[1]}</option>'
    html += '''
                </select>
            </div>
            <button type="submit">Actualizar</button>
        </form>
    '''
    html += '''
        <form id="eliminar-form" method="post">
            <h3>Eliminar Estudiante</h3>
            <div class="form-row">
                <input type="hidden" name="csrfmiddlewaretoken" value="">
                <input type="hidden" name="eliminar" value="1">
                <select name="id_estudiante" required>
                    <option value="">Seleccione un estudiante</option>
    '''
    for e in estudiantes:
        html += f'<option value="{e[0]}">{e[3]} {e[4]} (ID:{e[0]})</option>'
    html += '''
                </select>
            </div>
            <button type="submit">Eliminar</button>
        </form>
        '''
    if mensaje_error:
        html += f'<div class="error-msg">{mensaje_error}</div>'
    html += '''
        <script>
            // CSRF para Django (solo si usas CSRF en settings)
            document.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach(function(input){
                input.value = (document.cookie.match(/csrftoken=([^;]+)/)||[])[1]||'';
            });
        </script>
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
        path('', estudiante_view),
        path('estudiantes/', estudiante_view),
        path('crear_estudiante/', lambda request: HttpResponse('<h1>Página para crear estudiante</h1>')),
        path('actualizar_estudiante/', lambda request: HttpResponse('<h1>Página para actualizar estudiante</h1>')),
        path('eliminar_estudiante/', lambda request: HttpResponse('<h1>Página para eliminar estudiante</h1>')),
    ]

    from django.urls import include
    settings.ROOT_URLCONF = __name__ 

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    execute_from_command_line([sys.argv[0], "runserver", "8000"])
