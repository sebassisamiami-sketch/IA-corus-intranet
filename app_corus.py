# app_corus.py - VERSIÓN REPARADA
"""
CorusIntranetEngine v2.0 - VERSIÓN REPARADA
"""

import streamlit as st
import logging
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ===== CARGAR VARIABLES DE ENTORNO =====
load_dotenv()

# ===== CREAR DIRECTORIOS =====
for directorio in ["data/pdfs", "data/db", "data/sessions", "logs"]:
    Path(directorio).mkdir(parents=True, exist_ok=True)

# ===== CONFIGURAR LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== VALIDAR IMPORTS =====
try:
    from ia_motor import CorusIntranetEngine
    logger.info("✅ ia_motor cargado")
except ImportError as e:
    logger.error(f"❌ Error importando ia_motor: {e}")
    st.error(f"❌ Error: ia_motor.py no encontrado\n{e}")
    st.stop()

try:
    from chat_procesos import ChatProcessor
    logger.info("✅ chat_procesos cargado")
except ImportError as e:
    logger.error(f"❌ Error importando chat_procesos: {e}")
    st.error(f"❌ Error: chat_procesos.py no encontrado\n{e}")
    st.stop()

try:
    from procesar_datos import DataProcessor
    logger.info("✅ procesar_datos cargado")
except ImportError as e:
    logger.error(f"❌ Error importando procesar_datos: {e}")
    st.error(f"❌ Error: procesar_datos.py no encontrado\n{e}")
    st.stop()

# ===== CREDENCIALES =====
CREDENCIALES = {
    "Analista": "analista123",
    "Administrador": "admin123"
}

# ===== CONFIGURACIÓN STREAMLIT =====
st.set_page_config(
    page_title="🤖 Corus Intranet Engine v2.0",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CSS PERSONALIZADO =====
st.markdown("""
<style>
    .login-container {
        background: rgba(255, 255, 255, 0.95);
        padding: 40px;
        border-radius: 15px;
        max-width: 400px;
        margin: 50px auto;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    .login-container h1 {
        color: #667eea;
        text-align: center;
    }
    
    .stats-box {
        background: rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# ===== INICIALIZAR SESIÓN =====
def inicializar_sesion():
    """Inicializar variables de sesión"""
    variables_default = {
        "autenticado": False,
        "usuario": None,
        "rol": None,
        "chat_processor": None,
        "motor_ia": None,
        "historial": [],
        "inicio_sesion": None,
        "mostrar_stats": False,
        "procesar_pdfs_modal": False,
        "mostrar_bd_modal": False
    }
    
    for var, valor_default in variables_default.items():
        if var not in st.session_state:
            st.session_state[var] = valor_default

def registrar_acceso(usuario: str, rol: str, accion: str = "LOGIN"):
    """Registrar acceso en CSV"""
    try:
        archivo_log = "logs/registro_conexiones.csv"
        archivo_existe = os.path.exists(archivo_log)
        
        with open(archivo_log, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            if not archivo_existe:
                writer.writerow(['Timestamp', 'Usuario', 'Rol', 'Acción'])
            
            writer.writerow([
                datetime.now().isoformat(),
                usuario,
                rol,
                accion
            ])
    except Exception as e:
        logger.error(f"Error registrando acceso: {e}")

# ===== PANTALLA DE LOGIN =====
def pantalla_login():
    """Renderizar pantalla de login"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        
        st.markdown("# 🤖 Corus Intranet Engine")
        st.markdown("## v2.0")
        st.markdown("### Sistema de IA Corporativo")
        
        st.markdown("---")
        
        # Formulario de login
        usuario = st.text_input(
            "👤 Usuario",
            placeholder="Ingresa tu usuario",
            key="input_usuario"
        )
        
        rol = st.selectbox(
            "🔐 Rol",
            ["Analista", "Administrador"],
            key="select_rol"
        )
        
        contraseña = st.text_input(
            "🔑 Contraseña",
            type="password",
            placeholder="Ingresa tu contraseña",
            key="input_password"
        )
        
        if st.button("🔓 Iniciar Sesión", use_container_width=True, key="btn_login"):
            # Validar campos
            if not usuario or not contraseña:
                st.error("❌ Por favor completa todos los campos")
                return
            
            # Validar credenciales
            if contraseña != CREDENCIALES.get(rol):
                st.error("❌ Credenciales inválidas")
                logger.warning(f"Intento fallido: {usuario} ({rol})")
                return
            
            # Login exitoso
            logger.info(f"🔓 Intento de login: {usuario} ({rol})")
            
            with st.spinner("⏳ Inicializando sistema..."):
                try:
                    # Inicializar motor IA
                    logger.info("Inicializando CorusIntranetEngine...")
                    motor_ia = CorusIntranetEngine()
                    
                    # Cargar vectorstore
                    logger.info("Cargando vectorstore...")
                    motor_ia.load_vectorstore()
                    
                    # Configurar chain
                    logger.info("Configurando chain...")
                    motor_ia.setup_chain()
                    
                    # Inicializar chat processor
                    logger.info("Inicializando ChatProcessor...")
                    chat_processor = ChatProcessor(usuario, rol)
                    chat_processor._cargar_memoria_usuario()
                    
                    # Actualizar sesión
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.session_state.rol = rol
                    st.session_state.motor_ia = motor_ia
                    st.session_state.chat_processor = chat_processor
                    st.session_state.historial = chat_processor.historial_local
                    st.session_state.inicio_sesion = datetime.now()
                    
                    # Registrar acceso
                    registrar_acceso(usuario, rol, "LOGIN")
                    
                    logger.info(f"✅ Login exitoso: {usuario} ({rol})")
                    st.success(f"✅ ¡Bienvenido {usuario}!")
                    st.rerun()
                
                except Exception as e:
                    logger.error(f"❌ Error durante login: {e}", exc_info=True)
                    st.error(f"❌ Error inicializando sistema:\n{str(e)}")
                    st.markdown("### 🔍 Diagnóstico:")
                    st.markdown(f"""
                    - **Error:** {str(e)}
                    - **Archivo log:** logs/app.log
                    - **Verifica:** 
                      - ¿Existe el archivo ia_motor.py?
                      - ¿Está configurado OPENAI_API_KEY en .env?
                      - ¿Están instaladas todas las dependencias?
                    """)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Información de prueba
        st.markdown("---")
        st.markdown("""
        ### 🧪 Credenciales de Prueba:
        
        **Analista:**
        - Contraseña: `analista123`
        
        **Administrador:**
        - Contraseña: `admin123`
        """)

# ===== PANTALLA PRINCIPAL =====
def pantalla_principal():
    """Renderizar pantalla principal después de login"""
    
    # SIDEBAR
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.usuario}")
        st.markdown(f"**Rol:** `{st.session_state.rol}`")
        
        st.markdown("---")
        
        # Botón cerrar sesión
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
            registrar_acceso(st.session_state.usuario, st.session_state.rol, "LOGOUT")
            
            st.session_state.autenticado = False
            st.session_state.usuario = None
            st.session_state.rol = None
            st.session_state.motor_ia = None
            st.session_state.chat_processor = None
            st.session_state.historial = []
            
            logger.info(f"✅ Sesión cerrada")
            st.rerun()
    
    # CONTENIDO PRINCIPAL
    st.markdown("# 💬 Chat IA Corus")
    st.markdown("Consulta documentos corporativos con inteligencia artificial")
    
    # Input de usuario
    col_input, col_button = st.columns([0.85, 0.15])
    
    with col_input:
        user_input = st.text_input(
            "Escribe tu pregunta:",
            placeholder="Ejemplo: ¿Cuáles son las políticas?",
            label_visibility="collapsed",
            key="input_chat"
        )
    
    with col_button:
        enviar = st.button("📤", help="Enviar mensaje", use_container_width=True)
    
    # Procesar mensaje
    if enviar and user_input:
        logger.info(f"Procesando mensaje de {st.session_state.usuario}: {user_input[:50]}")
        
        with st.spinner("⏳ Procesando..."):
            try:
                respuesta = st.session_state.chat_processor.procesar_mensaje(
                    mensaje=user_input,
                    contexto={'rol': st.session_state.rol}
                )
                
                st.session_state.historial.append(respuesta)
                
                if respuesta['exitoso']:
                    st.success("✅ Respuesta generada")
                else:
                    st.error(f"❌ Error: {respuesta.get('error', {}).get('mensaje', 'Desconocido')}")
                
                st.rerun()
            
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}", exc_info=True)
                st.error(f"❌ Error: {str(e)}")
    
    # Mostrar historial
    st.markdown("### 📜 Historial")
    
    if st.session_state.historial:
        for msg in reversed(st.session_state.historial[-10:]):
            with st.container():
                st.markdown(f"**👤 Tú:** {msg['mensaje_original']}")
                
                if msg['exitoso']:
                    st.markdown(f"**🤖 IA:** {msg['respuesta']}")
                else:
                    st.error(f"**❌ Error:** {msg['respuesta']}")
                
                st.caption(f"⏱️ {msg['timestamp'][:16]}")
                st.divider()
    else:
        st.info("💭 No hay mensajes aún. ¡Haz una pregunta!")

# ===== MAIN =====
def main():
    """Función principal"""
    inicializar_sesion()
    
    if st.session_state.autenticado:
        pantalla_principal()
    else:
        pantalla_login()

if __name__ == "__main__":
    main()
