import streamlit as st
import time
import os
from streamlit_autorefresh import st_autorefresh

# Si tienes tu motor RAG en otro archivo, impórtalo aquí
# from chat_procesos import CorusIntranetEngine 

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="IA Corus - Procesos", page_icon="logo_corus.ico", layout="centered")

# --- 2. INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "ultimo_acceso" not in st.session_state:
    st.session_state.ultimo_acceso = time.time()
if "mostrar_alerta" not in st.session_state:
    st.session_state.mostrar_alerta = False

# Límite de tiempo: 5 minutos = 300 segundos
LIMITE_INACTIVIDAD = 300

# --- 3. DISEÑO DEL CUADRO DE DIÁLOGO (POPUP) ---
@st.dialog("⚠️ Alerta de Inactividad")
def dialogo_sesion():
    st.warning("Tu sesión está a punto de cerrarse por seguridad tras 5 minutos sin actividad.")
    st.write("¿Deseas mantener la sesión activa?")
    
    col1, col2 = st.columns(2)
    with col1:
        # Botón para seguir en línea
        if st.button("✅ Aceptar (Mantener en línea)", use_container_width=True):
            st.session_state.ultimo_acceso = time.time()
            st.session_state.mostrar_alerta = False
            st.rerun()
    with col2:
        # Botón para cerrar sesión
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.ultimo_acceso = time.time()
            st.session_state.mostrar_alerta = False
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
# A PARTIR DE AQUÍ, EL USUARIO YA ESTÁ ADENTRO DEL SISTEMA
# =====================================================================

# --- 5. MOTOR DE TEMPORIZADOR EN SEGUNDO PLANO ---
# Revisa el reloj silenciosamente cada 10 segundos (10000 ms)
st_autorefresh(interval=10000, limit=None, key="reloj_sesion")

tiempo_actual = time.time()
tiempo_transcurrido = tiempo_actual - st.session_state.ultimo_acceso

# Si pasan los 5 minutos, levantamos la bandera de alerta
if tiempo_transcurrido > LIMITE_INACTIVIDAD:
    st.session_state.mostrar_alerta = True

# Si la bandera está arriba, disparamos el cuadro de diálogo flotante
if st.session_state.mostrar_alerta:
    dialogo_sesion()

# --- 6. INTERFAZ PRINCIPAL DE LA APLICACIÓN ---
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_corus.png"):
        st.image("logo_corus.png", width='stretch')
with col2:
    st.title("Asistente de Procesos Corus")

# Botón lateral por si quieren cerrar sesión manualmente antes de los 5 minutos
st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update(autenticado=False))


#  7LÓGICA DE CHAT VA AQUÍ ---
# (CADA 5 MINUTOS SE CIERRA LA SESION)

# Entrada de texto del usuario
if prompt := st.chat_input("Consulta los manuales de procesos..."):
    # ¡MUY IMPORTANTE! Al enviar un mensaje, reiniciamos el reloj a cero
    st.session_state.ultimo_acceso = time.time()
    
    # proceso de respuesta con  motor RAG
    st.chat_message("user").write(prompt)
    st.chat_message("assistant").write("Procesando tu consulta...")
# =====================================================================
# SISTEMA PRINCIPAL (SOLO VISIBLE CON ACCESO CONCEDIDO)
# =====================================================================

# --- CSS: ESTILO CRISTAL, FOLDERS MODERNOS Y TIP BOX ---
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

# --- CABECERA ---
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

# 2. Motor IA
if "motor_ia" not in st.session_state:
    with st.spinner("Iniciando infraestructura y cargando datos corporativos..."):
        st.session_state.motor_ia = CorusIntranetEngine()

# --- SIDEBAR: PANEL DE CONTROL ---
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
    
    if st.button("🗑️ Limpiar Sesión"):
        st.session_state.historial_pantalla = []
        st.session_state.motor_ia.historial = []
        st.session_state.motor_ia.cat_actual = None
        st.rerun()

# 3. Área de Chat
if "historial_pantalla" not in st.session_state or not st.session_state.historial_pantalla:
    st.session_state.historial_pantalla = [{"rol": "assistant", "contenido": "¡Hola, analista! Soy tu experto en flujos y procesos de webmethods. ¿En qué puedo ayudarte hoy?"}]

for msg in st.session_state.historial_pantalla:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["contenido"])

if consulta := st.chat_input("Escribe tu consulta sobre flujos o manuales..."):
    with st.chat_message("user"):
        st.markdown(consulta)
    st.session_state.historial_pantalla.append({"rol": "user", "contenido": consulta})

    with st.chat_message("assistant"):
        with st.spinner("Analizando documentación oficial..."):
            respuesta = st.session_state.motor_ia.procesar_consulta(consulta)
            st.markdown(respuesta)
    st.session_state.historial_pantalla.append({"rol": "assistant", "contenido": respuesta})
