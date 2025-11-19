import os
import sys
from django.http import HttpResponse
from django.urls import path
import mysql.connector
from mysql.connector import Error
from django.conf import settings
import django
from django.core.management import execute_from_command_line

def crear_conexion(host_name, user_name, user_password, db_name):
    """Crea y retorna una conexión MySQL; retorna None si falla."""
    try:
        conexion = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        return conexion
    except Error as err:
        print(f"Error conexión MySQL: {err}")
        return None

def estudiante_view(request):
    mensaje_error = ""
    modalidades = []
    estudiantes = []

    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    if conexion is None:
        mensaje_error = "No se pudo conectar a la base de datos. Verifique la configuración."
    else:
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT id_modalidad, nombre_modalidad FROM Modalidades_Graduacion")
            modalidades = cursor.fetchall()

            if request.method == "POST":
                try:
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
                except Exception as e:
                    mensaje_error = "Ocurrió un error al procesar el formulario."
                    print("Error procesando POST:", e)

            cursor.execute("""
                SELECT e.id_estudiante, e.CI, e.RU, e.nombre, e.apellidos, e.correo, e.estado, m.nombre_modalidad
                FROM Estudiantes e
                LEFT JOIN Modalidades_Graduacion m ON e.id_modalidad = m.id_modalidad
            """)
            estudiantes = cursor.fetchall()
        except Exception as e:
            mensaje_error = "Error al consultar la base de datos."
            print("Error consulta:", e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conexion.close()
            except Exception:
                pass

    html = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gestión de Estudiantes</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            :root {{
                --primary: #0f3460; --primary-dark: #051e3e; --accent: #1e5a96;
                --muted: #6b7280; --success: #43a047; --danger: #ef5350;
                --bg: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                --shadow-lg: 0 8px 24px rgba(0,0,0,0.25);
            }}
            body {{
                font-family: 'Inter', sans-serif;
                background: var(--bg);
                color: #0a1929;
                min-height: 100vh;
                line-height: 1.6;
            }}
            .top-bar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                padding: 16px 28px;
                box-shadow: var(--shadow-lg);
                position: sticky;
                top: 0;
                z-index: 100;
                gap: 20px;
            }}
            .back-button {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(255,255,255,0.12);
                color: #fff;
                padding: 10px 18px;
                border-radius: 8px;
                border: 2px solid rgba(255,255,255,0.18);
                cursor: pointer;
                font-weight: 600;
                transition: all 0.25s;
            }}
            .back-button:hover {{ transform: translateX(-4px); background: rgba(255,255,255,0.18); }}
            .top-title {{
                color: #ffffff;
                font-size: 1.6rem;
                font-weight: 700;
                margin: 0;
                letter-spacing: 0.6px;
                text-align: right;
                flex: 1;
            }}
            .container {{
                max-width: 1200px;
                margin: 28px auto;
                padding: 24px;
            }}
            .action-buttons {{
                display: flex;
                justify-content: flex-end;
                margin-bottom: 20px;
                gap: 12px;
            }}
            .btn {{
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                font-weight: 700;
                color: white;
                background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
                box-shadow: 0 6px 18px rgba(15,52,96,0.18);
            }}
            .tabla-wrapper {{
                background: #ffffff;
                border-radius: 12px;
                box-shadow: var(--shadow-lg);
                overflow: hidden;
            }}
            table {{ width: 100%; border-collapse: collapse; }}
            thead {{ background: linear-gradient(135deg, #0f3460 0%, #1e5a96 100%); color: #fff; }}
            th {{ padding: 14px 12px; text-align: left; font-weight: 700; font-size: 0.9rem; }}
            td {{ padding: 12px; border-bottom: 1px solid #f0f2f5; font-size: 0.95rem; color: #0a1929; }}
            tr:hover td {{ background: #fbfdff; transform: translateY(0); }}
            .form-elegante {{ background: #fbfdff; padding: 18px; border-radius: 10px; border: 1px solid #eef2f7; margin-top: 18px; }}
            .form-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:12px; }}
            .form-row input, .form-row select {{ padding:10px 12px; border:1.5px solid #e6eef8; border-radius:8px; min-width:160px; }}
            .form-buttons {{ display:flex; gap:10px; justify-content:center; margin-top:12px; }}
            .btn-edit {{ background: linear-gradient(135deg, #6d4c41 0%, #8d5c41 100%); color: #fff; border-radius:8px; padding:8px 12px; }}
            .btn-delete {{ background: linear-gradient(135deg, #b71c1c 0%, #d71c1c 100%); color: #fff; border-radius:8px; padding:8px 12px; }}
            .error-msg {{ background: linear-gradient(90deg, #fee2e2 0%, #fecaca 100%); color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; font-weight:700; }}
            @media (max-width: 768px) {{
                .form-row {{ flex-direction: column; }}
                .top-title {{ text-align: center; }}
                .action-buttons {{ justify-content: center; }}
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">
            <button class="back-button" onclick="window.location.href='/menu'">
                <i class="fas fa-arrow-left"></i>
                Volver al Menú
            </button>
            <h1 class="top-title">Gestión de Estudiantes</h1>
        </div>

        <div class="container">
            <div class="action-buttons">
                <button class="btn" onclick="mostrarFormularioCrear()"><i class="fas fa-plus"></i> Crear Nuevo Registro</button>
            </div>

            <div class="tabla-wrapper">
                <div style="padding:18px;">
                    '''
    if mensaje_error:
        html += f'<div class="error-msg">{mensaje_error}</div>'

    html += '''
                    <table>
                        <thead>
                            <tr>
                                <th>CI</th>
                                <th>RU</th>
                                <th>Nombre</th>
                                <th>Apellido</th>
                                <th>Correo</th>
                                <th>Modalidad</th>
                                <th style="text-align:center;">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
    '''
    if estudiantes:
        for e in estudiantes:
            html += f'''
                            <tr>
                                <td>{e[1] or ""}</td>
                                <td>{e[2] or ""}</td>
                                <td>{e[3] or ""}</td>
                                <td>{e[4] or ""}</td>
                                <td>{e[5] or ""}</td>
                                <td>{e[7] or "N/A"}</td>
                                <td style="text-align:center;">
                                    <button class="btn-edit" onclick="mostrarFormularioActualizar()" title="Editar">✏️</button>
                                    <button class="btn-delete" onclick="mostrarFormularioEliminar()" title="Bloquear">🚫</button>
                                </td>
                            </tr>
            '''
    else:
        html += '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--muted);">No hay estudiantes registrados.</td></tr>'

    html += '''
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="form-elegante" id="forms-area">
                <form id="crear-form" method="post" style="display:none;">
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
                    <div class="form-buttons">
                        <button type="button" class="btn" onclick="ocultarFormularios()" style="background:#9e9e9e;">Cancelar</button>
                        <button type="submit" class="btn">Guardar</button>
                    </div>
                </form>

                <form id="actualizar-form" method="post" style="display:none;">
                    <h3>Actualizar Estudiante</h3>
                    <input type="hidden" name="csrfmiddlewaretoken" value="">
                    <input type="hidden" name="actualizar" value="1">
                    <div class="form-row">
                        <select id="estudiante-select" onchange="llenarFormularioActualizar()" required>
                            <option value="">Seleccione un estudiante</option>
    '''
    for e in estudiantes:
        html += f'<option value="{e[0]}|{e[1] or ""}|{e[2] or ""}|{e[3] or ""}|{e[4] or ""}|{e[5] or ""}|{e[6] or ""}|{e[7] or ""}">{e[3] or ""} {e[4] or ""}</option>'

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
                    <div class="form-buttons">
                        <button type="button" class="btn" onclick="ocultarFormularios()" style="background:#9e9e9e;">Cancelar</button>
                        <button type="submit" class="btn">Actualizar</button>
                    </div>
                </form>

                <form id="eliminar-form" method="post" style="display:none;">
                    <h3>Bloquear Estudiante</h3>
                    <input type="hidden" name="csrfmiddlewaretoken" value="">
                    <input type="hidden" name="eliminar" value="1">
                    <div class="form-row">
                        <select name="id_estudiante" required>
                            <option value="">Seleccione un estudiante</option>
    '''
    for e in estudiantes:
        html += f'<option value="{e[0]}">{e[3] or ""} {e[4] or ""}</option>'

    html += '''
                        </select>
                    </div>
                    <div class="form-buttons">
                        <button type="button" class="btn" onclick="ocultarFormularios()" style="background:#9e9e9e;">Cancelar</button>
                        <button type="submit" class="btn" style="background:linear-gradient(135deg,#b71c1c 0%,#d71c1c 100%);">Bloquear</button>
                    </div>
                </form>
            </div>
        </div>

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
            function ocultarFormularios() {{
                document.getElementById('crear-form').style.display = 'none';
                document.getElementById('actualizar-form').style.display = 'none';
                document.getElementById('eliminar-form').style.display = 'none';
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
            document.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach(function(input){{
                input.value = (document.cookie.match(/csrftoken=([^;]+)/)||[])[1]||'';
            }});
        </script>
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
