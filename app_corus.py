# app_corus.py - CorusIntranetEngine v2.0 OPTIMIZADO
"""
CorusIntranetEngine v2.0 - Sistema IA Corporativo
Optimizado para Streamlit Cloud
"""

import streamlit as st
from pathlib import Path

# ===== LOGO DE LA PÁGINA =====
# Cargamos logo_corus2.png como ícono de la página (pestaña del navegador).
# Si por alguna razón no se puede cargar, usamos el emoji como respaldo.
LOGO_PATH = Path(__file__).parent / "logo_corus2.png"
try:
    from PIL import Image
    _page_icon = Image.open(LOGO_PATH) if LOGO_PATH.exists() else "🤖"
except Exception:
    _page_icon = "🤖"

# ===== CONFIGURACIÓN INICIAL (DEBE SER LO PRIMERO) =====
st.set_page_config(
    page_title="Corus Intranet Engine v2.0",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

import logging
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# ===== FUNCIONES DE INICIALIZACIÓN =====
@st.cache_resource
def inicializar_sistema():
    """Inicializar sistema una sola vez"""
    from dotenv import load_dotenv
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ OPENAI_API_KEY no configurada")
        st.info("Por favor, configura tu API key en Streamlit Cloud → Settings → Secrets")
        st.stop()
    
    # Crear directorios necesarios
    directorios = [
        "data/pdfs", "data/db", "data/sessions", 
        "logs", "Manual Paraficales", "Manual Pensiones"
    ]
    
    for directorio in directorios:
        Path(directorio).mkdir(parents=True, exist_ok=True)
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("✅ Sistema inicializado")
    
    return logger

# Inicializar sistema
logger = inicializar_sistema()

# ===== IMPORTS LAZY (solo cuando sea necesario) =====
@st.cache_resource
def cargar_motor_ia():
    """Cargar motor IA una sola vez"""
    try:
        from ia_motor import obtener_motor
        logger.info("✅ Cargando motor IA...")
        motor = obtener_motor()
        logger.info("✅ Motor IA listo")
        return motor
    except Exception as e:
        logger.error(f"❌ Error cargando motor: {e}")
        return None

def cargar_chat_processor(usuario, rol):
    """Cargar chat processor"""
    try:
        from chat_procesos import ChatProcessor
        logger.info(f"✅ Chat processor para {usuario}")
        return ChatProcessor(usuario, rol)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None

def cargar_data_processor():
    """Cargar data processor"""
    try:
        from procesar_datos import DataProcessor
        return DataProcessor()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None


# ===== USUARIOS Y ROLES ADMINISTRABLES =====
ARCHIVO_USUARIOS = "data/usuarios.json"

def cargar_usuarios() -> Dict[str, Dict]:
    """Cargar usuarios desde archivo"""
    if Path(ARCHIVO_USUARIOS).exists():
        try:
            with open(ARCHIVO_USUARIOS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # Usuarios por defecto
    return {
        "admin": {"contraseña": "admin123", "rol": "Administrador"},
        "analista": {"contraseña": "analista123", "rol": "Analista"}
    }

def guardar_usuarios(usuarios: Dict):
    """Guardar usuarios en archivo"""
    Path("data").mkdir(exist_ok=True)
    with open(ARCHIVO_USUARIOS, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)
    logger.info("✅ Usuarios guardados")

def registrar_acceso(usuario: str, rol: str, accion: str = "LOGIN"):
    """Registrar acceso en CSV"""
    try:
        archivo_log = "logs/registro_conexiones.csv"
        archivo_existe = os.path.exists(archivo_log)
        
        with open(archivo_log, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not archivo_existe:
                writer.writerow(['Timestamp', 'Usuario', 'Rol', 'Acción', 'IP', 'Sesión'])
            
            writer.writerow([
                datetime.now().isoformat(),
                usuario,
                rol,
                accion,
                st.session_state.get('ip', 'local'),
                st.session_state.get('session_id', 'N/A')
            ])
    except Exception as e:
        logger.error(f"Error registrando acceso: {e}")

# ===== CSS PERSONALIZADO =====
st.markdown("""
<style>
    /* Colores corporativos */
    :root {
        --primary: #667eea;
        --secondary: #764ba2;
        --success: #21a366;
        --danger: #e74c3c;
    }
    
    /* Contenedor de login */
    .login-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 50px;
        border-radius: 20px;
        max-width: 500px;
        margin: 50px auto;
        color: white;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }
    
    .login-container h1 {
        text-align: center;
        margin-bottom: 10px;
    }
    
    .login-container p {
        text-align: center;
        margin-bottom: 30px;
        opacity: 0.9;
    }
    
    /* Botones */
    .stButton button {
        border-radius: 10px;
        font-weight: bold;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f5f7fa 0%, #e9ecef 100%);
    }
    
    /* Cards */
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }
    
    .stats-card h3 {
        margin-top: 0;
    }
    
    .stats-card .value {
        font-size: 28px;
        font-weight: bold;
    }
    
    /* Mensajes */
    .chat-message {
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
    }
    
    .user-message {
        background: #f0f4ff;
        border-left-color: #667eea;
    }
    
    .ai-message {
        background: #f5f5f5;
        border-left-color: #764ba2;
    }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea {
        border-radius: 10px !important;
    }
    
    /* Dividers */
    hr {
        margin: 20px 0;
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
        "motor_ia": None,
        "chat_processor": None,
        "historial": [],
        "inicio_sesion": None,
        "sidebar_expandido": True,
        "session_id": str(datetime.now().timestamp()),
        "ip": "local"
    }
    
    for var, valor_default in variables_default.items():
        if var not in st.session_state:
            st.session_state[var] = valor_default

# ===== PANTALLA LOGIN =====
def pantalla_login():
    """Pantalla de login"""
    
    usuarios = cargar_usuarios()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Mostrar el logo de la empresa centrado
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_column_width=True)

        st.markdown("""
        <div class="login-container">
        <h1>Corus Intranet Engine</h1>
        <p>Sistema IA Corporativo v2.0</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Seleccionar usuario
        usuarios_list = list(usuarios.keys())
        usuario_seleccionado = st.selectbox(
            "👤 Selecciona un usuario",
            usuarios_list,
            key="select_usuario_login"
        )
        
        contraseña = st.text_input(
            "🔑 Contraseña",
            type="password",
            key="input_password_login"
        )
        
        col_login, col_info = st.columns([2, 1])
        
        with col_login:
            if st.button("🔓 Iniciar Sesión", use_container_width=True, type="primary"):
                
                if not contraseña:
                    st.error("❌ Ingresa la contraseña")
                    return
                
                usuario_data = usuarios.get(usuario_seleccionado)
                
                if not usuario_data or usuario_data['contraseña'] != contraseña:
                    st.error("❌ Credenciales inválidas")
                    logger.warning(f"Intento fallido: {usuario_seleccionado}")
                    return
                
                with st.spinner("⏳ Inicializando sistema..."):
                    try:
                        logger.info(f"Iniciando sesión para {usuario_seleccionado}")
                        
                        # Obtener motor IA (cached)
                        motor_ia = cargar_motor_ia()
                        
                        if not motor_ia:
                            st.error("❌ Motor IA no disponible")
                            st.info("Verifica que OPENAI_API_KEY esté configurada")
                            return
                        
                        estado_motor = motor_ia.obtener_estado()
                        logger.info(f"Estado motor: {estado_motor['estado']}")
                        
                        if estado_motor['estado'] != 'listo':
                            st.error(f"❌ Motor IA no disponible: {estado_motor['estado']}")
                            return
                        
                        # Inicializar chat processor
                        chat_processor = cargar_chat_processor(
                            usuario_seleccionado,
                            usuario_data['rol']
                        )
                        
                        if not chat_processor:
                            st.error("❌ Error inicializando chat")
                            return
                        
                        chat_processor._cargar_memoria_usuario()
                        
                        # Actualizar sesión
                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario_seleccionado
                        st.session_state.rol = usuario_data['rol']
                        st.session_state.motor_ia = motor_ia
                        st.session_state.chat_processor = chat_processor
                        st.session_state.historial = chat_processor.historial_local
                        st.session_state.inicio_sesion = datetime.now()
                        
                        # Registrar
                        registrar_acceso(usuario_seleccionado, usuario_data['rol'], "LOGIN")
                        
                        logger.info(f"✅ Login exitoso: {usuario_seleccionado}")
                        st.success(f"✅ ¡Bienvenido {usuario_seleccionado}!")
                        st.rerun()
                    
                    except Exception as e:
                        logger.error(f"❌ Error: {e}", exc_info=True)
                        st.error(f"❌ Error iniciando sistema:\n{str(e)}")
        
        with col_info:
            if st.button("ℹ️", help="Ver credenciales de prueba"):
                st.info("""
                **Usuarios:**
                - admin / admin123
                - analista / analista123
                """)
        
        st.markdown("---")
        
        # Sección admin (crear usuarios)
        with st.expander("⚙️ Crear nuevo usuario (solo demo)"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                nuevo_usuario = st.text_input("Nuevo usuario", key="new_user_input")
                nueva_contraseña = st.text_input("Contraseña", type="password", key="new_pass_input")
                nuevo_rol = st.selectbox("Rol", ["Analista", "Administrador"], key="new_role_select")
            
            with col2:
                if st.button("➕ Crear", key="btn_crear_usuario"):
                    if not nuevo_usuario or not nueva_contraseña:
                        st.error("❌ Completa todos los campos")
                    elif nuevo_usuario in usuarios:
                        st.error("❌ Usuario ya existe")
                    else:
                        usuarios[nuevo_usuario] = {
                            "contraseña": nueva_contraseña,
                            "rol": nuevo_rol
                        }
                        guardar_usuarios(usuarios)
                        st.success(f"✅ Usuario '{nuevo_usuario}' creado")
                        st.rerun()

# ===== PANTALLA PRINCIPAL =====
def pantalla_principal():
    """Pantalla principal después de login"""
    
    # Sidebar expandible con tema profesional
    with st.sidebar:
        # Header del sidebar
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            margin-bottom: 20px;
        ">
            <h3 style="margin: 0;">👤 {st.session_state.usuario}</h3>
            <p style="margin: 5px 0; opacity: 0.9;">🏷️ {st.session_state.rol}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Menú principal
        st.markdown("### 📋 Menú")
        
        col_menu1, col_menu2 = st.columns([3, 1])
        
        with col_menu1:
            opcion = st.radio(
                "Selecciona",
                ["💬 Chat", "📊 Estadísticas"],
                label_visibility="collapsed",
                key="menu_principal"
            )
        
        st.divider()
        
        # Panel Admin (solo para administradores)
        if st.session_state.rol == "Administrador":
            st.markdown("### 🔐 Panel Administrativo")
            
            admin_opcion = st.selectbox(
                "Herramientas Admin",
                [
                    "Gestionar Usuarios",
                    "Procesar PDFs",
                    "Estado de BD",
                    "Registros de Acceso",
                    "Estadísticas IA"
                ],
                label_visibility="collapsed",
                key="admin_menu"
            )
            
            st.divider()
        else:
            admin_opcion = None
        
        # Sesión
        st.markdown("### 🔌 Sesión")
        
        col_sesion1, col_sesion2 = st.columns(2)
        
        with col_sesion1:
            if st.button("🗑️ Limpiar Chat", use_container_width=True):
                st.session_state.chat_processor.limpiar_historial()
                st.session_state.historial = []
                st.success("✅ Chat limpiado")
                st.rerun()
        
        with col_sesion2:
            if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
                registrar_acceso(st.session_state.usuario, st.session_state.rol, "LOGOUT")
                
                st.session_state.autenticado = False
                st.session_state.usuario = None
                st.session_state.rol = None
                st.session_state.motor_ia = None
                st.session_state.chat_processor = None
                st.session_state.historial = []
                
                logger.info("✅ Sesión cerrada")
                st.rerun()
        
        # Información
        st.markdown("---")
        st.caption(f"⏱️ Inicio: {st.session_state.inicio_sesion.strftime('%H:%M:%S')}")
    
    # CONTENIDO PRINCIPAL
    if opcion == "💬 Chat":
        mostrar_chat()
    elif opcion == "📊 Estadísticas":
        mostrar_estadisticas()
    
    # Panel Admin
    if st.session_state.rol == "Administrador" and admin_opcion:
        if admin_opcion == "Gestionar Usuarios":
            mostrar_admin_usuarios()
        elif admin_opcion == "Procesar PDFs":
            mostrar_admin_pdfs()
        elif admin_opcion == "Estado de BD":
            mostrar_admin_bd()
        elif admin_opcion == "Registros de Acceso":
            mostrar_admin_accesos()
        elif admin_opcion == "Estadísticas IA":
            mostrar_admin_estadisticas_ia()

def mostrar_chat():
    """Mostrar interfaz de chat"""
    
    st.markdown("# 💬 Chat Corporativo IA")
    st.markdown("Consulta documentos de **parafiscales** y **pensiones** con IA")
    
    # Input con Enter
    with st.form("form_chat", clear_on_submit=True):
        col_input, col_button = st.columns([0.85, 0.15])
        
        with col_input:
            user_input = st.text_area(
                "Tu pregunta:",
                placeholder="Ej: ¿Cuáles son las políticas de pensión?",
                height=80,
                label_visibility="collapsed",
                key="input_chat"
            )
        
        with col_button:
            submit = st.form_submit_button("📤 Enviar", use_container_width=True)
        
        if submit and user_input.strip():
            logger.info(f"📨 Mensaje de {st.session_state.usuario}: {user_input[:50]}")
            
            with st.spinner("⏳ Procesando pregunta..."):
                try:
                    respuesta = st.session_state.chat_processor.procesar_mensaje(
                        mensaje=user_input,
                        contexto={'rol': st.session_state.rol}
                    )
                    
                    if respuesta['exitoso']:
                        st.success("✅ Respuesta generada")
                        # No agregamos manualmente: procesar_mensaje() ya guarda
                        # la respuesta en chat_processor.historial_local
                    else:
                        st.error(f"❌ Error: {respuesta['respuesta']}")
                
                except Exception as e:
                    logger.error(f"❌ Error: {e}", exc_info=True)
                    st.error(f"❌ Error procesando:\n{str(e)}")
    
    # Historial
    st.markdown("### 📜 Historial de Conversación")
    
    # Leer SIEMPRE el historial vivo desde el chat_processor para evitar
    # referencias obsoletas tras limpiar el chat
    historial_actual = []
    if st.session_state.chat_processor:
        historial_actual = st.session_state.chat_processor.historial_local
    
    if historial_actual:
        # Mostrar en orden inverso (más recientes primero)
        for msg in reversed(historial_actual[-20:]):
            with st.container():
                col1, col2 = st.columns([0.1, 0.9])
                
                with col1:
                    st.markdown("👤")
                
                with col2:
                    st.markdown(f"**Tu pregunta:**")
                    st.markdown(f"_{msg['mensaje_original']}_")
                
                st.divider()
                
                col1, col2 = st.columns([0.1, 0.9])
                
                with col1:
                    st.markdown("🤖")
                
                with col2:
                    if msg['exitoso']:
                        st.markdown(f"**Respuesta IA:**")
                        st.markdown(msg['respuesta'])
                        
                        # Mostrar fuentes
                        if msg.get('sources'):
                            with st.expander(f"📚 Fuentes ({len(msg['sources'])})"):
                                for i, source in enumerate(msg['sources'], 1):
                                    st.markdown(f"**Fuente {i}: {source['archivo']}**")
                                    st.caption(f"Página: {source['metadata'].get('page', 'N/A')}")
                                    st.text(source['contenido'][:300] + "...")
                    else:
                        st.error(msg['respuesta'])
                
                st.caption(f"⏱️ {msg['timestamp'][:19]}")
                st.divider()
    else:
        st.info("💭 Sin historial aún. ¡Haz una pregunta!")

def mostrar_estadisticas():
    """Mostrar estadísticas"""
    
    st.markdown("# 📊 Estadísticas")
    
    motor = st.session_state.motor_ia
    stats = motor.obtener_estado()['estadisticas']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stats-card">
        <h3>📊 Queries Totales</h3>
        <div class="value">{stats['queries_totales']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-card">
        <h3>✅ Exitosas</h3>
        <div class="value">{stats['queries_exitosas']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-card">
        <h3>❌ Fallidas</h3>
        <div class="value">{stats['queries_fallidas']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        tasa_exito = (
            (stats['queries_exitosas'] / stats['queries_totales'] * 100)
            if stats['queries_totales'] > 0 else 0
        )
        st.markdown(f"""
        <div class="stats-card">
        <h3>📈 Tasa Éxito</h3>
        <div class="value">{tasa_exito:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

def mostrar_admin_usuarios():
    """Panel de gestión de usuarios"""
    
    st.markdown("## 👥 Gestión de Usuarios")
    
    usuarios = cargar_usuarios()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Usuarios Actuales")
        
        for usuario, datos in usuarios.items():
            col_user, col_rol, col_delete = st.columns([3, 2, 1])
            
            with col_user:
                st.text(f"👤 {usuario}")
            
            with col_rol:
                st.text(f"🏷️ {datos['rol']}")
            
            with col_delete:
                if st.button("🗑️", key=f"delete_{usuario}"):
                    del usuarios[usuario]
                    guardar_usuarios(usuarios)
                    st.success(f"✅ {usuario} eliminado")
                    st.rerun()
    
    with col2:
        st.markdown("### ➕ Nuevo Usuario")
        
        nuevo_user = st.text_input("Usuario", key="admin_new_user")
        nueva_pass = st.text_input("Contraseña", type="password", key="admin_new_pass")
        nuevo_rol = st.selectbox("Rol", ["Analista", "Administrador"], key="admin_new_rol")
        
        if st.button("➕ Crear", use_container_width=True):
            if not nuevo_user or not nueva_pass:
                st.error("❌ Completa todos los campos")
            elif nuevo_user in usuarios:
                st.error("❌ Usuario ya existe")
            else:
                usuarios[nuevo_user] = {
                    "contraseña": nueva_pass,
                    "rol": nuevo_rol
                }
                guardar_usuarios(usuarios)
                st.success(f"✅ Usuario '{nuevo_user}' creado")
                st.rerun()

def mostrar_admin_pdfs():
    """Panel de procesamiento de PDFs"""
    
    st.markdown("## 📄 Procesar Documentos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📁 Parafiscales")
        if st.button("🔄 Procesar carpeta parafiscales", key="btn_parafiscales"):
            with st.spinner("⏳ Procesando parafiscales..."):
                try:
                    processor = cargar_data_processor()
                    if not processor:
                        st.error("❌ Error cargando procesador")
                        return
                    
                    resultado = processor.procesar_carpeta(
                        "Manual Paraficales",
                        "parafiscales"
                    )
                    
                    if resultado['exito']:
                        st.success(f"✅ {resultado['archivos_procesados']} archivos procesados")
                        st.info(f"📊 {resultado['chunks_creados']} chunks creados")
                    else:
                        st.error(f"❌ {resultado.get('error', 'Error desconocido')}")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.markdown("### 📁 Pensiones")
        if st.button("🔄 Procesar carpeta pensiones", key="btn_pensiones"):
            with st.spinner("⏳ Procesando pensiones..."):
                try:
                    processor = cargar_data_processor()
                    if not processor:
                        st.error("❌ Error cargando procesador")
                        return
                    
                    resultado = processor.procesar_carpeta(
                        "Manual Pensiones",
                        "pensiones"
                    )
                    
                    if resultado['exito']:
                        st.success(f"✅ {resultado['archivos_procesados']} archivos procesados")
                        st.info(f"📊 {resultado['chunks_creados']} chunks creados")
                    else:
                        st.error(f"❌ {resultado.get('error', 'Error desconocido')}")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

def mostrar_admin_bd():
    """Panel estado de base de datos"""
    
    st.markdown("## 💾 Estado de Base de Datos")
    
    try:
        processor = cargar_data_processor()
        if not processor:
            st.error("❌ Error cargando procesador")
            return
        
        estado = processor.obtener_estado_bd()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📄 Documentos", estado['documentos'])
        
        with col2:
            st.metric("💾 Tamaño (MB)", estado['tamaño_mb'])
        
        with col3:
            st.metric("🔧 Estado", estado['estado'].upper())
        
        st.divider()
        
        if st.button("🗑️ Limpiar base de datos", type="secondary"):
            if st.confirm("⚠️ ¿Estás seguro? Esto eliminará todos los documentos."):
                with st.spinner("🔄 Limpiando..."):
                    if processor.limpiar_vectorstore():
                        st.success("✅ Base de datos limpiada")
                        st.rerun()
                    else:
                        st.error("❌ Error limpiando BD")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def mostrar_admin_accesos():
    """Panel de registros de acceso"""
    
    st.markdown("## 📋 Registro de Accesos")
    
    try:
        if Path("logs/registro_conexiones.csv").exists():
            import pandas as pd
            df = pd.read_csv("logs/registro_conexiones.csv")
            
            st.dataframe(df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                logins = len(df[df['Acción'] == 'LOGIN'])
                st.metric("🔓 Logins Totales", logins)
            
            with col2:
                logouts = len(df[df['Acción'] == 'LOGOUT'])
                st.metric("🚪 Logouts Totales", logouts)
        else:
            st.info("ℹ️ No hay registros aún")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def mostrar_admin_estadisticas_ia():
    """Panel de estadísticas IA"""
    
    st.markdown("## 🤖 Estadísticas IA")
    
    motor = st.session_state.motor_ia
    estado = motor.obtener_estado()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Estado del Motor")
        for key, value in estado.items():
            if key != 'estadisticas':
                st.text(f"**{key}:** {value}")
    
    with col2:
        st.markdown("### Estadísticas")
        stats = estado['estadisticas']
        for key, value in stats.items():
            st.text(f"**{key}:** {value}")

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
