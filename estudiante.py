import os
import sys
from django.http import HttpResponse
from django.urls import path
import mysql.connector
from mysql.connector import Error
from django.conf import settings
import django
from django.core.management import execute_from_command_line
from django.views.decorators.csrf import csrf_exempt

ESTUDIANTES_POR_PAGINA = 10 

def crear_conexion():
    """Establece y retorna la conexión a la base de datos MySQL."""
    try:
        
        return mysql.connector.connect(
            host='localhost',
            user='root',
            passwd='/73588144/',
            database='proyecto'
        )
    except mysql.connector.Error as err:
        print(f"Error de conexión: '{err}'")
        return None

@csrf_exempt
def estudiante_view(request):
    """
    Vista principal para la gestión de estudiantes, manejo de CRUD, búsqueda y paginación.
    """
    mensaje_error = ""
    estudiantes = []
   
    try:
        pagina_actual = int(request.GET.get('page', 1))
    except ValueError:
        pagina_actual = 1
        
    termino_busqueda = request.GET.get('q', '').strip() 
    total_paginas = 0
    total_estudiantes = 0 
    
    conexion = crear_conexion()
    if conexion is None:
        return HttpResponse("<h2>Error de conexión a la base de datos.</h2>")

    cursor = conexion.cursor()
    
    try:
        
        if request.method == "POST":
            
            if request.POST.get("actualizar") == "1":
                id_estudiante = request.POST.get("id_estudiante")
                nombre = request.POST.get("nombre")
                correo = request.POST.get("correo")
                ci = request.POST.get("ci")
                carrera = request.POST.get("carrera")
                
                if id_estudiante and nombre and correo and ci and carrera:
                    try:
                        cursor.execute("""
                            UPDATE Estudiantes
                            SET nombre=%s, correo=%s, ci=%s, carrera=%s
                            WHERE id_estudiante=%s
                        """, (nombre, correo, ci, carrera, id_estudiante))
                        conexion.commit()
                        mensaje_error = "Estudiante actualizado con éxito."
                    except mysql.connector.IntegrityError:
                        mensaje_error = "Error: El correo o CI ingresado ya existen."
                else:
                    mensaje_error = "Todos los campos son obligatorios para actualizar."
            
            else: 
                nombre = request.POST.get("nombre")
                correo = request.POST.get("correo")
                ci = request.POST.get("ci")
                carrera = request.POST.get("carrera")

                if nombre and correo and ci and carrera:
                    try:
                        cursor.execute("""
                            INSERT INTO Estudiantes (nombre, correo, ci, carrera)
                            VALUES (%s, %s, %s, %s)
                        """, (nombre, correo, ci, carrera))
                        conexion.commit()
                        mensaje_error = "Nuevo estudiante registrado con éxito."
                    except mysql.connector.IntegrityError:
                        mensaje_error = "Error: El correo o CI ingresado ya existen."
                else:
                    mensaje_error = "Todos los campos son obligatorios para crear."

        
       
        sql_count = "SELECT COUNT(*) FROM Estudiantes e"
        params = []
        
        if termino_busqueda:
            sql_count += " WHERE e.nombre LIKE %s OR e.correo LIKE %s OR e.ci LIKE %s OR e.carrera LIKE %s"
            like_term = f"%{termino_busqueda}%"
            
            params = [like_term, like_term, like_term, like_term] 
        
        cursor.execute(sql_count, tuple(params))
        total_estudiantes = cursor.fetchone()[0]
        
        total_paginas = (total_estudiantes + ESTUDIANTES_POR_PAGINA - 1) // ESTUDIANTES_POR_PAGINA
        
        if pagina_actual < 1:
            pagina_actual = 1
        elif pagina_actual > total_paginas and total_paginas > 0:
            pagina_actual = total_paginas
        elif total_estudiantes == 0:
            pagina_actual = 0
            
        offset = (pagina_actual - 1) * ESTUDIANTES_POR_PAGINA if pagina_actual > 0 else 0
        
        sql_select = """
            SELECT id_estudiante, nombre, correo, ci, carrera
            FROM Estudiantes e
        """
        
        select_params = list(params) 
        
        if termino_busqueda:
             sql_select += " WHERE e.nombre LIKE %s OR e.correo LIKE %s OR e.ci LIKE %s OR e.carrera LIKE %s"
             
        sql_select += " LIMIT %s OFFSET %s"
        select_params.append(ESTUDIANTES_POR_PAGINA)
        select_params.append(offset)

        cursor.execute(sql_select, tuple(select_params))
        estudiantes = cursor.fetchall()

    except Exception as e:
        mensaje_error = f"Error al consultar o modificar la base de datos: {e}"
        print("Error en estudiante_view:", e)
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

    data_paginacion = {
        'total_paginas': total_paginas,
        'pagina_actual': pagina_actual,
        'termino_busqueda': termino_busqueda,
        
        'path_base': request.path.rstrip('/') 
    }
    
    
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
            /* --- Estilos CSS (Idénticos a la vista de Docentes) --- */
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            :root {{
                --primary: #0b3b65; --primary-dark: #123a59; --accent: #1e73be;
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
                text-decoration: none;
            }}
            .back-button:hover {{ transform: translateX(-4px); background: rgba(255,255,255,0.18); }}
            .top-title {{
                color: #ffffff;
                font-size: 1.6rem;
                font-weight: 700;
                margin: 0;
                letter-spacing: 0.6px;
                text-align: center; 
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
                transition: background 0.2s;
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
            
            .btn-edit {{ 
                border-radius:8px; padding:8px 12px; border: none; cursor:pointer; 
                color: #fff; font-weight: 700; font-size: 1.1em;
                background: #8d5b38; 
            }}
            .btn-edit:hover {{
                background: #a67c52;
            }}
            .error-msg {{ background: linear-gradient(90deg, #fee2e2 0%, #fecaca 100%); color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; font-weight:700; }}
            
            .modal-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 1000;
                transition: opacity 0.3s ease-in-out;
                opacity: 0;
            }}
            .modal-container.active {{
                opacity: 1;
                display: flex;
            }}
            .modal-content {{
                background: #ffffff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: var(--shadow-lg);
                max-width: 600px;
                width: 90%;
                transform: translateY(-50px);
                transition: transform 0.3s ease-in-out;
            }}
            .modal-container.active .modal-content {{
                transform: translateY(0);
            }}
            .form-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:12px; }}
            .form-row input, .form-row select {{ flex: 1; padding:10px 12px; border:1.5px solid #e6eef8; border-radius:8px; min-width:160px; }}
            .form-buttons {{ display:flex; gap:10px; justify-content:center; margin-top:12px; }}
            /* --- Fin de Estilos CSS --- */
        </style>
    </head>
    <body>
        <div class="top-bar">
            <a class="back-button" href="/menu">
                <i class="fas fa-arrow-left"></i>
                Volver al Menú
            </a>
            <h1 class="top-title">Gestión de Estudiantes</h1>
            <div style="width: 160px;"></div> 
        </div>

        <div class="container">
            <div class="action-buttons">
                <input type="text" id="buscar_input" placeholder="Buscar por Nombre, CI, Correo o Carrera..." style="padding:10px 12px; border-radius:8px; border:1.5px solid #e6eef8; min-width:250px;">
                <button class="btn" onclick="buscarEstudiante()"><i class="fas fa-search"></i> Buscar</button>
                <button class="btn" onclick="mostrarModalCrear()"><i class="fas fa-plus"></i> Crear Nuevo Registro</button>
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
                                <th>Nombre</th>
                                <th>Correo</th>
                                <th>Carrera</th>
                                <th style="text-align:center;">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
    '''
    
   
    if estudiantes:
        for e in estudiantes:
            id_est = str(e[0])
            nombre = str(e[1] or "").replace("'", "\\'")
            correo = str(e[2] or "").replace("'", "\\'")
            ci = str(e[3] or "").replace("'", "\\'")
            carrera = str(e[4] or "").replace("'", "\\'")
            
            ci_display = e[3] or "" 
            
            html += f'''
                                <tr>
                                    <td>{ci_display}</td>
                                    <td>{e[1] or ""}</td>
                                    <td>{e[2] or ""}</td>
                                    <td>{e[4] or ""}</td>
                                    <td style="text-align:center;">
                                    <button class="btn-edit" onclick="editarRegistro('{id_est}', '{nombre}', '{correo}', '{ci}', '{carrera}')" title="Editar">✏️</button>
                                    </td>
                                </tr>
            '''
    else:
        html += '<tr><td colspan="5" style="text-align:center; padding:30px; color:var(--muted);">No hay estudiantes registrados.</td></tr>'

    html += '''
                        </tbody>
                    </table>
                </div>
            </div>
    '''
    
    
    paginacion_html = '<div style="display:flex; justify-content:center; align-items:center; margin-top: 20px; gap: 20px; font-weight: 500;">'
    
    base_query = f'?q={data_paginacion["termino_busqueda"]}&page=' if data_paginacion["termino_busqueda"] else '?page='
   
    url_base = data_paginacion['path_base'] + base_query 

    if data_paginacion["pagina_actual"] > 1:
        url_anterior = url_base + str(data_paginacion["pagina_actual"] - 1)
        paginacion_html += f'<a href="{url_anterior}" class="btn" style="padding: 8px 15px; text-decoration: none; background:var(--primary); color:#fff;"><i class="fas fa-chevron-left"></i> Anterior</a>'
    else:
        paginacion_html += f'<span style="padding: 8px 15px; background:#e0e0e0; color:#9e9e9e; cursor:not-allowed; border-radius: 8px;">Anterior</span>'

    if data_paginacion["total_paginas"] > 0:
        paginacion_html += f'<span style="font-size: 1.1em; color: var(--primary);">Página {data_paginacion["pagina_actual"]} de {data_paginacion["total_paginas"]}</span>'

    if data_paginacion["pagina_actual"] < data_paginacion["total_paginas"]:
        url_siguiente = url_base + str(data_paginacion["pagina_actual"] + 1)
        paginacion_html += f'<a href="{url_siguiente}" class="btn" style="padding: 8px 15px; text-decoration: none; background:var(--primary); color:#fff;">Siguiente <i class="fas fa-chevron-right"></i></a>'
    else:
        paginacion_html += f'<span style="padding: 8px 15px; background:#e0e0e0; color:#9e9e9e; cursor:not-allowed; border-radius: 8px;">Siguiente</span>'


    paginacion_html += '</div>'
    
    html += paginacion_html

    html += '''
        </div>
        
        <div class="modal-container" id="modal-crear" onclick="cerrarModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <form id="crear-form" method="post">
                    <h3 style="margin-top:0; color:var(--primary); text-align:center;">Crear Nuevo Estudiante</h3>
                    <div class="form-row">
                        <input type="text" name="nombre" placeholder="Nombre Completo" required>
                        <input type="email" name="correo" placeholder="Correo Electrónico" required>
                    </div>
                    <div class="form-row">
                        <input type="text" name="ci" placeholder="Cédula de Identidad (CI)" required>
                        <input type="text" name="carrera" placeholder="Carrera/Programa" required>
                    </div>
                    <div class="form-buttons">
                        <button type="button" class="btn" onclick="cerrarModal()" style="background:#9e9e9e;">Cancelar</button>
                        <button type="submit" class="btn">Guardar</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="modal-container" id="modal-actualizar" onclick="cerrarModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <form id="actualizar-form" method="post">
                    <h3 style="margin-top:0; color:var(--primary); text-align:center;">Actualizar Estudiante</h3>
                    <input type="hidden" name="actualizar" value="1">
                    <input type="hidden" id="upd_id" name="id_estudiante">
                    <div class="form-row">
                        <input type="text" id="upd_nombre" name="nombre" placeholder="Nombre Completo" required>
                        <input type="email" id="upd_correo" name="correo" placeholder="Correo Electrónico" required>
                    </div>
                    <div class="form-row">
                        <input type="text" id="upd_ci" name="ci" placeholder="Cédula de Identidad (CI)" required>
                        <input type="text" id="upd_carrera" name="carrera" placeholder="Carrera/Programa" required>
                    </div>
                    <div class="form-buttons">
                        <button type="button" class="btn" onclick="cerrarModal()" style="background:#9e9e9e;">Cancelar</button>
                        <button type="submit" class="btn">Actualizar</button>
                    </div>
                </form>
            </div>
        </div>

        <script>
    
    function showModal(id) {
        if (id === 'modal-crear') {
            document.getElementById('crear-form').reset();
        }

        document.getElementById('modal-crear').classList.remove('active');
        document.getElementById('modal-actualizar').classList.remove('active');
        
        document.getElementById('modal-crear').style.display = 'none';
        document.getElementById('modal-actualizar').style.display = 'none';

        const modal = document.getElementById(id);
        modal.style.display = 'flex';
        setTimeout(function() {
            modal.classList.add('active');
        }, 10);
    }

    function cerrarModal() {
        document.getElementById('modal-crear').classList.remove('active');
        document.getElementById('modal-actualizar').classList.remove('active');
        
        setTimeout(function() {
            document.getElementById('modal-crear').style.display = 'none';
            document.getElementById('modal-actualizar').style.display = 'none';
        }, 300);
    }
    
    function mostrarModalCrear() {
        showModal('modal-crear');
    }

    function editarRegistro(id, nombre, correo, ci, carrera) {
        document.getElementById('upd_id').value = id;
        document.getElementById('upd_nombre').value = nombre;
        document.getElementById('upd_correo').value = correo;
        document.getElementById('upd_ci').value = ci;
        document.getElementById('upd_carrera').value = carrera;
        
        showModal('modal-actualizar');
    }
    
    function buscarEstudiante() {
        var input = document.getElementById('buscar_input').value.trim();
        const currentPath = window.location.pathname;
        
        let newUrl = currentPath;
        if (input) {
             // Redirige al inicio de la paginación con el filtro
            newUrl += '?q=' + encodeURIComponent(input) + '&page=1'; 
        } else {
             // Si se borra la búsqueda, vuelve a la página 1
            newUrl += '?page=1';
        }
        window.location.href = newUrl;
    }

    document.addEventListener('DOMContentLoaded', function() {
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');
        if (query) {
            document.getElementById('buscar_input').value = query;
        }
    });
</script>
    </body>
    
    </html>
    '''
    return HttpResponse(html)

urlpatterns = [
    
    path('', estudiante_view),
    
    path('estudiantes/', estudiante_view),
    path('estudiantes', estudiante_view), 
]
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SECRET_KEY = 'secret-key'
    DEBUG = True

    if not settings.configured:
        settings.configure(
            DEBUG=DEBUG,
            SECRET_KEY=SECRET_KEY,
            ROOT_URLCONF=sys.modules[__name__], 
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
    settings.ROOT_URLCONF = sys.modules[__name__]
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    execute_from_command_line([sys.argv[0], "runserver", "8000"])
