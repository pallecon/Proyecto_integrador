from django.http import HttpResponse
from django.urls import path
from conexion import crear_conexion

# ============ FUNCIONES AUXILIARES ============

def calcular_estado_etapa(primera, segunda):
    """Calcula el estado de la etapa basado en las entregas."""
    if primera == "completado" and segunda == "completado":
        return "completado"
    elif (primera == "completado" and segunda == "falta") or (primera == "falta" and segunda == "completado"):
        return "en_proceso"
    elif primera == "falta" and segunda == "falta":
        return "pendiente"
    return "pendiente"

def obtener_datos_base(cursor):
    """Obtiene estudiantes, etapas y docentes de la BD."""
    cursor.execute("SELECT id_estudiante, nombre FROM Estudiantes")
    estudiantes = cursor.fetchall()
    
    cursor.execute("SELECT id_etapa, nombre_etapa FROM Etapas_Titulacion")
    etapas = cursor.fetchall()
    
    cursor.execute("SELECT id_docente, nombre FROM Docentes")
    docentes = cursor.fetchall()
    
    return estudiantes, etapas, docentes

def obtener_registros(cursor):
    """Obtiene todos los registros de monitoreo de titulación."""
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
    cursor.execute(select_sql)
    return cursor.fetchall()

def procesar_accion(request, cursor, conexion):
    """Procesa las acciones POST (crear, actualizar, eliminar)."""
    success_message = ""
    error_message = ""
    accion = request.POST.get("accion")
    
    try:
        if accion == "crear":
            success_message, error_message = _crear_registro(request, cursor, conexion)
        elif accion == "actualizar":
            success_message, error_message = _actualizar_registro(request, cursor, conexion)
        elif accion == "eliminar":
            success_message, error_message = _anular_registro(request, cursor, conexion)
    except Exception as e:
        error_message = f"Error procesando acción: {e}"
    
    return success_message, error_message

def _crear_registro(request, cursor, conexion):
    """Crea un nuevo registro de monitoreo."""
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
            INSERT INTO Monitoreo_Titulacion ({', '.join(campos)})
            VALUES ({', '.join(['%s'] * len(campos))})
        """, valores)
        conexion.commit()
        return "✓ Registro creado exitosamente", ""
    except Exception as e:
        return "", f"✗ Error al crear registro: {e}"

def _actualizar_registro(request, cursor, conexion):
    """Actualiza un registro existente."""
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
        return "✓ Registro actualizado exitosamente", ""
    except Exception as e:
        return "", f"✗ Error al actualizar registro: {e}"

def _anular_registro(request, cursor, conexion):
    """Anula un registro (marca como anulado)."""
    id_monitoreo = request.POST.get("id_monitoreo")
    
    try:
        cursor.execute("""
            UPDATE Monitoreo_Titulacion
            SET estado_etapa = %s
            WHERE id_monitoreo = %s
        """, ('anulado', id_monitoreo))
        conexion.commit()
        return "✓ Registro anulado exitosamente", ""
    except Exception as e:
        return "", f"✗ Error al anular registro: {e}"

# ============ VISTAS HTML ============

def generar_html_formularios(estudiantes, etapas, docentes):
    """Genera el HTML de los formularios."""
    return f'''
        <!-- Modal Crear -->
        <div class="modal" id="modalCrear">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="header-title">
                        <i class="fas fa-plus-circle"></i> 
                        <h2>Crear Nuevo Registro</h2>
                    </div>
                    <button class="modal-close" onclick="closeModal('modalCrear')">&times;</button>
                </div>
                <form method="post" class="form-elegante">
                    <input type="hidden" name="accion" value="crear">
                    {_generar_campos_formulario(estudiantes, etapas, docentes, "crear")}
                    <div class="form-buttons">
                        <button type="button" class="btn-cancel" onclick="closeModal('modalCrear')">Cancelar</button>
                        <button type="submit" class="btn-submit">Guardar Registro</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal Actualizar -->
        <div class="modal" id="modalActualizar">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="header-title">
                        <i class="fas fa-edit"></i>
                        <h2>Editar Registro</h2>
                    </div>
                    <button class="modal-close" onclick="closeModal('modalActualizar')">&times;</button>
                </div>
                <form method="post" class="form-elegante">
                    <input type="hidden" name="accion" value="actualizar">
                    <input type="hidden" name="id_monitoreo" id="update_id_monitoreo">
                    {_generar_campos_formulario(estudiantes, etapas, docentes, "update")}
                    <div class="form-buttons">
                        <button type="button" class="btn-cancel" onclick="closeModal('modalActualizar')">Cancelar</button>
                        <button type="submit" class="btn-submit">Actualizar Registro</button>
                    </div>
                </form>
            </div>
        </div>
    '''

def _generar_campos_formulario(estudiantes, etapas, docentes, prefijo=""):
    """Genera los campos del formulario."""
    id_prefijo = f"{prefijo}_" if prefijo else ""
    
    opciones_estudiantes = ''.join([f'<option value="{e[0]}">{e[1]}</option>' for e in estudiantes])
    opciones_etapas = ''.join([f'<option value="{et[0]}">{et[1]}</option>' for et in etapas])
    opciones_docentes = ''.join([f'<option value="{d[0]}">{d[1]}</option>' for d in docentes])
    
    return f'''
        <div class="form-group">
            <div class="form-field">
                <label>Estudiante *</label>
                <select name="id_estudiante" id="{id_prefijo}id_estudiante" required>
                    <option value="">Seleccione un estudiante</option>
                    {opciones_estudiantes}
                </select>
            </div>
            <div class="form-field">
                <label>Etapa *</label>
                <select name="id_etapa" id="{id_prefijo}id_etapa" required>
                    <option value="">Seleccione una etapa</option>
                    {opciones_etapas}
                </select>
            </div>
        </div>
        <div class="form-group">
            <div class="form-field">
                <label>Tutor *</label>
                <select name="id_tutor" id="{id_prefijo}id_tutor" required>
                    <option value="">Seleccione un tutor</option>
                    {opciones_docentes}
                </select>
            </div>
            <div class="form-field">
                <label>Revisor</label>
                <select name="id_revisor" id="{id_prefijo}id_revisor">
                    <option value="">Seleccione un revisor</option>
                    {opciones_docentes}
                </select>
            </div>
        </div>
        <div class="form-group">
            <div class="form-field">
                <label>1ra Entrega Estado *</label>
                <select name="primera_entrega_estado" id="{id_prefijo}primera_entrega_estado" required>
                    <option value="">Seleccione</option>
                    <option value="completado">Completado</option>
                    <option value="falta">Falta</option>
                </select>
            </div>
            <div class="form-field">
                <label>Fecha 1ra Entrega</label>
                <input type="date" name="fecha_primera_entrega" id="{id_prefijo}fecha_primera_entrega">
            </div>
        </div>
        <div class="form-group">
            <div class="form-field">
                <label>2da Entrega Estado *</label>
                <select name="segunda_entrega_estado" id="{id_prefijo}segunda_entrega_estado" required>
                    <option value="">Seleccione</option>
                    <option value="completado">Completado</option>
                    <option value="falta">Falta</option>
                </select>
            </div>
            <div class="form-field">
                <label>Fecha 2da Entrega</label>
                <input type="date" name="fecha_segunda_entrega" id="{id_prefijo}fecha_segunda_entrega">
            </div>
        </div>
    '''

def generar_fila_tabla(r):
    """Genera una fila de la tabla de registros."""
    estado_actual = r[9]
    fila_clase = "anulado-row" if estado_actual == "anulado" else ""
    
    primera_estado = r[10] or "-"
    fecha_primera = r[11].strftime('%d/%m/%Y') if r[11] else '-'
    
    segunda_estado = r[12] or "-"
    fecha_segunda = r[13].strftime('%d/%m/%Y') if r[13] else '-'
    
    clase_estado = f"estado-{estado_actual}" if estado_actual in ["completado", "en_proceso", "pendiente"] else ("estado-anulado" if estado_actual == "anulado" else "estado-pendiente")
    label_estado = estado_actual.replace('_', ' ').capitalize() if estado_actual != "anulado" else "Anulado"
    
    pre_defensa = '<span class="badge badge-success">Habilitado</span>' if estado_actual == "completado" else '<span class="badge badge-danger">No Habilitado</span>'
    
    editar_disabled = "disabled" if estado_actual == "anulado" else ""
    editar_cursor = "style='opacity:0.6;pointer-events:none;'" if estado_actual == "anulado" else ""
    
    return f'''
        <tr class='{fila_clase}'>
            <td><strong>{r[2]}</strong></td>
            <td>{r[4]}</td>
            <td>{r[6]}</td>
            <td>{r[8]}</td>
            <td class="fecha-entrega">{primera_estado.capitalize()}<br><small>{fecha_primera}</small></td>
            <td class="fecha-entrega">{segunda_estado.capitalize()}<br><small>{fecha_segunda}</small></td>
            <td><span class='{clase_estado}'>{label_estado}</span></td>
            <td style='text-align:center;'>{pre_defensa}</td>
            <td class="action-cell">
                <button class="btn-edit" onclick="openEditForm('{r[0]}', '{r[1]}', '{r[3]}', '{r[5]}', '{r[7]}', '{r[10]}', '{r[11] if r[11] else ""}', '{r[12]}', '{r[13] if r[13] else ""}')" title="Editar" {editar_disabled} {editar_cursor}><i class="fas fa-edit"></i></button>
                <button class="btn-delete" onclick="confirmAnular('{r[0]}')" title="Anular"><i class="fas fa-ban"></i></button>
            </td>
        </tr>
    '''

def _generar_estilos_css():
    """Retorna el CSS estilizado con creatividad."""
    return '''
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            :root {
                --primary: #0f3460; --primary-dark: #051e3e; --primary-light: #16547a;
                --secondary: #533483; --success: #43a047; --warning: #ffa726;
                --danger: #ef5350; --dark: #0a1929; --muted: #546e7a;
                --light: #ecf0f1; --border: #b0bec5;
                --shadow: 0 4px 12px rgba(0,0,0,0.15);
                --shadow-lg: 0 8px 24px rgba(0,0,0,0.25);
            }
            body { 
                font-family: 'Inter', sans-serif; 
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh; 
                color: var(--dark); 
                line-height: 1.6; 
            }
            .top-bar { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); 
                padding: 16px 32px; 
                box-shadow: var(--shadow-lg);
                border-bottom: 5px solid #1e5a96;
                position: sticky; 
                top: 0; 
                z-index: 100;
                gap: 30px;
            }
            .top-title {
                flex: 1;
                text-align: right;
                color: #ffffff;
                font-size: 1.8em;
                font-weight: 700;
                margin: 0;
                letter-spacing: 0.8px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                padding-right: 20px;
            }
            .back-button { 
                display: inline-flex; 
                align-items: center; 
                gap: 8px; 
                background: rgba(255, 255, 255, 0.15); 
                color: #ffffff; 
                padding: 10px 20px; 
                border-radius: 8px; 
                border: 2px solid rgba(255, 255, 255, 0.3); 
                cursor: pointer; 
                font-weight: 600; 
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
            }
            .back-button:hover { 
                background: rgba(255, 255, 255, 0.25);
                transform: translateX(-4px); 
                box-shadow: var(--shadow-lg); 
                border-color: #ffffff;
            }
            .container { 
                max-width: 1400px; 
                margin: 0 auto; 
                padding: 32px 20px 40px 20px; 
            }
            .action-buttons { 
                display: flex; 
                justify-content: flex-end; 
                margin-bottom: 28px; 
                gap: 12px; 
            }
            .btn { 
                padding: 12px 24px; 
                border-radius: 8px; 
                border: none; 
                cursor: pointer; 
                font-weight: 600; 
                transition: all 0.3s; 
                display: inline-flex; 
                align-items: center; 
                gap: 8px; 
                font-size: 0.95em; 
                box-shadow: var(--shadow);
            }
            .btn-primary { 
                background: linear-gradient(135deg, #0f3460 0%, #1e5a96 100%); 
                color: white; 
                border: 2px solid #ffffff;
            }
            .btn-primary:hover { 
                transform: translateY(-3px); 
                box-shadow: var(--shadow-lg);
            }
            .message-area { 
                padding: 16px 20px; 
                border-radius: 12px; 
                margin-bottom: 24px; 
                font-weight: 600; 
                display: none; 
                align-items: center; 
                gap: 12px; 
                animation: slideDown 0.3s;
                backdrop-filter: blur(10px);
            }
            .message-area.success { 
                background: rgba(27, 94, 32, 0.9); 
                color: #81c784; 
                border-left: 5px solid #43a047; 
                display: flex; 
            }
            .message-area.error { 
                background: rgba(183, 28, 28, 0.9); 
                color: #ef9a9a; 
                border-left: 5px solid #ef5350; 
                display: flex; 
            }
            @keyframes slideDown { 
                from { opacity: 0; transform: translateY(-10px); } 
                to { opacity: 1; transform: translateY(0); } 
            }
            
            /* Modal Styles */
            .modal { 
                display: none; 
                position: fixed; 
                top: 0; 
                left: 0; 
                width: 100%; 
                height: 100%; 
                background: rgba(0, 0, 0, 0.6); 
                z-index: 1000; 
                justify-content: center; 
                align-items: center;
                backdrop-filter: blur(5px);
            }
            .modal.show { display: flex; }
            .modal-content { 
                background: #ffffff; 
                padding: 0; 
                border-radius: 16px; 
                box-shadow: 0 10px 40px rgba(0,0,0,0.3); 
                border: none; 
                max-width: 600px; 
                width: 90%; 
                max-height: 90vh; 
                overflow-y: auto; 
                animation: modalSlideIn 0.3s;
            }
            @keyframes modalSlideIn { 
                from { transform: scale(0.8) translateY(-50px); opacity: 0; } 
                to { transform: scale(1) translateY(0); opacity: 1; } 
            }
            .modal-header { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                padding: 24px; 
                border-bottom: 3px solid #f0f0f0; 
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }
            .header-title {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .modal-header h2 { 
                color: #0f3460; 
                font-size: 1.3em; 
                margin: 0;
            }
            .modal-header i {
                color: #1e5a96;
                font-size: 1.5em;
            }
            .modal-close { 
                background: none; 
                border: none; 
                color: #0f3460; 
                font-size: 2em; 
                cursor: pointer; 
                transition: all 0.3s;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
            }
            .modal-close:hover { 
                color: #ef5350;
                background: rgba(239, 83, 80, 0.1);
                transform: rotate(90deg);
            }
            
            /* Form Styles */
            .form-elegante {
                padding: 24px;
            }
            .form-group { 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 20px; 
                margin-bottom: 20px;
            }
            .form-group.full { grid-column: span 2; }
            .form-field { 
                display: flex; 
                flex-direction: column; 
            }
            .form-field label { 
                font-weight: 600; 
                color: #0f3460; 
                margin-bottom: 8px; 
                font-size: 0.95em;
            }
            .form-field input, .form-field select { 
                padding: 12px; 
                border: 2px solid #e0e0e0; 
                border-radius: 8px; 
                font-size: 0.95em; 
                font-family: inherit; 
                transition: all 0.3s; 
                background: #ffffff; 
                color: #0a1929;
            }
            .form-field input::placeholder { color: #9e9e9e; }
            .form-field input:focus, .form-field select:focus { 
                border-color: #0f3460; 
                box-shadow: 0 0 0 4px rgba(15, 52, 96, 0.1); 
                outline: none;
            }
            .form-buttons { 
                display: flex; 
                gap: 12px; 
                justify-content: center; 
                padding: 24px; 
                border-top: 2px solid #f0f0f0;
            }
            .btn-submit { 
                background: linear-gradient(135deg, #0f3460 0%, #1e5a96 100%); 
                color: white; 
                border: none; 
                padding: 12px 28px; 
                border-radius: 8px; 
                cursor: pointer; 
                font-weight: 600;
                transition: all 0.3s;
            }
            .btn-submit:hover { 
                transform: translateY(-3px); 
                box-shadow: var(--shadow-lg);
            }
            .btn-cancel { 
                background: #f0f0f0; 
                color: #0f3460; 
                border: 2px solid #e0e0e0; 
                padding: 12px 28px; 
                border-radius: 8px; 
                cursor: pointer; 
                font-weight: 600;
                transition: all 0.3s;
            }
            .btn-cancel:hover { 
                background: #e8e8e8;
                border-color: #0f3460;
            }
            
            /* Table Styles */
            .tabla-wrapper { 
                background: #ffffff; 
                border-radius: 16px; 
                box-shadow: var(--shadow-lg); 
                overflow: hidden; 
                border: none;
            }
            table { 
                width: 100%; 
                border-collapse: collapse; 
            }
            thead { 
                background: linear-gradient(135deg, #0f3460 0%, #1e5a96 100%); 
                color: #ffffff; 
                border-bottom: 3px solid #1e5a96; 
            }
            th { 
                padding: 18px 12px; 
                text-align: left; 
                font-weight: 700; 
                font-size: 0.9em; 
                color: #ffffff;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            td { 
                padding: 16px 12px; 
                border-bottom: 1px solid #f0f0f0; 
                color: #0a1929;
            }
            td strong {
                color: #0f3460;
            }
            .fecha-entrega small {
                color: #546e7a;
                font-size: 0.85em;
            }
            tbody tr { 
                transition: all 0.3s ease; 
            }
            tbody tr:hover { 
                background: linear-gradient(90deg, rgba(15, 52, 96, 0.05) 0%, rgba(30, 90, 150, 0.05) 100%);
                transform: scale(1.01);
            }
            .anulado-row { opacity: 0.5; filter: grayscale(1); }
            .estado-anulado { 
                background: #9e9e9e; 
                color: #ffffff; 
                padding: 6px 12px; 
                border-radius: 6px; 
                font-weight: 700; 
                font-size: 0.85em; 
            }
            .estado-completado { 
                background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%); 
                color: #81c784; 
                padding: 6px 12px; 
                border-radius: 6px; 
                font-weight: 700;
            }
            .estado-en_proceso { 
                background: linear-gradient(135deg, #ff6f00 0%, #f57c00 100%); 
                color: #ffe0b2; 
                padding: 6px 12px; 
                border-radius: 6px; 
                font-weight: 700; 
            }
            .estado-pendiente { 
                background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%); 
                color: #bbdefb; 
                padding: 6px 12px; 
                border-radius: 6px; 
                font-weight: 700; 
            }
            .badge { 
                display: inline-block; 
                padding: 8px 16px; 
                border-radius: 20px; 
                font-weight: 700;
                font-size: 0.9em;
            }
            .badge-success { 
                background: linear-gradient(135deg, #1b5e20 0%, #43a047 100%); 
                color: #ffffff; 
            }
            .badge-danger { 
                background: linear-gradient(135deg, #b71c1c 0%, #d71c1c 100%); 
                color: #ffffff; 
            }
            .action-cell { 
                display: flex; 
                gap: 10px; 
                justify-content: center; 
            }
            .btn-edit, .btn-delete { 
                padding: 8px 14px; 
                border-radius: 6px; 
                border: none; 
                cursor: pointer; 
                font-weight: 600; 
                font-size: 0.85em; 
                transition: all 0.3s;
            }
            .btn-edit { 
                background: linear-gradient(135deg, #6d4c41 0%, #8d5c41 100%); 
                color: #ffb74d; 
            }
            .btn-edit:hover { 
                transform: scale(1.1) rotate(5deg); 
                box-shadow: var(--shadow);
            }
            .btn-delete { 
                background: linear-gradient(135deg, #b71c1c 0%, #d71c1c 100%); 
                color: #ffffff; 
            }
            .btn-delete:hover { 
                transform: scale(1.1) rotate(-5deg); 
                box-shadow: var(--shadow);
            }
            
            @media (max-width: 768px) {
                .form-group { grid-template-columns: 1fr; }
                .modal-content { width: 95%; }
                th, td { padding: 10px 6px; font-size: 0.9em; }
                .top-bar { flex-direction: column; gap: 12px; padding: 12px; }
                .action-buttons { justify-content: center; }
            }

            .top-title {
                flex: 1;
                text-align: right;
                color: #ffffff;
                font-size: 1.8em;
                font-weight: 700;
                margin: 0;
                letter-spacing: 0.8px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                padding-right: 20px;
            }
        </style>
    '''


def monitoreo_titulacion_view(request):
    """Vista principal del monitoreo de titulación."""
    conexion = crear_conexion('localhost', 'root', '/73588144/', 'proyecto')
    cursor = conexion.cursor()

    success_message = ""
    error_message = ""

    if request.method == "POST":
        success_message, error_message = procesar_accion(request, cursor, conexion)

    estudiantes, etapas, docentes = obtener_datos_base(cursor)
    registros = obtener_registros(cursor)

    filas_tabla = ''.join([generar_fila_tabla(r) for r in registros])

    html = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Monitoreo de Titulación - Salesiana</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
        <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
        {_generar_estilos_css()}
    </head>
    <body>
        <div class="top-bar">
            <button class="back-button" onclick="window.location.href='/menu'">
                <i class="fas fa-arrow-left"></i>
                Volver al Menú
            </button>
            <h1 class="top-title">Modalidad de Titulación</h1>
        </div>

        <div class="container">
            <div id="message-area" class="message-area {'success' if success_message else ('error' if error_message else '')}">
                <i class="fas {'fa-check-circle' if success_message else 'fa-exclamation-circle' if error_message else ''}"></i>
                <span>{success_message or error_message}</span>
            </div>

            <div class="action-buttons">
                <button class="btn btn-primary" onclick="openModal('modalCrear')">
                    <i class="fas fa-plus"></i>
                    Crear Nuevo Registro
                </button>
            </div>

            {generar_html_formularios(estudiantes, etapas, docentes)}

            <!-- Tabla de registros -->
            <div class="tabla-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Estudiante</th>
                            <th>Etapa</th>
                            <th>Tutor</th>
                            <th>Revisor</th>
                            <th>1ra Entrega</th>
                            <th>2da Entrega</th>
                            <th>Estado</th>
                            <th>Pre Defensa</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_tabla}
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            function openModal(id) {{
                const modal = document.getElementById(id);
                modal.classList.add('show');
            }}

            function closeModal(id) {{
                const modal = document.getElementById(id);
                modal.classList.remove('show');
            }}

            function openEditForm(id, estudianteId, etapaId, tutorId, revisorId, primeraEntregaEstado, fechaPrimeraEntrega, segundaEntregaEstado, fechaSegundaEntrega) {{
                openModal('modalActualizar');
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

            function confirmAnular(id) {{
                if (confirm('¿Está seguro de anular este registro?')) {{
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

            // Cerrar modal al hacer click fuera
            window.addEventListener('click', function(event) {{
                if (event.target.classList.contains('modal')) {{
                    event.target.classList.remove('show');
                }}
            }});

            window.onload = function() {{
                const messageDiv = document.getElementById('message-area');
                if (messageDiv.innerText.trim()) {{
                    messageDiv.style.display = 'flex';
                    setTimeout(() => {{ messageDiv.style.display = 'none'; }}, 5000);
                }}

                $('#crear_id_estudiante, #update_id_estudiante').select2({{width: '100%'}});
            }};
        </script>
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
