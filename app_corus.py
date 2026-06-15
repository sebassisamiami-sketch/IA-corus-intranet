import streamlit as st
import time
import os
import datetime
import glob
from streamlit_autorefresh import st_autorefresh
from chat_procesos import CorusIntranetEngine 

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="IA Corus - Procesos", page_icon="logo_corus2.png", layout="centered")

ARCHIVO_ESTADO = "estado_servidor.txt"
ARCHIVO_LOGS = "registro_conexiones.csv"

sitio_activo = True
if os.path.exists(ARCHIVO_ESTADO):
    with open(ARCHIVO_ESTADO, "r") as f:
        if f.read().strip() == "OFFLINE":
            sitio_activo = False

def registrar_acceso(usuario, rol):
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

# --- 2. SISTEMA DE SESIÓN AISLADA POR NAVEGADOR ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "rol_usuario" not in st.session_state: st.session_state.rol_usuario = "Analista"
if "es_admin" not in st.session_state: st.session_state.es_admin = False
if "ultimo_acceso" not in st.session_state: st.session_state.ultimo_acceso = time.time()
if "dialogo_abierto" not in st.session_state: st.session_state.dialogo_abierto = False
if "historial_pantalla" not in st.session_state: st.session_state.historial_pantalla = []
if "pensando" not in st.session_state: st.session_state.pensando = False

LIMITE_ADVERTENCIA = 300  
LIMITE_EXPULSION = 360    

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

# --- 3. CARGA GLOBAL Y ÚNICA DEL MOTOR (AHORRO DE MEMORIA) ---
@st.cache_resource(show_spinner=False)
def cargar_motor_central():
    return CorusIntranetEngine()

# --- 4. SISTEMA DE LOGIN DE DOBLE CAPA ---
if not st.session_state.autenticado:
    st.title("🏢 Acceso Restringido")
    if not sitio_activo:
        st.error("⚠️ SISTEMA EN MANTENIMIENTO: La plataforma ha sido desactivada temporalmente.")

    with st.form("formulario_login"):
        usuario_input = st.text_input("Ingresa tu Nombre y Apellido:", placeholder="Ej. Juan Pérez")
        pwd = st.text_input("Contraseña de acceso:", type="password")
        btn_ingresar = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if btn_ingresar:
            if not usuario_input.strip() or not pwd:
                st.warning("Por favor, ingresa tu nombre y la contraseña para continuar.")
            else:
                if pwd == "FarmeoAura*26*****":
                    if not sitio_activo:
                        st.error("Acceso denegado: El sistema está en mantenimiento.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        registrar_acceso(usuario_input.strip(), "Analista")
                        st.session_state.autenticado = True
                        st.session_state.rol_usuario = "Analista"
                        st.session_state.es_admin = False
                        st.session_state.ultimo_acceso = time.time()
                        st.success(f"Bienvenido, {usuario_input}. Cargando...")
                        time.sleep(1)
                        st.rerun()
                        
                elif pwd == "Pipeline**2038******":
                    registrar_acceso(usuario_input.strip(), "Administrador")
                    st.session_state.autenticado = True
                    st.session_state.rol_usuario = "Administrador"
                    st.session_state.es_admin = True
                    st.session_state.ultimo_acceso = time.time()
                    st.success("⚙️ Acceso de Administrador concedido...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
    st.stop() 

# =====================================================================
# SISTEMA PRINCIPAL (INTERFAZ AISLADA)
# =====================================================================

motor_ia = cargar_motor_central()

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

st.markdown("""
    <style>
    #MainMenu, footer, .stAppDeployButton {visibility: hidden; display: none !important;}
    header {background: transparent !important;}
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    .folder-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px 15px; border-radius: 10px; margin-bottom: 8px; display: flex; align-items: center; gap: 12px;
    }
    .folder-icon { color: #60a5fa; font-size: 18px; }
    .folder-text { color: #e2e8f0; font-size: 14px; font-weight: 500; font-family: 'Urbanist', sans-serif;}
    .tip-container { background: rgba(59, 130, 246, 0.05); border-left: 3px solid #3b82f6; padding: 15px; border-radius: 5px; margin-top: 20px;}
    .tip-text { font-size: 13px; color: #94a3b8; line-height: 1.4; }
    div.stButton > button {
        background: rgba(128, 128, 128, 0.1) !important; color: #f8fafc !important; font-weight: 500 !important;
        border-radius: 10px !important; border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 0.6rem !important; backdrop-filter: blur(10px) !important; text-transform: uppercase; font-size: 12px; letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_corus.png"):
        st.image("logo_corus.png", width='stretch')
    else:
        st.markdown("<h1 style='text-align: center;'>🏢</h1>", unsafe_allow_html=True)
with col2:
    st.title("Asistente Virtual Corus")
    st.caption(f"Inteligencia de Procesos | Sesión actual: **{st.session_state.rol_usuario}**")
st.divider()

with st.sidebar:
    if st.session_state.es_admin:
        st.markdown("### 🚨 PANEL MAESTRO")
        if st.button("👁️ VER CONEXIONES"):
            mostrar_monitor_conexiones()
        if sitio_activo:
            if st.button("🔴 APAGAR SITIO"):
                with open(ARCHIVO_ESTADO, "w") as f: f.write("OFFLINE")
                st.rerun()
        else:
            st.error("El sitio está OFFLINE.")
            if st.button("🟢 ACTIVAR SITIO"):
                if os.path.exists(ARCHIVO_ESTADO): os.remove(ARCHIVO_ESTADO)
                st.rerun()
        st.markdown("---")

    st.markdown("### 🛠️ Configuración")
    st.markdown("---")
    
    secciones = {}
    archivos_pdf = glob.glob("**/*.pdf", recursive=True)

    for ruta in archivos_pdf:
        if "chroma_db" in ruta or ".git" in ruta or "__pycache__" in ruta: continue
        partes = os.path.normpath(ruta).split(os.sep)
        if len(partes) >= 2:
            raiz, subcat = partes[0], partes[-2]
            if raiz == subcat: subcat = "General / Raíz"
            if raiz not in secciones: secciones[raiz] = set()
            secciones[raiz].add(subcat)
        elif len(partes) == 1:
            if "Documentos Sueltos" not in secciones: secciones["Documentos Sueltos"] = set()
            secciones["Documentos Sueltos"].add("Raíz Principal")

    if secciones:
        for raiz in sorted(secciones.keys()):
            with st.sidebar.expander(f"📁 {raiz}", expanded=False):
                for subcat in sorted(secciones[raiz]):
                    st.markdown(f'<div class="folder-card"><span class="folder-icon">📂</span><span class="folder-text">{subcat}</span></div>', unsafe_allow_html=True)
    else:
        st.warning("No hay manuales indexados en el servidor.")
    
    st.markdown("""<div class="tip-container"><p class="tip-text">💡 <b>Tip Pro:</b> Escribe <i>"actualizar base"</i> en el chat (como Administrador) para sincronizar nuevos manuales.</p></div>""", unsafe_allow_html=True)
    st.markdown("<br>" * 3, unsafe_allow_html=True)
    
    if st.button("🗑️ Limpiar Mi Chat"):
        # Fíjate que aquí ya NO borramos la variable del motor_ia, porque el motor ya no guarda historial.
        st.session_state.historial_pantalla = []
        st.session_state.ultimo_acceso = time.time()
        st.rerun()

    if st.button("🚪 Cerrar Acceso"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- LÓGICA DE CHAT AISLADA ---
if not st.session_state.historial_pantalla:
    st.session_state.historial_pantalla = [{"rol": "assistant", "contenido": f"¡Hola! Soy tu experto en flujos y procesos. Estás en sesión de **{st.session_state.rol_usuario}**. ¿En qué puedo ayudarte?"}]

for msg in st.session_state.historial_pantalla:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["contenido"])

if consulta := st.chat_input("Escribe tu consulta sobre flujos o manuales..."):
    st.session_state.ultimo_acceso = time.time()
    st.session_state.pensando = True 
    
    with st.chat_message("user"): st.markdown(consulta)
    st.session_state.historial_pantalla.append({"rol": "user", "contenido": consulta})

    with st.chat_message("assistant"):
        with st.spinner("Analizando documentación oficial..."):
            try:
                # COMPILAMOS ÚNICAMENTE LOS ÚLTIMOS 4 MENSAJES DE ESTE USUARIO
                contexto_usuario_actual = "\n".join([f"{m['rol'].upper()}: {m['contenido']}" for m in st.session_state.historial_pantalla[-5:-1]])
                
                # ENVIAMOS TODO AL MOTOR CENTRAL DE FORMA ESTÉRIL
                respuesta = motor_ia.procesar_consulta(consulta, contexto_usuario_actual, st.session_state.rol_usuario)
                st.markdown(respuesta)
                st.session_state.historial_pantalla.append({"rol": "assistant", "contenido": respuesta})
            except Exception as e:
                error_msg = f"❌ Ocurrió un error interno: {str(e)}"
                st.error(error_msg)
                st.session_state.historial_pantalla.append({"rol": "assistant", "contenido": error_msg})
    
    st.session_state.pensando = False
    st.rerun()
