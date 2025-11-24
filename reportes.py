import os
import sys
from django.http import HttpResponse
from django.urls import path
import mysql.connector
from mysql.connector import Error
from django.conf import settings
import django
from django.core.management import execute_from_command_line

def crear_conexion():
    try:
        return mysql.connector.connect(
            host='localhost',
            user='root',
            passwd='/73588144/',
            database='proyecto'
        )
    except mysql.connector.Error as err:
        print(f"Error de conexión a MySQL: '{err}'")
        return None

def reportes_view(request):
    mensaje_error = ""
    reporte_data = {}
    
    conexion = crear_conexion()
    if not conexion:
        return HttpResponse("""
            <!doctype html><html>
            <head><title>Error de Conexión</title></head>
            <body>
                <h2 style="color:red; text-align:center; padding-top: 50px;">
                    Error de conexión a la base de datos.
                </h2>
                <p style="text-align:center;">
                    Verifique que el servidor MySQL esté activo y que el usuario/contraseña sean correctos.
                </p>
            </body></html>
        """)

    cursor = conexion.cursor()
    try:
        
        cursor.execute("SELECT COUNT(*) FROM Docentes")
        reporte_data['total_docentes'] = cursor.fetchone()[0]
        
        try:
            cursor.execute("SELECT COUNT(*) FROM Estudiantes")
            reporte_data['total_estudiantes'] = cursor.fetchone()[0]
        except Error:
            reporte_data['total_estudiantes'] = "N/D (Tabla Estudiantes no encontrada)"
            
        cursor.execute("""
            SELECT area_especialidad, COUNT(id_docente)
            FROM Docentes
            GROUP BY area_especialidad
            ORDER BY 2 DESC
        """)
        reporte_data['docentes_por_area'] = cursor.fetchall()

        cursor.execute("""
            SELECT modalidad_graduacion, COUNT(id_docente)
            FROM Docentes
            GROUP BY modalidad_graduacion
            ORDER BY 2 DESC
        """)
        reporte_data['docentes_por_modalidad'] = cursor.fetchall()
        
    except Exception as e:
        mensaje_error = f"Error al ejecutar consultas SQL: {e}"
        print("Error en consultas SQL:", e)
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

    
    labels_area = [f[0] for f in reporte_data.get('docentes_por_area', [])]
    data_area = [f[1] for f in reporte_data.get('docentes_por_area', [])]
    js_labels_area = str(labels_area).replace("'", '"')
    js_data_area = str(data_area)
    
    labels_modalidad = [f[0] for f in reporte_data.get('docentes_por_modalidad', [])]
    data_modalidad = [f[1] for f in reporte_data.get('docentes_por_modalidad', [])]
    js_labels_modalidad = str(labels_modalidad).replace("'", '"')
    js_data_modalidad = str(data_modalidad)
    
    
    html = f'''
    <!doctype html>
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Reportes Estadísticos</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
        <style>
            :root{{--nav:#0b3b65;--nav-deco:#123a59;--accent:#1e73be;--card:#ffffff;--muted:#6b7b8c;--shadow: 0 18px 36px rgba(9,30,66,0.12);}}
            *{{box-sizing:border-box}} body{{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background: linear-gradient(180deg,#edf2f6 0%, #dfe8f2 100%);color:#223;}}
            .topbar{{background:linear-gradient(180deg,var(--nav) 0%, var(--nav-deco) 100%);color:#fff;padding:22px 28px;display:flex;align-items:center;justify-content:space-between;box-shadow: 0 6px 18px rgba(11,59,101,0.14);}} 
            .topbar .title{{font-weight:800;font-size:28px;letter-spacing:0.6px;}} 
            .topbar .back-btn{{background:transparent;color:#fff;border:1px solid rgba(255,255,255,0.12);padding:10px 14px;border-radius:10px;display:inline-flex;gap:10px;align-items:center;text-decoration:none;}}
            .page{{max-width:1180px;margin:34px auto;padding:0 22px}}
            .error-msg{{margin-top:14px;padding:16px;border-radius:12px;background:#d6453b;color:#fff; font-weight: 700; box-shadow: 0 4px 8px rgba(0,0,0,0.2);}}
            
            .card-grid{{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; margin-bottom: 30px; }}
            .card{{ background: var(--card); padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; border-left: 5px solid var(--accent); }}
            .card h3{{ color: var(--muted); font-size: 1rem; margin-bottom: 8px; }}
            .card h1{{ color: var(--nav); font-size: 2.5rem; font-weight: 800; }}
            .chart-container-grid{{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 30px; }}
            .chart-container{{ background: var(--card); padding: 24px; border-radius: 14px; box-shadow: var(--shadow); }}
            .chart-title{{ color: var(--nav); margin-bottom: 15px; border-bottom: 2px solid #eef3f7; padding-bottom: 10px; font-size: 1.2rem; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class='topbar'>
            <a class='back-btn' href='/'>&larr; Volver al Menú Principal</a>
            <div style='flex:1'></div>
            <div class='title' style='text-align:right'>Reportes Estadísticos 📊</div>
        </div>

        <div class='page'>
            {f"<div class='error-msg'>¡Error de Datos! {mensaje_error}</div>" if mensaje_error else ""}

            <div class="card-grid">
                <div class="card">
                    <h3>Total de Estudiantes</h3>
                    <h1>{reporte_data.get('total_estudiantes', 'N/D')}</h1>
                </div>
                <div class="card">
                    <h3>Total de Docentes</h3>
                    <h1>{reporte_data.get('total_docentes', 'N/D')}</h1>
                </div>
            </div>

            <div class="chart-container-grid">
                
                <div class="chart-container">
                    <h3 class="chart-title">Docentes por Área de Especialidad (Conteo: {len(data_area)} áreas)</h3>
                    <canvas id="docentesPorArea" style="max-height: 400px;"></canvas>
                </div>

                <div class="chart-container">
                    <h3 class="chart-title">Docentes Asignados por Modalidad</h3>
                    <canvas id="docentesPorModalidad" style="max-height: 400px;"></canvas>
                </div>
                
            </div>
        </div>

        <script>
            Chart.register(ChartDataLabels);
            
            const labelsArea = {js_labels_area};
            const dataArea = {js_data_area};
            
            if (dataArea.length > 0) {{
                const ctxArea = document.getElementById('docentesPorArea').getContext('2d');
                new Chart(ctxArea, {{
                    type: 'bar',
                    data: {{
                        labels: labelsArea,
                        datasets: [{{
                            label: 'Cantidad de Docentes',
                            data: dataArea,
                            backgroundColor: ['#1e73be', '#0b3b65', '#4d92d4', '#82b5e6', '#c4daee'],
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            datalabels: {{ 
                                anchor: 'end',
                                align: 'top',
                                formatter: (value) => value,
                                color: '#0b3b65',
                                font: {{
                                    weight: 'bold'
                                }}
                            }},
                            legend: {{
                                display: false 
                            }}
                        }},
                        scales: {{ 
                            y: {{ beginAtZero: true, ticks: {{ precision: 0 }}, title: {{ display: true, text: 'Cantidad' }} }},
                            x: {{ title: {{ display: true, text: 'Área de Especialidad' }} }}
                        }}
                    }}
                }});
            }}

            const labelsModalidad = {js_labels_modalidad};
            const dataModalidad = {js_data_modalidad};
            
            if (dataModalidad.length > 0) {{
                const ctxModalidad = document.getElementById('docentesPorModalidad').getContext('2d');
                new Chart(ctxModalidad, {{
                    type: 'pie', 
                    data: {{
                        labels: labelsModalidad,
                        datasets: [{{
                            data: dataModalidad,
                            backgroundColor: ['#36a64f', '#ff8a00', '#d6453b', '#2a5a8a', '#546e7a', '#78909c'],
                            hoverOffset: 4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ position: 'right' }},
                            title: {{ display: false }},
                            datalabels: {{ 
                                formatter: (value, context) => {{
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = (value / total * 100).toFixed(1) + '%';
                                    return percentage;
                                }},
                                color: '#fff', 
                                font: {{
                                    weight: 'bold'
                                }}
                            }}
                        }}
                    }}
                }});
            }}
        </script>
    </body>
    </html>
    '''
    return HttpResponse(html)


urlpatterns = [
    path('', reportes_view, name='home_reportes'), 
    path('reportes/', reportes_view, name='reportes_dashboard'),
]

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
    
    settings.ROOT_URLCONF = __name__

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    execute_from_command_line([sys.argv[0], "runserver", "8000"])