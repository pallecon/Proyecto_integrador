from django.http import HttpResponse
from django.urls import path
from conexion import crear_conexion

def monitoreo_titulacion_view(request):
    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    cursor = conexion.cursor()

    success_message = ""
    error_message = ""

    if request.method == "POST":
        accion = request.POST.get("accion")

        def calcular_estado_etapa(primera, segunda):
            if primera == "completado" and segunda == "completado":
                return "completado"
            elif (primera == "completado" and segunda == "falta") or (primera == "falta" and segunda == "completado"):
                return "en_proceso"
            elif primera == "falta" and segunda == "falta":
                return "pendiente"
            else:
                return "pendiente"

        if accion == "crear":
            campos = [
                "id_estudiante", "id_etapa", "id_tutor", "id_revisor",
                "primera_entrega_estado", "fecha_primera_entrega",
                "segunda_entrega_estado", "fecha_segunda_entrega"
            ]
            valores = [request.POST.get(c) for c in campos]

            estado_etapa = calcular_estado_etapa(
                request.POST.get("primera_entrega_estado"),
                request.POST.get("segunda_entrega_estado")
            )
            campos.insert(4, "estado_etapa")
            valores.insert(4, estado_etapa)
            try:
                cursor.execute(f"""
                    INSERT INTO Monitoreo_Titulacion (
                        {', '.join(campos)}
                    ) VALUES ({', '.join(['%s'] * len(campos))})
                """, valores)
                conexion.commit()
                success_message = "Registro creado exitosamente!"
            except Exception as e:
                print(f"Error al crear registro: {e}")
                error_message = f"Error al crear registro: {e}"

        elif accion == "actualizar":
            id_monitoreo = request.POST.get("id_monitoreo")
            campos = [
                "id_estudiante", "id_etapa", "id_tutor", "id_revisor",
                "primera_entrega_estado", "fecha_primera_entrega",
                "segunda_entrega_estado", "fecha_segunda_entrega"
            ]
            valores = [request.POST.get(c) for c in campos]
            estado_etapa = calcular_estado_etapa(
                request.POST.get("primera_entrega_estado"),
                request.POST.get("segunda_entrega_estado")
            )
            campos.insert(4, "estado_etapa")
            valores.insert(4, estado_etapa)
            try:
                cursor.execute(f"""
                    UPDATE Monitoreo_Titulacion
                    SET {', '.join([f"{c}=%s" for c in campos])}
                    WHERE id_monitoreo=%s
                """, valores + [id_monitoreo])
                cursor.execute("""
                    UPDATE Asignacion_revisor
                    SET id_revisor = %s
                    WHERE id_estudiante = %s
                """, (request.POST.get("id_revisor"), request.POST.get("id_estudiante")))
                conexion.commit()
                success_message = "Registro actualizado exitosamente!"
            except Exception as e:
                print(f"Error al actualizar registro: {e}")
                error_message = f"Error al actualizar registro: {e}"

        elif accion == "eliminar":
            id_monitoreo = request.POST.get("id_monitoreo")
            try:
                cursor.execute("""
                    DELETE FROM Monitoreo_Titulacion WHERE id_monitoreo = %s
                """, (id_monitoreo,))
                conexion.commit()
                success_message = "Registro eliminado exitosamente!"
            except Exception as e:
                print(f"Error al eliminar registro: {e}")
                error_message = f"Error al eliminar registro: {e}"

    cursor.execute("SELECT id_estudiante, nombre FROM Estudiantes")
    estudiantes = cursor.fetchall() 

    cursor.execute("SELECT id_etapa, nombre_etapa FROM Etapas_Titulacion")
    etapas = cursor.fetchall()  

    cursor.execute("SELECT id_docente, nombre FROM Docentes")
    docentes = cursor.fetchall()  

    columnas_monitoreo = [
        "id_monitoreo", "id_estudiante", "id_etapa", "id_tutor", "id_revisor",
        "estado_etapa",
        "primera_entrega_estado", "fecha_primera_entrega",
        "segunda_entrega_estado", "fecha_segunda_entrega"
    ]

    select_sql = """
        SELECT 
            m.id_monitoreo,
            m.id_estudiante,
            e.nombre AS estudiante_nombre,
            m.id_etapa,
            et.nombre_etapa,
            m.id_tutor,
            dt.nombre AS tutor_nombre,
            m.id_revisor,
            IFNULL(dr.nombre, '-') AS revisor_nombre,
            m.estado_etapa,
            m.primera_entrega_estado,
            m.fecha_primera_entrega,
            m.segunda_entrega_estado,
            m.fecha_segunda_entrega
        FROM Monitoreo_Titulacion m
        JOIN Estudiantes e ON m.id_estudiante = e.id_estudiante
        JOIN Etapas_Titulacion et ON m.id_etapa = et.id_etapa
        JOIN Docentes dt ON m.id_tutor = dt.id_docente
        LEFT JOIN Docentes dr ON m.id_revisor = dr.id_docente
        ORDER BY m.id_monitoreo ASC
    """

    try:
        cursor.execute(select_sql)
        registros = cursor.fetchall()
    except Exception as e:
        error_message = f"Error al consultar registros: {e}"
        registros = []

    columnas_tabla = [
        ("id_monitoreo", "ID Monitoreo"),
        ("estudiante_nombre", "Estudiante"),
        ("nombre_etapa", "Etapa"),
        ("tutor_nombre", "Tutor"),
        ("revisor_nombre", "Revisor"),
        ("primera_entrega_estado", "1ra Entrega Estado"),
        ("fecha_primera_entrega", "Fecha 1ra Entrega"),
        ("segunda_entrega_estado", "2da Entrega Estado"),
        ("fecha_segunda_entrega", "Fecha 2da Entrega"),
        ("estado_etapa", "Etapa de estado"),
        ("pre_defensa", "Pre Defensa"), 
    ]

    html = f'''
    <html>
    <head>
        <title>Monitoreo de Titulación</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
        <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
        <style>
            /* Estilos principales (resumen: diseño limpio y responsivo para la tabla y formularios) */
            body {{
                font-family: 'Roboto', sans-serif;
                background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 0;
                animation: gradientBG 12s ease-in-out infinite alternate;
                background-size: 200% 200%;
            }}
            @keyframes gradientBG {{
                0% {{ background-position: 0% 50%; }}
                100% {{ background-position: 100% 50%; }}
            }}
            .container {{
                max-width: 1200px;
                margin: 40px auto;
                background: rgba(255,255,255,0.95);
                padding: 40px 30px 30px 30px;
                border-radius: 24px;
                box-shadow: 0 16px 40px rgba(0,0,0,0.18);
                backdrop-filter: blur(6px);
                position: relative;
                transition: box-shadow 0.3s;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .tabla-wrapper {{
                width: 100%;
                overflow-x: auto;
                margin: 0 auto 30px auto;
                border-radius: 16px;
                box-shadow: 0 4px 24px #b2ebf2;
                background: rgba(255,255,255,0.98);
                padding: 10px 0;
            }}
            table {{
                border-collapse: separate;
                border-spacing: 0;
                width: 98%;
                margin: 0 auto;
                background: transparent;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: none;
            }}
            th, td {{
                border-bottom: 1px solid #b2ebf2;
                padding: 14px 10px;
                text-align: center;
                vertical-align: middle;
            }}
            th {{
                background: linear-gradient(90deg, #0077cc 60%, #4dd0e1 100%);
                color: #fff;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-size: 1em;
            }}
            tr:last-child td {{
                border-bottom: none;
            }}
            tr {{
                transition: background 0.25s;
            }}
            tr:nth-child(even) {{
                background-color: #f7fafc;
            }}
            tr:hover {{
                background: linear-gradient(90deg, #e3f2fd 0%, #b2ebf2 100%);
                box-shadow: 0 2px 12px #b2ebf2;
            }}
            .action-buttons {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .action-buttons button {{
                margin: 0 10px;
                padding: 14px 36px;
                font-size: 1.1em;
                border-radius: 30px;
                border: none;
                background: linear-gradient(90deg, #4dd0e1 60%, #0077cc 100%);
                color: #fff;
                cursor: pointer;
                transition: background 0.3s, transform 0.1s, box-shadow 0.3s;
                box-shadow: 0 4px 16px rgba(0,0,0,0.09);
                font-weight: 600;
            }}
            .action-buttons button:hover {{
                background: linear-gradient(90deg, #00bcd4 60%, #0288d1 100%);
                transform: translateY(-2px) scale(1.04);
                box-shadow: 0 8px 24px #b2ebf2;
            }}
            .formulario {{
                display: none;
                padding: 32px 24px;
                background: rgba(255,255,255,0.97);
                border: 1.5px solid #b2ebf2;
                border-radius: 14px;
                margin-top: 20px;
                margin-bottom: 30px;
                box-shadow: 0 4px 24px #b2ebf2;
                backdrop-filter: blur(2px);
            }}
            .formulario h3 {{
                margin-top: 0;
                color: #0077cc;
                text-align: center;
                margin-bottom: 25px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            .formulario form {{
                display: grid;
                grid-template-columns: 1fr 2fr;
                gap: 20px;
                align-items: center;
            }}
            .formulario label {{
                font-weight: 500;
                text-align: right;
                color: #546e7a;
            }}
            .formulario input,
            .formulario select {{
                padding: 12px;
                border-radius: 7px;
                border: 1.5px solid #b0bec5;
                font-size: 1em;
                transition: border-color 0.3s, box-shadow 0.3s;
                background: #f7fafc;
            }}
            .formulario input:focus,
            .formulario select:focus {{
                border-color: #0077cc;
                box-shadow: 0 0 8px #b2ebf2;
                outline: none;
            }}
            .formulario button[type="submit"] {{
                grid-column: span 2;
                margin-top: 20px;
                background: linear-gradient(90deg, #0077cc 60%, #4dd0e1 100%);
                padding: 14px 36px;
                font-size: 1.1em;
                border-radius: 30px;
                border: none;
                color: #fff;
                cursor: pointer;
                transition: background 0.3s, transform 0.1s, box-shadow 0.3s;
                box-shadow: 0 4px 16px #b2ebf2;
                font-weight: 600;
            }}
            .formulario button[type="submit"]:hover {{
                background: linear-gradient(90deg, #0288d1 60%, #00bcd4 100%);
                transform: translateY(-2px) scale(1.04);
                box-shadow: 0 8px 24px #b2ebf2;
            }}
            .formulario .cancel-button button {{
                background: #90a4ae;
                color: #fff;
                padding: 10px 24px;
                border: none;
                border-radius: 20px;
                cursor: pointer;
                transition: background 0.3s;
                font-weight: 500;
            }}
            .formulario .cancel-button button:hover {{
                background: #78909c;
            }}
            .estado-completado {{
                font-weight: bold;
                color: #43a047;
                text-shadow: 0 1px 2px #e8f5e9;
            }}
            .estado-en_proceso {{
                font-weight: bold;
                color: #ffa726;
                text-shadow: 0 1px 2px #fff3e0;
            }}
            .estado-pendiente {{
                font-weight: bold;
                color: #ef5350;
                text-shadow: 0 1px 2px #ffebee;
            }}
            .message-area {{
                text-align: center;
                margin-bottom: 20px;
                padding: 14px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 1.1em;
                opacity: 0;
                animation: fadeIn 0.5s ease-out forwards;
                box-shadow: 0 2px 8px #b2ebf2;
            }}
            .message-area.success {{
                background-color: #e8f5e9;
                color: #43a047;
                border: 1.5px solid #43a047;
            }}
            .message-area.error {{
                background-color: #ffebee;
                color: #ef5350;
                border: 1.5px solid #ef5350;
            }}
            .action-cell {{
                text-align: center;
                white-space: nowrap;
            }}
            .action-cell button {{
                margin: 0 4px;
                padding: 8px 18px;
                font-size: 0.95em;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                transition: background 0.3s, transform 0.1s;
                font-weight: 500;
            }}
            .action-cell .edit-button {{
                background: linear-gradient(90deg, #ffb300 60%, #ffe082 100%);
                color: #263238;
            }}
            .action-cell .edit-button:hover {{
                background: linear-gradient(90deg, #fb8c00 60%, #ffd54f 100%);
                transform: translateY(-1px) scale(1.05);
            }}
            .action-cell .delete-button {{
                background: linear-gradient(90deg, #ef5350 60%, #ff8a80 100%);
                color: #fff;
            }}
            .action-cell .delete-button:hover {{
                background: linear-gradient(90deg, #e53935 60%, #ff5252 100%);
                transform: translateY(-1px) scale(1.05);
            }}
            .back-button {{
                background: linear-gradient(90deg, #607d8b 60%, #b0bec5 100%);
                color: #fff;
                padding: 10px 28px;
                border: none;
                border-radius: 20px;
                cursor: pointer;
                transition: background 0.3s, transform 0.1s;
                font-weight: 600;
                margin-bottom: 24px;
                display: inline-block;
                box-shadow: 0 2px 8px #b2ebf2;
            }}
            .back-button:hover {{
                background: linear-gradient(90deg, #546e7a 60%, #90a4ae 100%);
                transform: translateY(-2px) scale(1.04);
            }}
            .back-button:active {{
                transform: translateY(0);
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(-10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            /* Decoración especial para el select de estudiantes */
            .select-estudiante-wrapper {{
                position: relative;
                display: flex;
                align-items: center;
            }}
            .select-estudiante-wrapper i {{
                position: absolute;
                left: 14px;
                color: #4dd0e1;
                font-size: 1.2em;
                pointer-events: none;
                z-index: 2;
                top: 50%;
                transform: translateY(-50%);
                filter: drop-shadow(0 1px 2px #b2ebf2);
            }}
            .select-estudiante {{
                width: 100%;
                padding-left: 38px !important;
                background: linear-gradient(90deg, #e0f7fa 60%, #fff 100%);
                border-radius: 8px;
                border: 1.5px solid #4dd0e1;
                font-size: 1em;
                transition: border-color 0.3s, box-shadow 0.3s;
                appearance: none;
                -webkit-appearance: none;
                -moz-appearance: none;
                box-shadow: 0 2px 8px #e0f7fa33;
                min-height: 44px;
                color: #0077cc;
                font-weight: 500;
            }}
            .select-estudiante:focus {{
                border-color: #0077cc;
                box-shadow: 0 0 10px #b2ebf2;
                outline: none;
                background: linear-gradient(90deg, #b2ebf2 60%, #fff 100%);
            }}
            .select-estudiante option {{
                color: #0077cc;
                background: #f7fafc;
                font-weight: 400;
            }}

            /* Estilos para el select2 */
            .select2-container--default .select2-selection--single {{
    background: linear-gradient(90deg, #e0f7fa 60%, #fff 100%);
    border-radius: 8px;
    border: 1.5px solid #4dd0e1;
    min-height: 44px;
    color: #0077cc;
    font-weight: 500;
    font-size: 1em;
    padding-left: 30px;
}}
.select2-container--default .select2-selection--single:focus {{
    border-color: #0077cc;
    box-shadow: 0 0 10px #b2ebf2;
}}
.select2-container--default .select2-results__option--highlighted[aria-selected] {{
    background: #b2ebf2;
    color: #0077cc;
}}
.select2-container--default .select2-selection--single .select2-selection__arrow {{
    height: 44px;
}}
        </style>
        <script>
            // Mostrar/ocultar formularios de crear/actualizar
            function toggleForm(id, display = 'block') {{
                document.querySelectorAll('.formulario').forEach(function(f) {{ f.style.display = 'none'; }});
                const formElement = document.getElementById(id);
                if (display === 'block') {{
                    formElement.style.display = 'block';
                }} else {{
                    formElement.style.display = 'none';
                }}
            }}

            // Rellenar formulario de edición con los valores seleccionados
            function openEditForm(id, estudianteId, etapaId, tutorId, revisorId, primeraEntregaEstado, fechaPrimeraEntrega, segundaEntregaEstado, fechaSegundaEntrega) {{
                toggleForm('actualizar');
                document.getElementById('update_id_monitoreo').value = id;
                document.getElementById('update_id_estudiante').value = estudianteId;
                document.getElementById('update_id_etapa').value = etapaId;
                document.getElementById('update_id_tutor').value = tutorId;
                document.getElementById('update_id_revisor').value = revisorId;
                document.getElementById('update_primera_entrega_estado').value = primeraEntregaEstado;
                document.getElementById('update_fecha_primera_entrega').value = fechaPrimeraEntrega;
                document.getElementById('update_segunda_entrega_estado').value = segundaEntregaEstado;
                document.getElementById('update_fecha_segunda_entrega').value = fechaSegundaEntrega;
            }}

            // Confirmación antes de eliminar
            function confirmDelete(id) {{
                if (confirm('¿Estás seguro de que deseas eliminar este registro?')) {{
                    const form = document.createElement('form');
                    form.method = 'post';
                    form.style.display = 'none';

                    const accionInput = document.createElement('input');
                    accionInput.type = 'hidden';
                    accionInput.name = 'accion';
                    accionInput.value = 'eliminar';
                    form.appendChild(accionInput);

                    const idInput = document.createElement('input');
                    idInput.type = 'hidden';
                    idInput.name = 'id_monitoreo';
                    idInput.value = id;
                    form.appendChild(idInput);

                    document.body.appendChild(form);
                    form.submit();
                }}
            }}

            // Mostrar mensaje si existe
            window.onload = function() {{
                const messageDiv = document.getElementById('message-area');
                const messageText = messageDiv.innerText.trim();
                if (messageText) {{
                    messageDiv.style.display = 'block';
                }}
            }};

            // Inicializar select2 en selects de estudiante
            $(document).ready(function() {{
                $('#id_estudiante').select2({{
                    width: '100%',
                    placeholder: "Seleccione Estudiante"
                }});
                $('#update_id_estudiante').select2({{
                    width: '100%',
                    placeholder: "Seleccione Estudiante"
                }});
            }});
        </script>
    </head>
    <body>
        <!-- Botón para salir / volver -->
        <button class="back-button" type="button" onclick="window.location.href='/menu'" style="margin-bottom:18px;">Volver al Menú</button>
        <div class="container">
            <div class="header">
                <i class="fa-solid fa-graduation-cap"></i>
                <h2>Monitoreo de Titulación</h2>
            </div>

            <!-- Área de mensajes (éxito/error) -->
            <div id="message-area" class="message-area {'success' if success_message and 'exitosamente' in success_message else 'error' if error_message else ''}" style="display: {'block' if success_message or error_message else 'none'};">
                {success_message or error_message}
            </div>

            <!-- Botón para abrir formulario de creación -->
            <div class="action-buttons">
                <button onclick="toggleForm('crear')">Crear Nuevo Registro</button>
            </div>

            <!-- Formulario de creación (oculto por defecto) -->
            <div class="formulario" id="crear">
                <h3>Crear Nuevo Registro</h3>
                <form method="post">
                    <input type="hidden" name="accion" value="crear">
                    <label>Estudiante:</label>
                    <select name="id_estudiante" id="id_estudiante" required>
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{e[0]}">{e[0]} - {e[1]}</option>' for e in estudiantes])}
                    </select>
                    <label>Etapa:</label>
                    <select name="id_etapa" required>
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{et[0]}">{et[1]}</option>' for et in etapas])}
                    </select>
                    <label>Tutor:</label>
                    <select name="id_tutor" required>
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{d[0]}">{d[1]}</option>' for d in docentes])}
                    </select>
                    <label>Revisor:</label>
                    <select name="id_revisor">
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{d[0]}">{d[1]}</option>' for d in docentes])}
                    </select>
                    <label>1ra Entrega Estado:</label>
                    <select name="primera_entrega_estado" required>
                        <option value="">Seleccione</option>
                        <option value="completado">Completado</option>
                        <option value="falta">Falta</option>
                    </select>
                    <label>Fecha 1ra Entrega:</label>
                    <input type="date" name="fecha_primera_entrega">
                    <label>2da Entrega Estado:</label>
                    <select name="segunda_entrega_estado" required>
                        <option value="">Seleccione</option>
                        <option value="completado">Completado</option>
                        <option value="falta">Falta</option>
                    </select>
                    <label>Fecha 2da Entrega:</label>
                    <input type="date" name="fecha_segunda_entrega">
                    <label>Estado Etapa:</label>
                    <input type="text" name="estado_etapa" value="Automático" readonly style="background:#e0e0e0; color:#888; border:1px solid #b0bec5; cursor:not-allowed;">
                    <div class="cancel-button" style="grid-column: span 2; text-align:center;">
                        <button type="button" onclick="toggleForm('crear', 'none')">Cancelar</button>
                        <button type="submit" style="margin-left:10px;">Guardar</button>
                    </div>
                </form>
            </div>

            <!-- Formulario de edición (oculto por defecto) -->
            <div class="formulario" id="actualizar">
                <h3>Editar Registro</h3>
                <form method="post">
                    <input type="hidden" name="accion" value="actualizar">
                    <input type="hidden" name="id_monitoreo" id="update_id_monitoreo">
                    <label>Estudiante:</label>
                    <select name="id_estudiante" id="update_id_estudiante" required>
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{e[0]}">{e[0]} - {e[1]}</option>' for e in estudiantes])}
                    </select>
                    <label>Etapa:</label>
                    <select name="id_etapa" id="update_id_etapa" required>
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{et[0]}">{et[1]}</option>' for et in etapas])}
                    </select>
                    <label>Tutor:</label>
                    <select name="id_tutor" id="update_id_tutor" required>
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{d[0]}">{d[1]}</option>' for d in docentes])}
                    </select>
                    <label>Revisor:</label>
                    <select name="id_revisor" id="update_id_revisor">
                        <option value="">Seleccione</option>
                        {''.join([f'<option value="{d[0]}">{d[1]}</option>' for d in docentes])}
                    </select>
                    <label>1ra Entrega Estado:</label>
                    <select name="primera_entrega_estado" id="update_primera_entrega_estado" required>
                        <option value="">Seleccione</option>
                        <option value="completado">Completado</option>
                        <option value="falta">Falta</option>
                    </select>
                    <label>Fecha 1ra Entrega:</label>
                    <input type="date" name="fecha_primera_entrega" id="update_fecha_primera_entrega">
                    <label>2da Entrega Estado:</label>
                    <select name="segunda_entrega_estado" id="update_segunda_entrega_estado" required>
                        <option value="">Seleccione</option>
                        <option value="completado">Completado</option>
                        <option value="falta">Falta</option>
                    </select>
                    <label>Fecha 2da Entrega:</label>
                    <input type="date" name="fecha_segunda_entrega" id="update_fecha_segunda_entrega">
                    <label>Estado Etapa:</label>
                    <input type="text" name="estado_etapa" id="update_estado_etapa" value="Automático" readonly style="background:#e0e0e0; color:#888; border:1px solid #b0bec5; cursor:not-allowed;">
                    <div class="cancel-button" style="grid-column: span 2; text-align:center;">
                        <button type="button" onclick="toggleForm('actualizar', 'none')">Cancelar</button>
                        <button type="submit" style="margin-left:10px;">Actualizar</button>
                    </div>
                </form>
            </div>

            <!-- Tabla de registros -->
            <div class="tabla-wrapper">
                <table>
                    <tr>
    '''
    for _, titulo in columnas_tabla:
        html += f"<th>{titulo}</th>"
    html += "<th>Acciones</th></tr>"

    for r in registros:
        html += "<tr>"
        html += f"<td>{r[0]}</td>"   
        html += f"<td>{r[2]}</td>"   
        html += f"<td>{r[4]}</td>"   
        html += f"<td>{r[6]}</td>"   
        html += f"<td>{r[8]}</td>"   
        html += f"<td>{r[10]}</td>"  
        html += f"<td>{r[11].strftime('%Y-%m-%d') if r[11] else '-'}</td>"  
        html += f"<td>{r[12]}</td>"  
        html += f"<td>{r[13].strftime('%Y-%m-%d') if r[13] else '-'}</td>"  

        val = r[9]
        clase_estado = ""
        if val == "completado":
            clase_estado = "estado-completado"
        elif val == "en_proceso":
            clase_estado = "estado-en_proceso"
        elif val == "pendiente":
            clase_estado = "estado-pendiente"
        html += f"<td class='{clase_estado}' style='font-size:1.1em; text-align:center;'>{val.capitalize()}</td>"

        if val == "completado":
            pre_defensa = "<span style='background:#43a047;color:#fff;padding:6px 16px;border-radius:12px;font-weight:700;'>Habilitado</span>"
        else:
            pre_defensa = "<span style='background:#ef5350;color:#fff;padding:6px 16px;border-radius:12px;font-weight:700;'>Inhabilitado</span>"
        html += f"<td style='text-align:center;'>{pre_defensa}</td>"

        html += f'''
            <td class="action-cell">
                <button class="edit-button" onclick="openEditForm(
                    '{r[0]}', '{r[1]}', '{r[3]}', '{r[5]}', '{r[7]}',
                    '{r[10]}', '{r[11] if r[11] else ""}', '{r[12]}', '{r[13] if r[13] else ""}'
                )">Editar</button>
                <button class="delete-button" onclick="confirmDelete('{r[0]}')">Eliminar</button>
            </td>
        </tr>
        '''
    html += '''
            </table>
        </div>
    </body>
    </html>
    '''
    return HttpResponse(html)

urlpatterns = [
    path('', monitoreo_titulacion_view),
    path('monitoreo_titulacion', monitoreo_titulacion_view),
]

if __name__ == "__main__":
    import sys
    from django.core.management import execute_from_command_line
    import django
    from django.conf import settings
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY='secret-key',
            ROOT_URLCONF=__name__,
            ALLOWED_HOSTS=['*'],
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.staticfiles',
            ],
            TEMPLATES=[
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [],
                },
            ],
            STATIC_URL='/static/',
            STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')],
        )
    django.setup()
    execute_from_command_line([sys.argv[0], "runserver", "8000"])
