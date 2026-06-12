import streamlit as st
import time
import os
from streamlit_autorefresh import st_autorefresh
from chat_procesos import CorusIntranetEngine 

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="IA Corus - Procesos", page_icon="logo_corus.ico", layout="centered")

# --- 2. INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "ultimo_acceso" not in st.session_state:
    st.session_state.ultimo_acceso = time.time()
if "dialogo_abierto" not in st.session_state:
    st.session_state.dialogo_abierto = False
if "historial_pantalla" not in st.session_state:
    st.session_state.historial_pantalla = []

# Tiempos límite en segundos
LIMITE_ADVERTENCIA = 300  # 5 minutos para mostrar la alerta
LIMITE_EXPULSION = 360    # 6 minutos para cerrar la sesión a la fuerza

# --- 3. DISEÑO DEL CUADRO DE DIÁLOGO (POPUP) ---
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
            st.session_state.dialogo_abierto = False
            st.rerun()

# --- 4. SISTEMA DE LOGIN DE CRISTAL ---
if not st.session_state.autenticado:
    st.title("🏢 Acceso Restringido Corus")
    pwd = st.text_input("Contraseña de acceso:", type="password")
    if pwd:
        if pwd == "Corus2026*":
            st.session_state.autenticado = True
            st.session_state.ultimo_acceso = time.time()
            st.success("Acceso concedido. Cargando...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop() # Bloquea el resto del código si no hay acceso

# =====================================================================
# SISTEMA PRINCIPAL (SOLO VISIBLE CON ACCESO CONCEDIDO)
# =====================================================================

# --- 5. INICIALIZACIÓN DEL MOTOR IA ---
if "motor_ia" not in st.session_state:
    with st.spinner("Iniciando infraestructura y cargando datos corporativos..."):
        st.session_state.motor_ia = CorusIntranetEngine()

# --- 6. GUARDIÁN DE SESIÓN (TEMPORIZADOR EN SEGUNDO PLANO) ---
# Revisa el reloj silenciosamente cada 10 segundos
st_autorefresh(interval=10000, limit=None, key="reloj_sesion")

tiempo_actual = time.time()
inactividad = tiempo_actual - st.session_state.ultimo_acceso

# Regla de expulsión
if inactividad >= LIMITE_EXPULSION:
    st.session_state.autenticado = False
    st.session_state.dialogo_abierto = False
    st.rerun()
# Regla de advertencia
elif inactividad >= LIMITE_ADVERTENCIA:
    if not st.session_state.dialogo_abierto:
        mostrar_ventana_caducidad()

# --- 7. CSS: ESTILO CRISTAL, FOLDERS MODERNOS Y TIP BOX ---
st.markdown("""
    <style>
    /* Limpieza de marcas de agua */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none !important;}
    header {background: transparent !important;}

    /* Fondo del Panel Lateral con Transparencia */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }

    /* DISEÑO DE SUB-CARPETAS (Folder Cards) */
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

    /* CAJA DE TIP (Sugerencia) */
    .tip-container {
        background: rgba(59, 130, 246, 0.05);
        border-left: 3px solid #3b82f6;
        padding: 15px;
        border-radius: 5px;
        margin-top: 20px;
    }
    .tip-text { font-size: 13px; color: #94a3b8; line-height: 1.4; }

    /* EL BOTÓN: Gris humo transparentoso */
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

# --- 8. CABECERA VISUAL ---
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

# --- 9. SIDEBAR: PANEL DE CONTROL ---
with st.sidebar:
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
    
    # Botón de limpiar chat
    if st.button("🗑️ Limpiar Sesión"):
        st.session_state.historial_pantalla = []
        st.session_state.motor_ia.historial = []
        st.session_state.motor_ia.cat_actual = None
        st.session_state.ultimo_acceso = time.time() # Reinicia reloj
        st.rerun()

    # Botón de cerrado manual en la barra lateral
    if st.button("🚪 Cerrar Acceso"):
        st.session_state.autenticado = False
        st.rerun()

# --- 10. ÁREA DE CHAT (LÓGICA RAG) ---
if not st.session_state.historial_pantalla:
    st.session_state.historial_pantalla = [{"rol": "assistant", "contenido": "¡Hola, analista! Soy tu experto en flujos y procesos. ¿En qué puedo ayudarte hoy?"}]

for msg in st.session_state.historial_pantalla:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["contenido"])

# Entrada de texto del usuario
if consulta := st.chat_input("Escribe tu consulta sobre flujos o manuales..."):
    # ¡CRÍTICO PARA QUE LA SESIÓN NO SE CIERRE MIENTRAS CHATEAN!
    st.session_state.ultimo_acceso = time.time()
    
    with st.chat_message("user"):
        st.markdown(consulta)
    st.session_state.historial_pantalla.append({"rol": "user", "contenido": consulta})

    with st.chat_message("assistant"):
        with st.spinner("Analizando documentación oficial..."):
            respuesta = st.session_state.motor_ia.procesar_consulta(consulta)
            st.markdown(respuesta)
    st.session_state.historial_pantalla.append({"rol": "assistant", "contenido": respuesta})
