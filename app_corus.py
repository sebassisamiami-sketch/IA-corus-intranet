import os
import streamlit as st
from chat_procesos import CorusIntranetEngine

# 1. Configuración de la página (Debe ser la primera instrucción)
st.set_page_config(
    page_title="IA Corus - Gestión de Procesos", 
    page_icon="🤖", 
    layout="centered", 
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE CONTROL DE ACCESO (LOGIN) ---
def check_password():
    """Retorna True si el usuario ingresa la contraseña correcta."""
    # Contraseña maestra asignada para el equipo
    contrasena_maestra = "Corus2026*" 

    def password_entered():
        if st.session_state["password_input"] == contrasena_maestra:
            st.session_state["acceso_concedido"] = True
            del st.session_state["password_input"]  # Borra la contraseña de la memoria
        else:
            st.session_state["acceso_concedido"] = False

    # Lógica de visualización del formulario de seguridad
    if "acceso_concedido" not in st.session_state:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #3b82f6;'>🏢 Acceso Restringido </h2>", unsafe_allow_html=True)
        st.text_input("🔑 Ingresa la contraseña para continuar:", type="password", on_change=password_entered, key="password_input")
        return False
    elif not st.session_state["acceso_concedido"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #3b82f6;'>🏢 Acceso Restringido Corus</h2>", unsafe_allow_html=True)
        st.text_input("🔑 Ingresa la contraseña corporativa para continuar:", type="password", on_change=password_entered, key="password_input")
        st.error("🚫 Contraseña incorrecta. Acceso denegado.")
        return False
    
    return True # Acceso validado exitosamente

# Detiene la ejecución de todo el código de abajo si no hay contraseña
if not check_password():
    st.stop()


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
        st.image("logo_corus.png", use_container_width=True)
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