import streamlit as st
import time
import os
import datetime
from streamlit_autorefresh import st_autorefresh
from chat_procesos import CorusIntranetEngine 

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="IA Corus - Procesos", page_icon="logo_corus.ico", layout="centered")

# --- 2. LECTURA DEL ESTADO GLOBAL DEL SERVIDOR (KILL SWITCH) ---
ARCHIVO_ESTADO = "estado_servidor.txt"
sitio_activo = True
if os.path.exists(ARCHIVO_ESTADO):
    with open(ARCHIVO_ESTADO, "r") as f:
        if f.read().strip() == "OFFLINE":
            sitio_activo = False

# --- 3. MOTOR DE AUDITORÍA Y LOGS ---
ARCHIVO_LOGS = "registro_conexiones.csv"

def registrar_acceso(usuario, rol):
    """Guarda la marca de tiempo, usuario y rol en un archivo CSV local."""
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario_limpio = usuario.replace(",", " ")
    with open(ARCHIVO_LOGS, "a", encoding="utf-8") as f:
        f.write(f"{ahora},{usuario_limpio},{rol}\n")

@st.dialog("👁️ Monitor de Accesos Corporativos")
def mostrar_monitor_conexiones():
    if os.path.exists(ARCHIVO_LOGS):
        with open(ARCHIVO_LOGS, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        
        datos = []
        for linea in reversed(lineas):
            partes = linea.strip().split(",")
            if len(partes) == 3:
                datos.append({"Fecha / Hora": partes[0], "Usuario": partes[1], "Rol": partes[2]})
        
        if datos:
            st.dataframe(datos, use_container_width=True, hide_index=True)
        else:
            st.info("El archivo de logs está vacío.")
    else:
        st.info("Aún no hay conexiones registradas en el sistema.")

# --- 4. INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "es_admin" not in st.session_state:
    st.session_state.es_admin = False
if "ultimo_acceso" not in st.session_state:
    st.session_state.ultimo_acceso = time.time()
if "dialogo_abierto" not in st.session_state:
    st.session_state.dialogo_abierto = False
if "historial_pantalla" not in st.session_state:
    st.session_state.historial_pantalla = []

# Tiempos límite de control de sesión
LIMITE_ADVERTENCIA = 300  
LIMITE_EXPULSION = 360    

# --- 5. DISEÑO DEL CUADRO DE DIÁLOGO DE INACTIVIDAD ---
@st.dialog("⚠️ Alerta de Inactividad")
def mostrar_ventana_caducidad():
    st.session_state.dialogo_abierto = True
    st.warning("Tu sesión está a punto de cerrarse por seguridad tras 5 minutos sin actividad.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Mantener en línea", use_container_width=True):
            st.session_state.ultimo_acceso = time.time()
            st.session_state.dialogo_abierto = False
            st.rerun()
    with col2:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.es_admin = False
            st.session_state.dialogo_abierto = False
            st.rerun()

# --- 6. SISTEMA DE LOGIN DE DOBLE CAPA ---
if not st.session_state.autenticado:
    st.title("🏢 Acceso Restringido")
    
    if not sitio_activo:
        st.error("⚠️ SISTEMA EN MANTENIMIENTO: La plataforma ha sido desactivada temporalmente.")

    with st.form("formulario_login"):
        usuario_input = st.text_input("Ingresa tu Nombre y Apellido:", placeholder="Ej. Sebastián Siabato")
        pwd = st.text_input("Contraseña de acceso:", type="password")
        btn_ingresar = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if btn_ingresar:
            if not usuario_input.strip() or not pwd:
                st.warning("Por favor, ingresa tu nombre y la contraseña para continuar.")
            else:
                if pwd == "Corus2026*":
                    if not sitio_activo:
                        st.error("Acceso denegado: El sistema está en mantenimiento.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        registrar_acceso(usuario_input.strip(), "Analista")
                        st.session_state.autenticado = True
                        st.session_state.es_admin = False
                        st.session_state.ultimo_acceso = time.time()
                        st.success(f"Bienvenido, {usuario_input}. Cargando...")
                        time.sleep(1)
                        st.rerun()
                        
                elif pwd == "AdminCorus2026*":
                    registrar_acceso(usuario_input.strip(), "Administrador")
                    st.session_state.autenticado = True
                    st.session_state.es_admin = True
                    st.session_state.ultimo_acceso = time.time()
                    st.success("⚙️ Acceso de Administrador concedido...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
    st.stop() 

# =====================================================================
# SISTEMA PRINCIPAL (SOLO VISIBLE CON ACCESO CONCEDIDO)
# =====================================================================

# --- 7. INICIALIZACIÓN DEL MOTOR IA ---
if "motor_ia" not in st.session_state:
    with st.spinner("Iniciando infraestructura y cargando datos corporativos..."):
        st.session_state.motor_ia = CorusIntranetEngine()

# --- 8. GUARDIÁN DE SESIÓN Y VIGILANTE DE MANTENIMIENTO ---
if "pensando" not in st.session_state:
    st.session_state.pensando = False

if not sitio_activo and not st.session_state.es_admin:
    st.session_state.autenticado = False
    st.session_state.dialogo_abierto = False
    st.rerun()

if not st.session_state.pensando:
    st_autorefresh(interval=30000, limit=None, key="reloj_sesion")

tiempo_actual = time.time()
inactividad = tiempo_actual - st.session_state.ultimo_acceso

if inactividad >= LIMITE_EXPULSION:
    st.session_state.autenticado = False
    st.session_state.es_admin = False
    st.session_state.dialogo_abierto = False
    st.rerun()
elif inactividad >= LIMITE_ADVERTENCIA:
    if not st.session_state.dialogo_abierto:
        mostrar_ventana_caducidad()

# --- 9. CSS: ESTILO CRISTAL Y DISEÑO ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none !important;}
    header {background: transparent !important;}

    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }

    .folder-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.3s ease;
    }
    .folder-card:hover {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        transform: translateX(5px);
    }
    .folder-icon { color: #60a5fa; font-size: 18px; }
    .folder-text {
        color: #e2e8f0; font-size: 14px; font-weight: 500;
        font-family: 'Urbanist', sans-serif;
    }

    .tip-container {
        background: rgba(59, 130, 246, 0.05);
        border-left: 3px solid #3b82f6;
        padding: 15px;
        border-radius: 5px;
        margin-top: 20px;
    }
    .tip-text { font-size: 13px; color: #94a3b8; line-height: 1.4; }

    div.stButton > button {
        background: rgba(128, 128, 128, 0.1) !important;
        color: #f8fafc !important; 
        font-weight: 500 !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 0.6rem !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 1px;
    }
    div.stButton > button:hover {
        background: rgba(128, 128, 128, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 10. CABECERA VISUAL ---
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_corus.png"):
        st.image("logo_corus.png", width='stretch')
    else:
        st.markdown("<h1 style='text-align: center;'>🏢</h1>", unsafe_allow_html=True)

with col2:
    st.title("Asistente Virtual")
    st.caption("Inteligencia de Procesos & Gestión del Conocimiento")
st.divider()

# --- 11. SIDEBAR: PANEL DE CONTROL ---
with st.sidebar:
    if st.session_state.es_admin:
        st.markdown("### 🚨 PANEL MAESTRO")
        if st.button("👁️ VER CONEXIONES", type="secondary"):
            mostrar_monitor_conexiones()
            
        if sitio_activo:
            if st.button("🔴 APAGAR SITIO", type="primary"):
                with open(ARCHIVO_ESTADO, "w") as f:
                    f.write("OFFLINE")
                st.rerun()
        else:
            st.error("El sitio está OFFLINE.")
            if st.button("🟢 ACTIVAR SITIO", type="primary"):
                if os.path.exists(ARCHIVO_ESTADO):
                    os.remove(ARCHIVO_ESTADO)
                st.rerun()
        st.markdown("---")

    st.markdown("### 🛠️ Configuración")
    st.markdown("---")
    
    # --- CLASIFICADOR DINÁMICO DE SUB-CARPETAS EN PRODUCCIÓN ---
    cat_parafiscales = []
    cat_pensiones = []
    cat_instrucciones = []
    cat_bpm = []
    
    if st.session_state.motor_ia.categorias:
        for cat in st.session_state.motor_ia.categorias:
            # Si el nombre coincide con la raíz o existe físicamente dentro de ella en el servidor
            if cat == "Manual Pensiones" or os.path.isdir(os.path.join("Manual Pensiones", cat)):
                cat_pensiones.append(cat)
            elif cat == "Instrucciones Adicionales" or os.path.isdir(os.path.join("Instrucciones Adicionales", cat)):
                cat_instrucciones.append(cat)
            elif cat == "Preguntas Adicionales BPM" or os.path.isdir(os.path.join("Preguntas Adicionales BPM", cat)):
                cat_bpm.append(cat)
            else:
                cat_parafiscales.append(cat)

    def renderizar_bloque_carpetas(lista_categorias, mensaje_vacio):
        """Función auxiliar para inyectar las carpetas con diseño cristal."""
        if lista_categorias:
            for cat in lista_categorias:
                st.markdown(f"""
                <div class="folder-card">
                    <span class="folder-icon">📂</span>
                    <span class="folder-text">{cat}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption(f"ℹ️ {mensaje_vacio}")

    # Renderizado ordenado de las 4 secciones solicitadas
    with st.expander("📚 Manuales Parafiscales", expanded=False):
        renderizar_bloque_carpetas(cat_parafiscales, "No hay subcarpetas indexadas.")
        
    with st.expander("📑 Manual Pensiones", expanded=False):
        renderizar_bloque_carpetas(cat_pensiones, "No hay subcarpetas indexadas.")
        
    with st.expander("📝 Instrucciones Adicionales", expanded=False):
        renderizar_bloque_carpetas(cat_instrucciones, "No hay subcarpetas indexadas.")
        
    with st.expander("⚙️ Preguntas Adicionales BPM", expanded=False):
        renderizar_bloque_carpetas(cat_bpm, "No hay subcarpetas indexadas.")
    
    st.markdown(f"""
    <div class="tip-container">
        <p class="tip-text">
            💡 <b>Tip Pro:</b> Escribe <i>"actualizar base"</i> en el chat para sincronizar 
            la IA automáticamente cuando subas nuevos manuales.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>" * 3, unsafe_allow_html=True)
    
    if st.button("🗑️ Limpiar Sesión"):
        st.session_state.historial_pantalla = []
        st.session_state.motor_ia.historial = []
        st.session_state.motor_ia.cat_actual = None
        st.session_state.ultimo_acceso = time.time()
        st.rerun()

    if st.button("🚪 Cerrar Acceso"):
        st.session_state.autenticado = False
        st.session_state.es_admin = False
        st.rerun()

# --- 12. ÁREA DE CHAT (LÓGICA RAG) ---
if not st.session_state.historial_pantalla:
    st.session_state.historial_pantalla = [{"rol": "assistant", "contenido": "¡Hola! Soy tu experto en flujos y procesos. ¿En qué puedo ayudarte hoy?"}]

for msg in st.session_state.historial_pantalla:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["contenido"])

if consulta := st.chat_input("Escribe tu consulta sobre flujos o manuales..."):
    st.session_state.ultimo_acceso = time.time()
    st.session_state.pensando = True 
    
    with st.chat_message("user"):
        st.markdown(consulta)
    st.session_state.historial_pantalla.append({"rol": "user", "contenido": consulta})

    with st.chat_message("assistant"):
        with st.spinner("Analizando documentación oficial..."):
            respuesta = st.session_state.motor_ia.procesar_consulta(consulta)
            st.markdown(respuesta)
    st.session_state.historial_pantalla.append({"rol": "assistant", "contenido": respuesta})
    
    st.session_state.pensando = False
    st.rerun()
