import os
import sys
from django.http import HttpResponse, HttpResponseRedirect  
from django.urls import path
import mysql.connector
from django.conf import settings
import django
from django.core.management import execute_from_command_line

def crear_conexion(host_name, user_name, user_password, db_name):
    conexion = None
    try:
        conexion = mysql.connector.connect(
            host=host_name,
            port=3306,  
            user=user_name,
            passwd=user_password,
            database=db_name
        )
    except mysql.connector.Error as err:
        print(f"Error: '{err}'")
    return conexion

def modalidad_view(request):
    mensaje_error = ""
    modalidades = []
    modalidad = None
    mostrar_formulario_agregar = False

    id_modalidad = request.GET.get("id_modalidad") or request.POST.get("id_modalidad")
    accion = request.GET.get("accion") or request.POST.get("accion")

    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    if not conexion:
        return HttpResponse("<h2 style='color:red'>No se pudo conectar a la base de datos. Verifica que exista 'modalidades_graduacion'.</h2>")
    cursor = conexion.cursor()

    if request.method == "POST" and request.POST.get("agregar") == "1":
        nombre_modalidad = request.POST.get("nombre_modalidad")
        descripcion = request.POST.get("descripcion")
        try:
            cursor.execute("""
                INSERT INTO Modalidades_Graduacion (nombre_modalidad, descripcion)
                VALUES (%s, %s)
            """, (nombre_modalidad, descripcion))
            conexion.commit()
            cursor.close()
            conexion.close()
            return HttpResponseRedirect(request.path)  
        except Exception as e:
            mensaje_error = f"Error al añadir: {e}"

    if request.method == "POST" and request.POST.get("editar") == "1":
        id_modalidad = request.POST.get("id_modalidad")
        nombre_modalidad = request.POST.get("nombre_modalidad")
        descripcion = request.POST.get("descripcion")
        try:
            cursor.execute("""
                UPDATE Modalidades_Graduacion
                SET nombre_modalidad=%s, descripcion=%s
                WHERE id_modalidad=%s
            """, (nombre_modalidad, descripcion, id_modalidad))
            conexion.commit()
            cursor.close()
            conexion.close()
            return HttpResponseRedirect(request.path)
        except Exception as e:
            mensaje_error = f"Error al editar: {e}"

    if request.method == "POST" and request.POST.get("eliminar") == "1":
        id_modalidad = request.POST.get("id_modalidad")
        try:
            cursor.execute("DELETE FROM Modalidades_Graduacion WHERE id_modalidad=%s", (id_modalidad,))
            conexion.commit()
            cursor.close()
            conexion.close()
            return HttpResponse("eliminado")
        except Exception as e:
            return HttpResponse("error")

    if accion == "agregar":
        mostrar_formulario_agregar = True

    if id_modalidad and not mostrar_formulario_agregar:
        cursor.execute("""
            SELECT id_modalidad, nombre_modalidad, descripcion
            FROM Modalidades_Graduacion
            WHERE id_modalidad = %s
        """, (id_modalidad,))
        modalidad = cursor.fetchone()
        if not modalidad:
            mensaje_error = "Modalidad no encontrada."
    else:
        cursor.execute("""
            SELECT id_modalidad, nombre_modalidad, descripcion
            FROM Modalidades_Graduacion
        """)
        modalidades = cursor.fetchall()
    cursor.close()
    conexion.close()

    html = f'''
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Modalidades de Graduación</title>
        <style>
            body {{
                margin: 0;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(120deg, #1565c0 0%, #42a5f5 100%);
                color: #333;
                min-height: 100vh;
            }}
            .container {{
                max-width: 800px;
                margin: 50px auto;
                background: #fff;
                border-radius: 28px;
                box-shadow: 0 16px 40px 0 rgba(21,101,192,0.16), 0 2px 8px rgba(0,0,0,0.07);
                padding: 48px 56px 56px 56px;
                position: relative;
                overflow: hidden;
            }}
            h2 {{
                text-align: center;
                color: #1565c0;
                margin-bottom: 32px;
                font-size: 2.3rem;
                font-weight: 900;
                letter-spacing: 2px;
                text-shadow: 0 4px 16px #90caf9;
            }}
            .modalidad-btns {{
                display: flex;
                justify-content: flex-end;
                margin-bottom: 24px;
                gap: 12px;
            }}
            .modalidad-btns a, .modalidad-btns button {{
                background: linear-gradient(90deg, #1565c0 60%, #42a5f5 100%);
                color: #fff;
                border: none;
                border-radius: 12px;
                padding: 12px 32px;
                font-weight: 800;
                font-size: 1.08em;
                text-decoration: none;
                cursor: pointer;
                box-shadow: 0 2px 12px #90caf980;
                transition: background 0.2s, transform 0.1s, box-shadow 0.2s;
                letter-spacing: 1px;
                display: inline-block;
            }}
            .modalidad-btns a:hover, .modalidad-btns button:hover {{
                background: linear-gradient(90deg, #0d47a1 60%, #1976d2 100%);
                transform: translateY(-2px) scale(1.05);
                box-shadow: 0 8px 24px #90caf980;
            }}
            table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0 10px;
                background: #f7fbff;
                border-radius: 18px;
                overflow: hidden;
                margin-bottom: 36px;
                box-shadow: 0 2px 16px #90caf930;
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
            tr:nth-child(even) td {{
                background: #e3f2fd;
            }}
            tr:hover td {{
                background: #bbdefb;
                transition: background 0.2s;
            }}
            .detalle {{
                background: #e3f2fd;
                padding: 32px 22px 22px 22px;
                border-radius: 18px;
                box-shadow: 0 2px 12px #90caf950;
                margin-bottom: 30px;
                position: relative;
                z-index: 2;
            }}
            .detalle label {{
                font-weight: 700;
                color: #1565c0;
                margin-bottom: 8px;
                display: block;
                letter-spacing: 0.5px;
            }}
            .detalle input[type="text"],
            .detalle textarea {{
                width: 100%;
                padding: 12px 16px;
                margin-bottom: 18px;
                border-radius: 9px;
                border: 1.5px solid #90caf9;
                font-size: 1.07em;
                background: #fff;
                color: #1565c0;
                font-weight: 600;
                transition: border 0.2s, box-shadow 0.2s;
            }}
            .detalle input:focus, .detalle textarea:focus {{
                border: 1.5px solid #1565c0;
                outline: none;
                box-shadow: 0 0 8px #42a5f580;
            }}
            .volver-btn {{
                display: inline-block;
                padding: 12px 28px;
                background: linear-gradient(90deg, #1565c0, #42a5f5);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: bold;
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(21,101,192,0.13);
                transition: transform 0.2s, background 0.2s;
                text-align: center;
                margin-top: 10px;
                font-size: 1.08em;
                letter-spacing: 1px;
            }}
            .volver-btn:hover {{
                background: linear-gradient(90deg, #0d47a1, #1976d2);
                transform: scale(1.05);
            }}
            .error-msg {{
                background: #e74c3c;
                color: white;
                padding: 14px;
                text-align: center;
                border-radius: 10px;
                margin-bottom: 20px;
                font-weight: 700;
                box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
                font-size: 1.1em;
            }}
            button[type="submit"], .eliminar-btn {{
                background: linear-gradient(90deg, #2ecc40 60%, #27ae60 100%);
                color: #fff;
                border: none;
                padding: 12px 32px;
                border-radius: 11px;
                font-size: 1.09em;
                font-weight: 800;
                margin-top: 10px;
                cursor: pointer;
                transition: background 0.2s, transform 0.1s;
                box-shadow: 0 2px 10px #27ae6040;
                letter-spacing: 0.7px;
            }}
            button[type="submit"]:hover, .eliminar-btn:hover {{
                background: linear-gradient(90deg, #27ae38 60%, #229954 100%);
                transform: scale(1.07);
            }}
            .eliminar-btn {{
                background: linear-gradient(90deg, #e74c3c 60%, #c0392b 100%);
                margin-left: 10px;
                margin-top: 0;
                padding: 10px 24px;
                font-size: 1em;
                box-shadow: 0 2px 10px #c0392b40;
            }}
            .eliminar-btn:hover {{
                background: linear-gradient(90deg, #c0392b 60%, #a93226 100%);
            }}
            @media (max-width: 900px) {{
                .container {{ padding: 10px 2vw; }}
                table, th, td {{ font-size: 0.97em; }}
                .detalle {{ padding: 10px 2vw; }}
            }}
            @media (max-width: 600px) {{
                .container {{ padding: 2vw 1vw; }}
                h2 {{ font-size: 1.3rem; }}
                .modalidad-btns a, .modalidad-btns button, .volver-btn {{ padding: 10px 12px; font-size: 1em; }}
                .detalle {{ padding: 10px 2vw; }}
            }}
            .modal-error-modal {{
                display: none;
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.35);
                z-index: 99999;
                align-items: center;
                justify-content: center;
            }}
            .modal-error-content {{
                background: #fff;
                border-radius: 18px;
                box-shadow: 0 8px 32px rgba(231,76,60,0.18);
                padding: 38px 48px;
                max-width: 400px;
                margin: auto;
                text-align: center;
                border: 2px solid #e74c3c;
                color: #c0392b;
                font-size: 1.25em;
                font-weight: 800;
                letter-spacing: 1px;
                position: relative;
            }}
            .modal-error-content button {{
                margin-top: 18px;
                padding: 10px 28px;
                border-radius: 8px;
                border: none;
                background: linear-gradient(90deg, #e74c3c 60%, #c0392b 100%);
                color: #fff;
                font-weight: 700;
                font-size: 1em;
                cursor: pointer;
                transition: background 0.2s, transform 0.1s;
            }}
            .modal-error-content button:hover {{
                background: linear-gradient(90deg, #c0392b 60%, #a93226 100%);
                transform: scale(1.05);
            }}
        </style>
    </head>
    <body>
        <button class="volver-btn" type="button" onclick="window.location.href='/menu'" style="margin-bottom:18px;">Salir</button>
        <div class="container">
            <h2>Modalidades de Graduación</h2>
    '''
    if mensaje_error:
        html += f'<div class="error-msg">{mensaje_error}</div>'
    elif mostrar_formulario_agregar:
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="agregar" value="1">
            <label>Nombre de la Modalidad:</label>
            <input type="text" name="nombre_modalidad" required>
            <label>Descripción:</label>
            <textarea name="descripcion" required></textarea>
            <button type="submit">Añadir</button>
            <button type="submit" name="agregar" value="1" class="volver-btn">Volver a la lista</button>
        </form>
        '''
    elif modalidad:
        html += f'''
        <form method="post" class="detalle">
            <input type="hidden" name="editar" value="1">
            <input type="hidden" name="id_modalidad" value="{modalidad[0]}">
            <label>ID Modalidad:</label>
            <div style="margin-bottom:12px;font-weight:700;color:#1976d2;">{modalidad[0]}</div>
            <label>Nombre de la Modalidad:</label>
            <input type="text" name="nombre_modalidad" value="{modalidad[1]}" required>
            <label>Descripción:</label>
            <textarea name="descripcion" required>{modalidad[2]}</textarea>
            <button type="submit">Guardar Cambios</button>
            <button type="submit" name="editar" value="1" class="volver-btn">Volver a la lista</button>
        </form>
        <form method="post" onsubmit="return confirm('¿Seguro que deseas eliminar esta modalidad?');" style="margin-top:10px;">
            <input type="hidden" name="eliminar" value="1">
            <input type="hidden" name="id_modalidad" value="{modalidad[0]}">
            <button type="submit" class="eliminar-btn">Eliminar</button>
        </form>
        '''
    else:
        html += '''
        <div class="modalidad-btns">
            <a href="?accion=agregar">Añadir Modalidad</a>
        </div>
        <div id="modal-eliminado" style="display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#e6ffe6;color:#218838;border:2px solid #28a745;border-radius:12px;padding:30px 50px;font-size:1.3rem;box-shadow:0 8px 32px rgba(40,167,69,0.18);z-index:9999;text-align:center;">
            Eliminado
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID Modalidad</th>
                    <th>Nombre Modalidad</th>
                    <th>Descripción</th>
                    <th>Editar</th>
                    <th>Eliminar</th>
                </tr>
            </thead>
            <tbody>
        '''
        for m in modalidades:
            html += f'''
            <tr id="fila-{m[0]}">
                <td>{m[0]}</td>
                <td>{m[1]}</td>
                <td>{m[2]}</td>
                <td>
                    <a href="?id_modalidad={m[0]}" class="volver-btn" style="padding:7px 18px;font-size:0.98em;background:linear-gradient(90deg,#1976d2,#42a5f5);margin:0;">Editar</a>
                </td>
                <td>
                    <form class="form-eliminar" data-id="{m[0]}" style="display:inline;">
                        <input type="hidden" name="eliminar" value="1">
                        <input type="hidden" name="id_modalidad" value="{m[0]}">
                        <button type="submit" class="eliminar-btn">Eliminar</button>
                    </form>
                </td>
            </tr>
            '''
        html += '''
            </tbody>
        </table>
        <script>
        document.querySelectorAll('.form-eliminar').forEach(function(form){
            form.addEventListener('submit', function(e){
                e.preventDefault();
                if(confirm('¿Seguro que deseas eliminar esta modalidad?')){
                    var formData = new FormData(form);
                    fetch(window.location.pathname, {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.text())
                    .then(data => {
                        // Oculta la fila eliminada
                        var id = form.getAttribute('data-id');
                        var fila = document.getElementById('fila-' + id);
                        if(fila) fila.style.display = 'none';
                        // Muestra el modal
                        document.getElementById('modal-eliminado').style.display = 'block';
                        setTimeout(function(){
                            document.getElementById('modal-eliminado').style.display = 'none';
                        }, 1500);
                    });
                }
            });
        });
        </script>
        '''
    html += '''
        <div id="modal-error" class="modal-error-modal">
            <div class="modal-error-content">
                <span id="modal-error-msg"></span>
                <br>
                <button onclick="document.getElementById('modal-error').style.display='none'">Cerrar</button>
            </div>
        </div>
        <script>
            function mostrarError(msg) {
                document.getElementById('modal-error-msg').innerText = msg;
                document.getElementById('modal-error').style.display = 'flex';
            }
    '''
    if mensaje_error:
        html += f"mostrarError({mensaje_error!r});"
    html += '''
        </script>
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
        path('', modalidad_view),
        path('modalidad/', modalidad_view),
    ]

    from django.urls import include
    settings.ROOT_URLCONF = __name__

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    execute_from_command_line([sys.argv[0], "runserver", "8000"])