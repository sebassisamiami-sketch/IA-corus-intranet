import streamlit as st
import time
import os
import datetime
import glob
import json
from streamlit_autorefresh import st_autorefresh
from chat_procesos import CorusIntranetEngine 

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="IA Corus - Procesos", page_icon="logo_corus2.png", layout="centered")

ARCHIVO_ESTADO = "estado_servidor.txt"
ARCHIVO_LOGS = "registro_conexiones.csv"
ARCHIVO_MEMORIA_CHATS = "memoria_largo_plazo.json"

sitio_activo = True
if os.path.exists(ARCHIVO_ESTADO):
    with open(ARCHIVO_ESTADO, "r") as f:
        if f.read().strip() == "OFFLINE":
            sitio_activo = False

# --- GESTIÓN DE MEMORIA EN DISCO LOCAL ---
def cargar_memoria_disco(usuario_clave: str) -> list:
    if os.path.exists(ARCHIVO_MEMORIA_CHATS):
        try:
            with open(ARCHIVO_MEMORIA_CHATS, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(usuario_clave, [])
        except Exception:
            return []
    return []

def guardar_memoria_disco(usuario_clave: str, historial: list):
    data = {}
    if os.path.exists(ARCHIVO_MEMORIA_CHATS):
        try:
            with open(ARCHIVO_MEMORIA_CHATS, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data[usuario_clave] = historial
    with open(ARCHIVO_MEMORIA_CHATS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
        else: st.info("El archivo de logs está vacío.")
    else: st.info("Aún no hay conexiones registradas.")

# --- 2. INITIALIZACIÓN DE SESIÓN (VOLÁTIL) ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "usuario_identidad" not in st.session_state: st.session_state.usuario_identidad = ""
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

@st.cache_resource(show_spinner=False)
def cargar_motor_central():
    return CorusIntranetEngine()

# --- 3. LOGIN CON RECUPERACIÓN DE MEMORIA ---
if not st.session_state.autenticado:
    st.title("🏢 Acceso Restringido")
    if not sitio_activo: st.error("⚠️ SISTEMA EN MANTENIMIENTO.")

    with st.form("formulario_login"):
        usuario_input = st.text_input("Ingresa tu Nombre y Apellido:", placeholder="Ej. Juan Pérez")
        pwd = st.text_input("Contraseña de acceso:", type="password")
        btn_ingresar = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if btn_ingresar:
            if not usuario_input.strip() or not pwd:
                st.warning("Por favor, ingresa los datos.")
            else:
                nombre_formateado = usuario_input.strip().replace(" ", "_")
                if pwd == "FarmeoAura*26*****":
                    if not sitio_activo:
                        st.error("Sistema en mantenimiento.")
                    else:
                        registrar_acceso(usuario_input.strip(), "Analista")
                        st.session_state.update(autenticado=True, usuario_identidad=nombre_formateado, rol_usuario="Analista", es_admin=False, ultimo_acceso=time.time())
                        # 🚨 Cargar memoria desde disco de este analista específico
                        st.session_state.historial_pantalla = cargar_memoria_disco(f"{nombre_formateado}_Analista")
                        st.rerun()
                        
                elif pwd == "Pipeline**2038******":
                    registrar_acceso(usuario_input.strip(), "Administrador")
                    st.session_state.update(autenticado=True, usuario_identidad=nombre_formateado, rol_usuario="Administrador", es_admin=True, ultimo_acceso=time.time())
                    # 🚨 Cargar memoria desde disco del administrador específico
                    st.session_state.historial_pantalla = cargar_memoria_disco(f"{nombre_formateado}_Administrador")
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
    st.stop() 

# =====================================================================
# INTERFAZ PRINCIPAL
# =====================================================================
motor_ia = cargar_motor_central()
clave_memoria_actual = f"{st.session_state.usuario_identidad}_{st.session_state.rol_usuario}"

if not sitio_activo and not st.session_state.es_admin:
    st.session_state.autenticado = False
    st.rerun()

if not st.session_state.pensando:
    st_autorefresh(interval=30000, limit=None, key="reloj_sesion")

if (time.time() - st.session_state.ultimo_acceso) >= LIMITE_EXPULSION:
    st.session_state.autenticado = False
    st.rerun()
elif (time.time() - st.session_state.ultimo_acceso) >= LIMITE_ADVERTENCIA:
    if not st.session_state.dialogo_abierto: mostrar_ventana_caducidad()

st.markdown("""
    <style>
    #MainMenu, footer, .stAppDeployButton {visibility: hidden; display: none !important;}
    header {background: transparent !important;}
    [data-testid="stSidebar"] { background-color: rgba(255, 255, 255, 0.02) !important; backdrop-filter: blur(20px) !important;}
    .folder-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); padding: 10px 15px; border-radius: 10px; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; }
    .folder-icon { color: #60a5fa; font-size: 18px; }
    .folder-text { color: #e2e8f0; font-size: 14px; font-weight: 500;}
    .tip-container { background: rgba(59, 130, 246, 0.05); border-left: 3px solid #3b82f6; padding: 15px; border-radius: 5px; margin-top: 20px;}
    .tip-text { font-size: 13px; color: #94a3b8; }
    div.stButton > button { background: rgba(128, 128, 128, 0.1) !important; color: #f8fafc !important; border-radius: 10px !important; text-transform: uppercase; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_corus.png"): st.image("logo_corus.png", width='stretch')
    else: st.markdown("<h1>🏢</h1>", unsafe_allow_html=True)
with col2:
    st.title("Asistente Virtual Corus")
    st.caption(f"Sesión: **{st.session_state.rol_usuario}** | Colaborador: **{st.session_state.usuario_identidad.replace('_', ' ')}**")
st.divider()

with st.sidebar:
    if st.session_state.es_admin:
        st.markdown("### 🚨 PANEL MAESTRO")
        if st.button("👁️ VER CONEXIONES"): mostrar_monitor_conexiones()
        if sitio_activo:
            if st.button("🔴 APAGAR SITIO"):
                with open(ARCHIVO_ESTADO, "w") as f: f.write("OFFLINE")
                st.rerun()
        else:
            if st.button("🟢 ACTIVAR SITIO"):
                if os.path.exists(ARCHIVO_ESTADO): os.remove(ARCHIVO_ESTADO)
                st.rerun()
        st.markdown("---")

    st.markdown("### 🛠️ Configuración")
    secciones = {}
    for ruta in glob.glob("**/*.pdf", recursive=True):
        if "chroma_db" in ruta or ".git" in ruta or "__pycache__" in ruta: continue
        partes = os.path.normpath(ruta).split(os.sep)
        if len(partes) >= 2:
            raiz, subcat = partes[0], partes[-2]
            if raiz == subcat: subcat = "General / Raíz"
            if raiz not in secciones: secciones[raiz] = set()
            secciones[raiz].add(subcat)

    if secciones:
        for raiz in sorted(secciones.keys()):
            with st.sidebar.expander(f"📁 {raiz}", expanded=False):
                for subcat in sorted(secciones[raiz]):
                    st.markdown(f'<div class="folder-card"><span class="folder-icon">📂</span><span class="folder-text">{subcat}</span></div>', unsafe_allow_html=True)

    if st.button("🗑️ Limpiar Mi Chat"):
        st.session_state.historial_pantalla = []
        # Limpiar también la memoria en el disco para este usuario
        guardar_memoria_disco(clave_memoria_actual, [])
        st.rerun()

    if st.button("🚪 Cerrar Acceso"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- ÁREA DE CHAT CON MEMORIA DE LARGO PLAZO ---
if not st.session_state.historial_pantalla:
    st.session_state.historial_pantalla = [{"rol": "assistant", "contenido": f"¡Hola! Bienvenido de vuelta. Tu historial ha sido restaurado con éxito en tu rol de **{st.session_state.rol_usuario}**. ¿En qué caso vamos a trabajar hoy?"}]

for msg in st.session_state.historial_pantalla:
    with st.chat_message(msg["rol"]): st.markdown(msg["contenido"])

if consulta := st.chat_input("Escribe tu consulta..."):
    st.session_state.ultimo_acceso = time.time()
    st.session_state.pensando = True 
    
    with st.chat_message("user"): st.markdown(consulta)
    st.session_state.historial_pantalla.append({"rol": "user", "contenido": consulta})
    # Sincronizar con el disco de inmediato
    guardar_memoria_disco(clave_memoria_actual, st.session_state.historial_pantalla)

    with st.chat_message("assistant"):
        with st.spinner("Consultando documentación oficial..."):
            try:
                contexto_usuario_actual = "\n".join([f"{m['rol'].upper()}: {m['contenido']}" for m in st.session_state.historial_pantalla[-5:-1]])
                respuesta = motor_ia.procesar_consulta(consulta, contexto_usuario_actual, st.session_state.rol_usuario)
                st.markdown(respuesta)
                st.session_state.historial_pantalla.append({"rol": "assistant", "contenido": respuesta})
                # Guardar respuesta en el disco permanente
                guardar_memoria_disco(clave_memoria_actual, st.session_state.historial_pantalla)
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    st.session_state.pensando = False
    st.rerun()
