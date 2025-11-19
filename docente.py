import os
import sys
from django.http import HttpResponse
from django.urls import path
import mysql.connector
from django.conf import settings
import django
from django.core.management import execute_from_command_line
from django.views.decorators.csrf import csrf_exempt

def crear_conexion():
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
def docente_view(request):
    mensaje_error = ""
    conexion = crear_conexion()
    if not conexion:
        return HttpResponse("<h2>Error de conexión a la base de datos.</h2>")

    cursor = conexion.cursor()
    try:
        if request.method == "POST":
            if request.POST.get("actualizar") == "1":
                id_docente = request.POST.get("id_docente")
                nombre = request.POST.get("nombre")
                correo = request.POST.get("correo")
                area_especialidad = request.POST.get("area_especialidad")
                modalidad_graduacion = request.POST.get("modalidad_graduacion")
                if id_docente and nombre and correo and area_especialidad and modalidad_graduacion:
                    try:
                        cursor.execute("""
                            UPDATE Docentes
                            SET nombre=%s, correo=%s, area_especialidad=%s, modalidad_graduacion=%s
                            WHERE id_docente=%s
                        """, (nombre, correo, area_especialidad, modalidad_graduacion, id_docente))
                        conexion.commit()
                    except mysql.connector.IntegrityError:
                        mensaje_error = "Error: El correo ingresado ya existe."
                else:
                    mensaje_error = "Todos los campos son obligatorios para actualizar."
            elif request.POST.get("eliminar") == "1":
                id_docente = request.POST.get("id_docente")
                if id_docente:
                    cursor.execute("DELETE FROM Docentes WHERE id_docente=%s", (id_docente,))
                    conexion.commit()
                else:
                    mensaje_error = "Debe seleccionar un docente para eliminar."
            else:
                nombre = request.POST.get("nombre")
                correo = request.POST.get("correo")
                area_especialidad = request.POST.get("area_especialidad")
                modalidad_graduacion = request.POST.get("modalidad_graduacion")
                if nombre and correo and area_especialidad and modalidad_graduacion:
                    try:
                        cursor.execute("""
                            INSERT INTO Docentes (nombre, correo, area_especialidad, modalidad_graduacion)
                            VALUES (%s, %s, %s, %s)
                        """, (nombre, correo, area_especialidad, modalidad_graduacion))
                        conexion.commit()
                    except mysql.connector.IntegrityError:
                        mensaje_error = "Error: El correo ingresado ya existe."
                else:
                    mensaje_error = "Todos los campos son obligatorios para crear."

        cursor.execute("""
            SELECT id_docente, nombre, correo, area_especialidad, modalidad_graduacion
            FROM Docentes
        """)
        docentes = cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

    header_html = (
        "<th>nombre</th>"
        "<th>correo</th>"
        "<th>area_especialidad</th>"
        "<th>modalidad_graduacion</th>"
        "<th style='text-align:right;padding-right:22px'>ACCIONES</th>"
    )

    rows_html = ""
    for d in docentes:
        id_doc = d[0]
        nombre = d[1] or ""
        correo = d[2] or ""
        area = d[3] or ""
        modalidad = d[4] or ""

        modalidad_text = str(modalidad)
        if 'complet' in modalidad_text.lower():
            badge_cls = 'green'
        elif 'proceso' in modalidad_text.lower():
            badge_cls = 'orange'
        else:
            badge_cls = 'red'

        rows_html += (
            "<tr>"
            f"<td class='name-cell'>{nombre}</td>"
            f"<td class='muted'>{correo}</td>"
            f"<td class='muted'>{area}</td>"
            f"<td><span class='status {badge_cls}'>{modalidad}</span></td>"
            "<td>"
            "<div class='actions' style='justify-content:flex-end;'>"
            f"<button class='icon-btn edit-btn' onclick=\"document.getElementById('docente-select').value='{id_doc}|{nombre}|{correo}|{area}|{modalidad}'; togglePanel('actualizar-form')\" title='Editar'><span class='icon-small'>✎</span></button>"
            f"<button class='icon-btn del-btn' onclick=\"document.getElementById('eliminar-select').value='{id_doc}'; togglePanel('eliminar-form')\" title='Eliminar'><span class='icon-small'>⛔</span></button>"
            "</div>"
            "</td>"
            "</tr>"
        )

    options_html = ""
    for d in docentes:
        options_html += f"<option value='{d[0]}'>{d[1]} (ID:{d[0]})</option>\n"

    html = (
        "<!doctype html>"
        "<html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<title>Lista de Docentes</title>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>"
        ":root{--nav:#0b3b65;--nav-deco:#123a59;--accent:#1e73be;--card:#ffffff;--muted:#6b7b8c;--green:#36a64f;--orange:#ff8a00;--red:#d6453b;--shadow: 0 18px 36px rgba(9,30,66,0.12);}"
        "*{box-sizing:border-box} body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background: linear-gradient(180deg,#edf2f6 0%, #dfe8f2 100%);color:#223;}"
        ".topbar{background:linear-gradient(180deg,var(--nav) 0%, var(--nav-deco) 100%);color:#fff;padding:22px 28px;display:flex;align-items:center;justify-content:space-between;box-shadow: 0 6px 18px rgba(11,59,101,0.14);} "
        ".topbar .title{font-weight:800;font-size:28px;letter-spacing:0.6px;} .topbar .back-btn{background:transparent;color:#fff;border:1px solid rgba(255,255,255,0.12);padding:10px 14px;border-radius:10px;display:inline-flex;gap:10px;align-items:center;text-decoration:none;}"
        ".page{max-width:1180px;margin:34px auto;padding:0 22px}.card{background:var(--card);border-radius:14px;padding:20px;box-shadow:var(--shadow);overflow:hidden}.card-header{display:flex;align-items:center;justify-content:space-between;padding:12px 6px 20px 6px}"
        ".create-btn{background:linear-gradient(180deg,var(--nav) 0%, var(--accent) 100%);color:#fff;padding:10px 16px;border-radius:10px;border:none;font-weight:800;cursor:pointer;display:flex;align-items:center;gap:10px}"
        ".table-wrap{margin-top:6px} table.docs{width:100%;border-collapse:separate;border-spacing:0;border-radius:12px;overflow:hidden}"
        "table.docs thead th{background:var(--nav);color:#fff;padding:18px 14px;text-align:left;font-weight:800;font-size:13px}"
        "table.docs tbody td{padding:18px 14px;color:#243241;border-bottom:1px solid #eef3f7;vertical-align:middle}"
        ".name-cell{font-weight:800;color:#17385d}.muted{color:var(--muted);font-weight:600;font-size:0.95rem}"
        ".status{display:inline-block;padding:8px 12px;border-radius:999px;color:#fff;font-weight:800;font-size:0.86rem}"
        ".status.green{background:var(--green)}.status.orange{background:var(--orange)}.status.red{background:var(--red)}"
        ".actions{display:flex;gap:10px}.icon-btn{width:42px;height:42px;border-radius:8px;border:none;display:inline-flex;align-items:center;justify-content:center;color:#fff;cursor:pointer}"
        ".edit-btn{background:#8d5b38}.del-btn{background:#d23b3b}.icon-small{font-size:16px}"
        ".form-panel{margin-top:18px;display:none;background:#f7fbff;padding:18px;border-radius:10px}.form-row{display:flex;gap:12px;flex-wrap:wrap}.form-row input,.form-row select{padding:10px;border-radius:8px;border:1px solid #d7e7f4}"
        ".form-actions{margin-top:10px;display:flex;gap:10px}.btn-save{background:var(--green);color:#fff;border:none;padding:10px 14px;border-radius:8px}.btn-cancel{background:#fff;color:var(--nav);border:1px solid #d2e6fb;padding:10px 14px;border-radius:8px}"
        ".error-msg{margin-top:14px;padding:12px;border-radius:10px;background:linear-gradient(90deg,#d6453b,#ff6b6b);color:#fff}"
        "</style>"
        "<script>"
        "function togglePanel(id){var panels=['crear-form','actualizar-form','eliminar-form'];panels.forEach(function(p){document.getElementById(p).style.display=(p===id)?'block':'none';});setTimeout(function(){var el=document.getElementById(id); if(el) window.scrollTo({top:el.offsetTop-80,behavior:'smooth'});},200);}"
        "function llenarFormularioActualizar(){var sel=document.getElementById('docente-select'); if(!sel.value) return; var parts=sel.value.split('|'); document.getElementById('upd_id').value=parts[0]||''; document.getElementById('upd_nombre').value=parts[1]||''; document.getElementById('upd_correo').value=parts[2]||''; document.getElementById('upd_area').value=parts[3]||''; document.getElementById('upd_modalidad').value=parts[4]||'';}"
        "</script>"
        "</head>"
        "<body>"
        "<div class='topbar'><a class='back-btn' href='/menu'>&larr; Volver al Menú</a><div style='flex:1'></div><div class='title' style='text-align:right'>Lista de Docentes</div></div>"
        "<div class='page'><div class='card'>"
        "<div class='card-header'><div></div><div style='margin-left:auto'><button class='create-btn' onclick=\"togglePanel('crear-form')\"><span style='font-size:18px;font-weight:900;'>+</span> Crear Nuevo Registro</button></div></div>"
        "<div class='table-wrap'><table class='docs' role='table'><thead><tr>"
        + header_html +
        "</tr></thead><tbody>"
        + rows_html +
        "</tbody></table></div>"
        "<form id='crear-form' class='form-panel' method='post'>"
        "<h3 style='margin:0;color:var(--nav)'>Crear Nuevo Docente</h3>"
        "<div class='form-row' style='margin-top:12px;'>"
        "<input type='text' name='nombre' placeholder='Nombre' required>"
        "<input type='email' name='correo' placeholder='Correo' required>"
        "<input type='text' name='area_especialidad' placeholder='Área de Especialidad' required>"
        "<input type='text' name='modalidad_graduacion' placeholder='Modalidad de Graduación' required>"
        "</div><div class='form-actions'><button class='btn-save' type='submit'>Guardar</button><button type='button' class='btn-cancel' onclick=\"document.getElementById('crear-form').style.display='none'\">Cancelar</button></div></form>"
        "<form id='actualizar-form' class='form-panel' method='post'>"
        "<h3 style='margin:0;color:var(--nav)'>Actualizar Docente</h3>"
        "<div class='form-row' style='margin-top:12px;'>"
        "<select id='docente-select' name='id_docente' onchange='llenarFormularioActualizar()'>"
        "<option value=''>Seleccione un docente</option>"
        + "".join([f"<option value='{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}'>{row[1]} (ID:{row[0]})</option>" for row in docentes]) +
        "</select></div>"
        "<input type='hidden' name='actualizar' value='1'>"
        "<input type='hidden' id='upd_id' name='id_docente'>"
        "<div class='form-row' style='margin-top:12px;'>"
        "<input type='text' id='upd_nombre' name='nombre' placeholder='Nombre' required>"
        "<input type='email' id='upd_correo' name='correo' placeholder='Correo' required>"
        "<input type='text' id='upd_area' name='area_especialidad' placeholder='Área de Especialidad' required>"
        "<input type='text' id='upd_modalidad' name='modalidad_graduacion' placeholder='Modalidad de Graduación' required>"
        "</div><div class='form-actions'><button class='btn-save' type='submit'>Actualizar</button><button type='button' class='btn-cancel' onclick=\"document.getElementById('actualizar-form').style.display='none'\">Cerrar</button></div></form>"
        "<form id='eliminar-form' class='form-panel' method='post'>"
        "<h3 style='margin:0;color:var(--nav)'>Eliminar Docente</h3>"
        "<div class='form-row' style='margin-top:12px;'>"
        "<input type='hidden' name='eliminar' value='1'>"
        f"<select id='eliminar-select' name='id_docente' required><option value=''>Seleccione un docente</option>{options_html}</select>"
        "</div><div class='form-actions'><button class='btn-save' type='submit' style='background:var(--red)'>Eliminar</button><button type='button' class='btn-cancel' onclick=\"document.getElementById('eliminar-form').style.display='none'\">Cancelar</button></div></form>"
        + (f"<div class='error-msg'>{mensaje_error}</div>" if mensaje_error else "")
        + "</div></div></body></html>"
    )

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
        path('', docente_view),
        path('docentes/', docente_view),
    ]

    settings.ROOT_URLCONF = __name__

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    execute_from_command_line([sys.argv[0], "runserver", "8000"])
