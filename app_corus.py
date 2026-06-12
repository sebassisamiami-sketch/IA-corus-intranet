import streamlit as st
import time
import os
from streamlit_autorefresh import st_autorefresh
from chat_procesos import CorusIntranetEngine 

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="IA Corus - Procesos", page_icon="logo_corus2.png", layout="centered")

# --- 2. LECTURA DEL ESTADO GLOBAL DEL SERVIDOR (KILL SWITCH) ---
ARCHIVO_ESTADO = "estado_servidor.txt"
sitio_activo = True
if os.path.exists(ARCHIVO_ESTADO):
    with open(ARCHIVO_ESTADO, "r") as f:
        if f.read().strip() == "OFFLINE":
            sitio_activo = False

# --- 3. INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
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

# Tiempos límite en segundos
LIMITE_ADVERTENCIA = 300  # 5 minutos para mostrar la alerta
LIMITE_EXPULSION = 360    # 6 minutos para cerrar la sesión a la fuerza

# --- 4. DISEÑO DEL CUADRO DE DIÁLOGO (POPUP) ---
@st.dialog("⚠️ Alerta de Inactividad")
def mostrar_ventana_caducidad():
    st.session_state.dialogo_abierto = True
    st.warning("Tu sesión está a punto de cerrarse por seguridad tras 5 minutos sin actividad.")
    st.write("¿Deseas mantener la sesión activa?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Aceptar (Mantener en línea)", use_container_width=True):
            st.session_state.ultimo_acceso = time.time()
            st.session_state.dialogo_abierto = False
            st.rerun()
    with col2:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.es_admin = False
            st.session_state.dialogo_abierto = False
            st.rerun()

# --- 5. SISTEMA DE LOGIN DE DOBLE CAPA ---
if not st.session_state.autenticado:
    st.title("🏢 Acceso Restringido Corus")
    
    # Aviso público si el sitio está apagado
    if not sitio_activo:
        st.error("⚠️ SISTEMA EN MANTENIMIENTO: La plataforma de procesos ha sido desactivada temporalmente. Intenta más tarde.")

    pwd = st.text_input("Contraseña de acceso:", type="password")
    if pwd:
        # 1. Intento de acceso como usuario normal
        if pwd == "FarmeoAura*26*****":
            if not sitio_activo:
                st.error("Acceso denegado: El sistema está en mantenimiento.")
                time.sleep(2)
                st.rerun()
            else:
                st.session_state.autenticado = True
                st.session_state.es_admin = False
                st.session_state.ultimo_acceso = time.time()
                st.success("Acceso concedido. Cargando...")
                time.sleep(1)
                st.rerun()
                
        # 2. Intento de acceso como Administrador Maestro
        elif pwd == "Pipeline**2038******":
            st.session_state.autenticado = True
            st.session_state.es_admin = True
            st.session_state.ultimo_acceso = time.time()
            st.success("⚙️ Acceso de Administrador concedido...")
            time.sleep(1)
            st.rerun()
            
        else:
            st.error("Contraseña incorrecta.")
    st.stop() # Bloquea el resto del código si no hay acceso

# =====================================================================
# SISTEMA PRINCIPAL (SOLO VISIBLE CON ACCESO CONCEDIDO)
# =====================================================================

# --- 6. INICIALIZACIÓN DEL MOTOR IA ---
if "motor_ia" not in st.session_state:
    with st.spinner("Iniciando infraestructura y cargando datos corporativos..."):
        st.session_state.motor_ia = CorusIntranetEngine()

# --- 7. GUARDIÁN DE SESIÓN Y VIGILANTE DE MANTENIMIENTO ---
if "pensando" not in st.session_state:
    st.session_state.pensando = False

# Expulsión en vivo: Si el admin apaga el sitio, saca a los normales de inmediato
if not sitio_activo and not st.session_state.es_admin:
    st.session_state.autenticado = False
    st.session_state.dialogo_abierto = False
    st.rerun()

# El reloj solo avanza si la IA no está pensando
if not st.session_state.pensando:
    st_autorefresh(interval=30000, limit=None, key="reloj_sesion")

tiempo_actual = time.time()
inactividad = tiempo_actual - st.session_state.ultimo_acceso

# Reglas de expulsión por tiempo
if inactividad >= LIMITE_EXPULSION:
    st.session_state.autenticado = False
    st.session_state.es_admin = False
    st.session_state.dialogo_abierto = False
    st.rerun()
elif inactividad >= LIMITE_ADVERTENCIA:
    if not st.session_state.dialogo_abierto:
        mostrar_ventana_caducidad()

# --- 8. CSS: ESTILO CRISTAL, FOLDERS MODERNOS Y TIP BOX ---
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

# --- 9. CABECERA VISUAL ---
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_corus.png"):
        st.image("logo_corus.png", width='stretch')
    else:
        st.markdown("<h1 style='text-align: center;'>🏢</h1>", unsafe_allow_html=True)

with col2:
    st.title("Asistente Virtual Corus")
    st.caption("Inteligencia de Procesos & Gestión del Conocimiento")
st.divider()

# --- 10. SIDEBAR: PANEL DE CONTROL ---
with st.sidebar:
    # 🔴 PANEL EXCLUSIVO PARA EL ADMINISTRADOR 🔴
    if st.session_state.es_admin:
        st.markdown("### 🚨 MASTER SWITCH")
        if sitio_activo:
            if st.button("🔴 APAGAR SITIO (Kill Switch)", type="primary"):
                with open(ARCHIVO_ESTADO, "w") as f:
                    f.write("OFFLINE")
                st.rerun()
        else:
            st.error("El sitio está OFFLINE para los usuarios.")
            if st.button("🟢 ACTIVAR SITIO", type="primary"):
                if os.path.exists(ARCHIVO_ESTADO):
                    os.remove(ARCHIVO_ESTADO)
                st.rerun()
        st.markdown("---")

    st.markdown("### 🛠️ Configuración")
    st.markdown("---")
    
    with st.expander("📚 Manuales Parafiscales", expanded=True):
        if st.session_state.motor_ia.categorias:
            for cat in st.session_state.motor_ia.categorias:
                st.markdown(f"""
                <div class="folder-card">
                    <span class="folder-icon">📂</span>
                    <span class="folder-text">{cat}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No hay manuales cargados.")
    
    st.markdown(f"""
    <div class="tip-container">
        <p class="tip-text">
            💡 <b>Tip Pro:</b> Si subes un nuevo archivo PDF a las subcarpetas, escribe 
            <i>"actualizar base"</i> en el chat para sincronizar la IA automáticamente.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>" * 5, unsafe_allow_html=True)
    
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

# --- 11. ÁREA DE CHAT (LÓGICA RAG CON CANDADO) ---
if not st.session_state.historial_pantalla:
    st.session_state.historial_pantalla = [{"rol": "assistant", "contenido": "¡Hola, analista! Soy tu experto en flujos y procesos. ¿En qué puedo ayudarte hoy?"}]

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
