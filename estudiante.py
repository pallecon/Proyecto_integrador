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
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #e8eef7;
                min-height: 100vh;
            }}
            .header {{
                background: linear-gradient(90deg, #1e3a5f 0%, #2c5282 100%);
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 8px 24px rgba(0,0,0,0.3);
                position: sticky;
                top: 0;
                z-index: 100;
            }}
            .header-left {{
                display: flex;
                align-items: center;
                gap: 20px;
            }}
            .volver-btn {{
                background: rgba(255, 255, 255, 0.2);
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                border: 2px solid rgba(255, 255, 255, 0.4);
                font-weight: 600;
                cursor: pointer;
                font-size: 0.95rem;
                transition: all 0.3s;
            }}
            .volver-btn:hover {{
                background: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.6);
            }}
            .header h1 {{
                color: white;
                font-size: 2rem;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            .container {{
                max-width: 1400px;
                margin: 30px auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.15);
                overflow: hidden;
            }}
            .toolbar {{
                background: #e8eef7;
                padding: 30px 40px;
                display: flex;
                justify-content: flex-end;
                align-items: center;
                border-bottom: 1px solid #d1dce8;
                gap: 15px;
            }}
            .toolbar button {{
                padding: 12px 28px;
                font-size: 1rem;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                letter-spacing: 0.5px;
            }}
            .btn-crear {{
                background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
                color: white;
                border: 2px solid #3d5a7f;
            }}
            .btn-crear:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(30, 58, 95, 0.4);
                background: linear-gradient(135deg, #2c5282 0%, #1e3a5f 100%);
                border-color: #4a7ba7;
            }}
            .btn-editar {{
                background: #8b6f47;
                color: white;
                padding: 8px 12px;
                font-size: 1.1rem;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .btn-editar:hover {{
                transform: scale(1.1);
                background: #a0845a;
                box-shadow: 0 2px 8px rgba(139, 111, 71, 0.3);
            }}
            .btn-eliminar {{
                background: #c41e3a;
                color: white;
                padding: 8px 12px;
                font-size: 1.1rem;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .btn-eliminar:hover {{
                transform: scale(1.1);
                background: #a01830;
                box-shadow: 0 2px 8px rgba(196, 30, 58, 0.3);
            }}
            .content {{
                padding: 40px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th {{
                background: linear-gradient(90deg, #1e3a5f 0%, #2c5282 100%);
                color: white;
                padding: 18px;
                text-align: left;
                font-weight: 700;
                font-size: 0.95rem;
                letter-spacing: 0.5px;
                border: none;
            }}
            td {{
                padding: 16px 18px;
                border-bottom: 1px solid #e2e8f0;
                font-size: 0.95rem;
            }}
            tr:hover td {{
                background: #f5f7fc;
                transition: background 0.2s;
            }}
            .badge {{
                display: inline-block;
                padding: 6px 14px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 0.85rem;
                text-align: center;
            }}
            .badge-proceso {{
                background: #fca311;
                color: white;
                font-weight: 700;
            }}
            .badge-completado {{
                background: #4caf50;
                color: white;
                font-weight: 700;
            }}
            .badge-falta {{
                background: #fee2e2;
                color: #991b1b;
            }}
            .badge-habilitado {{
                background: #4caf50;
                color: white;
                font-weight: 700;
            }}
            .badge-no-habilitado {{
                background: #c41e3a;
                color: white;
                font-weight: 700;
            }}
            .actions {{
                display: flex;
                gap: 12px;
                justify-content: center;
                align-items: center;
            }}
            .empty-msg {{
                text-align: center;
                color: #6b7280;
                font-size: 1.1rem;
                padding: 60px 20px;
            }}
            #crear-form, #actualizar-form, #eliminar-form {{
                display: none;
                background: #f8fafc;
                border-radius: 12px;
                padding: 30px;
                margin-top: 20px;
                border: 2px solid #e2e8f0;
            }}
            #crear-form h3, #actualizar-form h3, #eliminar-form h3 {{
                color: #0f172a;
                margin-bottom: 25px;
                font-size: 1.3rem;
                font-weight: 700;
            }}
            .form-row {{
                display: flex;
                gap: 15px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }}
            #crear-form input, #crear-form select,
            #actualizar-form input, #actualizar-form select,
            #eliminar-form select {{
                flex: 1;
                min-width: 180px;
                padding: 12px 15px;
                border: 1.5px solid #cbd5e1;
                border-radius: 8px;
                font-size: 1rem;
                background: white;
                transition: all 0.3s;
                color: #1f2937;
            }}
            #crear-form input:focus, #actualizar-form input:focus, #crear-form select:focus, #actualizar-form select:focus {{
                border: 1.5px solid #1e293b;
                outline: none;
                box-shadow: 0 0 10px rgba(15, 23, 42, 0.2);
                background: white;
            }}
            #crear-form button, #actualizar-form button, #eliminar-form button {{
                padding: 12px 32px;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s;
                margin-top: 15px;
                letter-spacing: 0.5px;
            }}
            #crear-form button {{
                background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
                color: white;
                border: 2px solid #3d5a7f;
            }}
            #crear-form button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(30, 58, 95, 0.4);
                background: linear-gradient(135deg, #2c5282 0%, #1e3a5f 100%);
                border-color: #4a7ba7;
            }}
            #actualizar-form button {{
                background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
                color: white;
            }}
            #actualizar-form button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(30, 58, 95, 0.3);
                background: linear-gradient(135deg, #2c5282 0%, #1e3a5f 100%);
            }}
            #eliminar-form button {{
                background: #c41e3a;
                color: white;
            }}
            #eliminar-form button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(196, 30, 58, 0.3);
                background: #a01830;
            }}
            .error-msg {{
                background: linear-gradient(90deg, #fee2e2 0%, #fecaca 100%);
                color: #991b1b;
                padding: 16px 20px;
                border-radius: 8px;
                border-left: 4px solid #dc2626;
                font-weight: 600;
                margin-bottom: 20px;
            }}
            @media (max-width: 1024px) {{
                .header {{ padding: 15px 20px; }}
                .header h1 {{ font-size: 1.5rem; }}
                .toolbar {{ padding: 20px; flex-wrap: wrap; }}
                .content {{ padding: 20px; }}
                table {{ font-size: 0.85rem; }}
                .header {{ flex-direction: column; gap: 15px; }}
                .header-left {{ width: 100%; justify-content: space-between; }}
            }}
            @media (max-width: 768px) {{
                table {{ font-size: 0.75rem; }}
                td, th {{ padding: 10px; }}
                .form-row {{ flex-direction: column; gap: 0; }}
                .form-row input, .form-row select {{ width: 100%; }}
            }}
        </style>
        <script>
            function mostrarFormularioCrear() {{
                document.getElementById('crear-form').style.display = 'block';
                document.getElementById('actualizar-form').style.display = 'none';
                document.getElementById('eliminar-form').style.display = 'none';
                document.getElementById('crear-form').scrollIntoView({{ behavior: 'smooth' }});
            }}
            function mostrarFormularioActualizar() {{
                document.getElementById('actualizar-form').style.display = 'block';
                document.getElementById('crear-form').style.display = 'none';
                document.getElementById('eliminar-form').style.display = 'none';
                document.getElementById('actualizar-form').scrollIntoView({{ behavior: 'smooth' }});
            }}
            function mostrarFormularioEliminar() {{
                document.getElementById('eliminar-form').style.display = 'block';
                document.getElementById('crear-form').style.display = 'none';
                document.getElementById('actualizar-form').style.display = 'none';
                document.getElementById('eliminar-form').scrollIntoView({{ behavior: 'smooth' }});
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
        <div class="header">
            <div class="header-left">
                <button class="volver-btn" onclick="window.location.href='/menu'">← Volver al Menú</button>
            </div>
            <h1>Modalidad de Titulación</h1>
        </div>
        <div class="container">
            <div class="toolbar">
                <button class="btn-crear" onclick="mostrarFormularioCrear()">+ Crear Nuevo Registro</button>
            </div>
            <div class="content">
    '''
    if mensaje_error:
        html += f'<div class="error-msg">{mensaje_error}</div>'
    
    html += '''
                <table>
                    <tr>
                        <th>ESTUDIANTE</th>
                        <th>ETAPA</th>
                        <th>TUTOR</th>
                        <th>REVISOR</th>
                        <th>1RA ENTREGA</th>
                        <th>2DA ENTREGA</th>
                        <th>ESTADO</th>
                        <th>PRE DEFENSA</th>
                        <th>ACCIONES</th>
                    </tr>
    '''
    if estudiantes:
        for e in estudiantes:
            html += f'''
                    <tr>
                        <td>{e[3]} {e[4]}</td>
                        <td>{e[6]}</td>
                        <td>{e[1]}</td>
                        <td>{e[2]}</td>
                        <td>{e[5]}</td>
                        <td>{e[6]}</td>
                        <td><span class="badge badge-proceso">En proceso</span></td>
                        <td><span class="badge badge-no-habilitado">No Habilitado</span></td>
                        <td>
                            <div class="actions">
                                <button class="btn-editar" onclick="mostrarFormularioActualizar()" title="Editar">📝</button>
                                <button class="btn-eliminar" onclick="mostrarFormularioEliminar()" title="Bloquear">⛔</button>
                            </div>
                        </td>
                    </tr>
            '''
    else:
        html += '<tr><td colspan="9" class="empty-msg">No hay estudiantes registrados.</td></tr>'
    
    html += '''
                </table>
                <form id="crear-form" method="post">
                    <h3>Crear Nuevo Estudiante</h3>
                    <input type="hidden" name="csrfmiddlewaretoken" value="">
                    <div class="form-row">
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
                <form id="actualizar-form" method="post">
                    <h3>Actualizar Estudiante</h3>
                    <input type="hidden" name="csrfmiddlewaretoken" value="">
                    <input type="hidden" name="actualizar" value="1">
                    <div class="form-row">
                        <select id="estudiante-select" onchange="llenarFormularioActualizar()" required>
                            <option value="">Seleccione un estudiante</option>
    '''
    for e in estudiantes:
        html += f'<option value="{e[0]}|{e[1]}|{e[2]}|{e[3]}|{e[4]}|{e[5]}|{e[6]}|{e[7]}">{e[3]} {e[4]} (ID:{e[0]})</option>'
    
    html += '''
                        </select>
                    </div>
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
                <form id="eliminar-form" method="post">
                    <h3>Bloquear Estudiante</h3>
                    <input type="hidden" name="csrfmiddlewaretoken" value="">
                    <input type="hidden" name="eliminar" value="1">
                    <div class="form-row">
                        <select name="id_estudiante" required>
                            <option value="">Seleccione un estudiante</option>
    '''
    for e in estudiantes:
        html += f'<option value="{e[0]}">{e[3]} {e[4]} (ID:{e[0]})</option>'
    
    html += '''
                        </select>
                    </div>
                    <button type="submit">Bloquear</button>
                </form>
                <script>
                    document.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach(function(input){
                        input.value = (document.cookie.match(/csrftoken=([^;]+)/)||[])[1]||'';
                    });
                </script>
            </div>
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
    ]

    from django.urls import include
    settings.ROOT_URLCONF = __name__ 

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    execute_from_command_line([sys.argv[0], "runserver", "8000"])
