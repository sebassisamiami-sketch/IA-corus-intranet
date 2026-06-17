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

import base64

def _logo_data_uri():
    """Devuelve el logo como data URI para incrustarlo en HTML (bienvenida)."""
    try:
        if LOGO_PATH.exists():
            data = base64.b64encode(LOGO_PATH.read_bytes()).decode()
            return f"data:image/png;base64,{data}"
    except Exception:
        pass
    return ""

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
import html
from datetime import datetime, timedelta
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
        _autoindexar_documentos(motor)
        logger.info("✅ Motor IA listo")
        return motor
    except Exception as e:
        logger.error(f"❌ Error cargando motor: {e}")
        return None

def detectar_carpetas_documentos():
    """Detecta las carpetas (a nivel raíz del repo) que contienen PDFs.
    Cada una se trata como una sección. Devuelve una lista de nombres."""
    base = Path(__file__).parent
    excluir = {".git", ".streamlit", ".devcontainer", ".agents", "data",
               "logs", "__pycache__", ".github"}
    carpetas = []
    try:
        for d in sorted(base.iterdir(), key=lambda x: x.name.lower()):
            if d.is_dir() and d.name not in excluir and not d.name.startswith("."):
                if any(True for _ in d.rglob("*.pdf")):
                    carpetas.append(d.name)
    except Exception as e:
        logger.error(f"Error detectando carpetas: {e}")
    return carpetas

def subcarpetas_con_pdfs(nombre_carpeta):
    """Lista las subcarpetas (y PDFs sueltos) que contienen PDFs dentro de una carpeta."""
    base = Path(__file__).parent / nombre_carpeta
    subs = []
    try:
        for sub in sorted(base.iterdir(), key=lambda x: x.name.lower()):
            if sub.is_dir():
                n = len(list(sub.rglob("*.pdf")))
                if n > 0:
                    subs.append((sub.name, n))
        pdfs_raiz = list(base.glob("*.pdf"))
        if pdfs_raiz:
            subs.append(("(archivos sueltos)", len(pdfs_raiz)))
    except Exception:
        pass
    return subs

def _autoindexar_documentos(motor):
    """Indexa los PDFs del repo automaticamente si el indice esta vacio.

    Streamlit Cloud borra el disco en cada redespliegue, por eso reconstruimos
    el indice al arrancar para que la IA siempre tenga los documentos.
    """
    try:
        if not motor or not getattr(motor, "vectorstore", None):
            return
        try:
            count = motor.vectorstore._collection.count()
        except Exception:
            count = 0
        if count and count > 0:
            logger.info(f"📚 Indice ya tiene {count} documentos")
            return
        logger.info("📚 Indice vacio: indexando PDFs automaticamente...")
        from procesar_datos import DataProcessor
        processor = DataProcessor()
        total = 0
        for carpeta in detectar_carpetas_documentos():
            res = processor.procesar_carpeta(carpeta, carpeta)
            if res.get('exito'):
                total += res.get('chunks_creados', 0)
        logger.info(f"✅ Auto-indexado completado: {total} chunks")
    except Exception as e:
        logger.error(f"⚠️ Error auto-indexando: {e}", exc_info=True)

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

# ===== ESTADO DEL SERVIDOR (interruptor de mantenimiento) =====
# Se guarda en la raíz del repo para que también pueda controlarse desde fuera (.bat)
ESTADO_APP_PATH = Path(__file__).parent / "estado_app.json"

def leer_estado_app() -> bool:
    """True si el servidor está activo; False si está en mantenimiento."""
    try:
        if ESTADO_APP_PATH.exists():
            with open(ESTADO_APP_PATH, 'r', encoding='utf-8') as f:
                return bool(json.load(f).get("servidor_activo", True))
    except Exception:
        pass
    return True

def guardar_estado_app(activo: bool) -> bool:
    """Guarda el estado del servidor (activo o mantenimiento)."""
    try:
        with open(ESTADO_APP_PATH, 'w', encoding='utf-8') as f:
            json.dump({"servidor_activo": bool(activo)}, f, ensure_ascii=False, indent=2)
        logger.info(f"🖥️ Estado del servidor: activo={activo}")
        return True
    except Exception as e:
        logger.error(f"Error guardando estado del servidor: {e}")
        return False

def cargar_usuarios() -> Dict[str, Dict]:
    """Cargar usuarios combinando: por defecto + Secrets (permanentes) + archivo local.

    - Secrets: persisten siempre (recomendado para los compañeros del equipo).
    - Archivo local (data/usuarios.json): creados en la app, se pierden al redesplegar.
    """
    # 1) Usuarios por defecto
    usuarios = {
        "admin": {"contraseña": "admin123", "rol": "Administrador"},
        "analista": {"contraseña": "analista123", "rol": "Analista"}
    }

    # 2) Usuarios PERMANENTES definidos en Streamlit Secrets ([usuarios.<nombre>])
    try:
        secret_users = st.secrets.get("usuarios", None)
        if secret_users:
            for nombre, datos in dict(secret_users).items():
                datos = dict(datos)
                usuarios[nombre] = {
                    "contraseña": datos.get("contraseña", datos.get("password", "")),
                    "rol": datos.get("rol", "Analista")
                }
    except Exception:
        pass

    # 3) Usuarios creados en la app (temporales hasta el próximo redespliegue)
    if Path(ARCHIVO_USUARIOS).exists():
        try:
            with open(ARCHIVO_USUARIOS, 'r', encoding='utf-8') as f:
                usuarios.update(json.load(f))
        except Exception:
            pass

    return usuarios

def guardar_usuarios(usuarios: Dict):
    """Guardar usuarios en archivo"""
    Path("data").mkdir(exist_ok=True)
    with open(ARCHIVO_USUARIOS, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)
    logger.info("✅ Usuarios guardados")

def _verificar_password(plano: str, almacenado: str) -> bool:
    """Verifica la contraseña. Soporta hash bcrypt y texto plano (compatibilidad)."""
    if not isinstance(almacenado, str) or plano is None:
        return False
    # ¿Es un hash bcrypt?
    if almacenado.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            import bcrypt
            return bcrypt.checkpw(plano.encode("utf-8"), almacenado.encode("utf-8"))
        except Exception:
            return False
    # Texto plano (sigue funcionando para no romper nada)
    return plano == almacenado

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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Tipografía profesional en toda la app */
    html, body, [class*="css"], .stApp,
    section.main, section[data-testid="stSidebar"],
    input, textarea, button, select {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    }

    /* Ocultar barra/herramientas de Streamlit (Deploy, menu, footer) y franja blanca superior */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
    }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }

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
    
    /* Sidebar estilo ChatGPT (oscuro) */
    section[data-testid="stSidebar"] {
        background: #171717 !important;
        border-right: 1px solid #2a2a2a;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
        color: #ececf1 !important;
    }
    section[data-testid="stSidebar"] hr { border-color: #2a2a2a !important; }
    /* Selectbox del sidebar en oscuro */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: #2a2a2a !important;
        color: #ececf1 !important;
        border-color: #3a3a3a !important;
    }
    /* Botones del sidebar en oscuro */
    section[data-testid="stSidebar"] .stButton button {
        background: #2a2a2a !important;
        color: #ececf1 !important;
        border: 1px solid #3a3a3a !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #343541 !important;
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

    /* ===== CHAT MODERNO Y MINIMALISTA ===== */
    .chat-bubble {
        border-radius: 14px;
        padding: 14px 18px;
        margin: 8px 0;
        line-height: 1.5;
        animation: fadeIn .25s ease;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .user-bubble {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff;
        margin-left: 18%;
        box-shadow: 0 4px 14px rgba(102, 126, 234, 0.25);
    }
    .ai-bubble {
        background: #f4f6fb;
        color: #1f2937;
        margin-right: 12%;
        border: 1px solid #e6e9f2;
    }
    .bubble-label {
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .6px;
        text-transform: uppercase;
        opacity: .75;
        margin-bottom: 4px;
    }
    .bubble-text { font-size: .95rem; }
    .chat-time {
        font-size: .7rem;
        color: #9ca3af;
        margin: 2px 0 14px 0;
    }

    /* ===== FUENTES ESTILO VENTANA DE COMANDOS / TERMINAL ===== */
    div[data-testid="stCodeBlock"] {
        background: #0d1117 !important;
        border-radius: 10px;
        border: 1px solid #30363d;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
        overflow: hidden;
    }
    div[data-testid="stCodeBlock"] pre {
        background: #0d1117 !important;
        color: #c9d1d9 !important;
        padding: 16px !important;
        font-size: .82rem !important;
    }
    div[data-testid="stCodeBlock"] code { color: #c9d1d9 !important; }
    /* Barra superior tipo ventana con tres "botones" */
    .terminal-bar {
        background: #161b22;
        border: 1px solid #30363d;
        border-bottom: none;
        border-radius: 10px 10px 0 0;
        padding: 8px 12px;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .75rem;
        color: #8b949e;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .terminal-bar .dot {
        width: 11px; height: 11px; border-radius: 50%;
        display: inline-block;
    }
    .terminal-bar .red    { background: #ff5f56; }
    .terminal-bar .yellow { background: #ffbd2e; }
    .terminal-bar .green  { background: #27c93f; }
    .terminal-bar .title  { margin-left: 10px; }
    /* Pega el code block a la barra del terminal */
    .terminal-bar + div[data-testid="stCodeBlock"] {
        border-radius: 0 0 10px 10px;
        margin-top: 0;
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
        "ip": "local",
        "intentos_fallidos": 0,
        "bloqueo_hasta": None,
        "ultima_actividad": None
    }
    
    for var, valor_default in variables_default.items():
        if var not in st.session_state:
            st.session_state[var] = valor_default

# ===== PANTALLA LOGIN =====
def pantalla_login():
    """Pantalla de login"""
    
    usuarios = cargar_usuarios()
    
    col1, col2, col3 = st.columns([1, 12, 1])
    
    with col2:
        # Estilos estilo Microsoft (tarjeta blanca centrada) SOLO para login
        st.markdown("""
        <style>
            /* Fondo gris claro estilo Microsoft */
            [data-testid="stAppViewContainer"] { background: #f2f2f2; }
            [data-testid="stHeader"] { background: transparent; }

            /* Tarjeta central blanca */
            section.main .block-container {
                max-width: 470px;
                background: #ffffff;
                padding: 44px 44px 36px 44px;
                margin-top: 6vh;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
                border-radius: 2px;
            }

            /* Encabezado */
            .ms-title {
                font-size: 1.55rem; font-weight: 600;
                color: #1b1b1b; margin: 16px 0 6px 0;
            }
            .ms-sub { color: #605e5c; font-size: .9rem; margin-bottom: 20px; }

            /* Etiquetas */
            section.main .stTextInput label,
            section.main .stSelectbox label {
                color: #1b1b1b !important; font-weight: 600; font-size: .85rem;
            }
            /* Inputs estilo Microsoft (borde recto) */
            section.main .stTextInput input,
            section.main div[data-baseweb="select"] > div {
                background: #ffffff !important;
                color: #1b1b1b !important;
                border: 1px solid #8a8886 !important;
                border-radius: 0 !important;
            }
            section.main .stTextInput input:focus {
                border-color: #0067b8 !important;
                box-shadow: none !important;
            }
            /* Botón azul Microsoft */
            section.main .stButton button[kind="primary"] {
                background: #0067b8 !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 0 !important;
                font-weight: 600;
            }
            section.main .stButton button[kind="primary"]:hover {
                background: #005da6 !important;
                transform: none;
                box-shadow: none;
            }
        </style>
        """, unsafe_allow_html=True)

        # Logo (estilo Microsoft, arriba a la izquierda)
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=108)

        st.markdown('<div class="ms-title">Iniciar sesión</div>', unsafe_allow_html=True)
        st.markdown('<div class="ms-sub">Usa tu cuenta corporativa de Corus</div>', unsafe_allow_html=True)
        
        # Seleccionar usuario
        usuarios_list = list(usuarios.keys())
        usuario_seleccionado = st.selectbox(
            "Cuenta",
            usuarios_list,
            key="select_usuario_login"
        )
        
        contraseña = st.text_input(
            "Contraseña",
            type="password",
            key="input_password_login"
        )
        
        col_login = st.container()
        
        with col_login:
            if st.button("Iniciar sesión", use_container_width=True, type="primary"):
                
                # 🔒 Bloqueo temporal por intentos fallidos
                bloqueo_hasta = st.session_state.get("bloqueo_hasta")
                if bloqueo_hasta and datetime.now() < bloqueo_hasta:
                    restante = int((bloqueo_hasta - datetime.now()).total_seconds())
                    st.error(f"🔒 Demasiados intentos. Intenta de nuevo en {restante} segundos.")
                    return

                if not contraseña:
                    st.error("❌ Ingresa la contraseña")
                    return
                
                usuario_data = usuarios.get(usuario_seleccionado)
                
                if not usuario_data or not _verificar_password(contraseña, usuario_data.get('contraseña', '')):
                    st.session_state.intentos_fallidos = st.session_state.get("intentos_fallidos", 0) + 1
                    intentos = st.session_state.intentos_fallidos
                    logger.warning(f"Intento fallido ({intentos}/5): {usuario_seleccionado}")
                    if intentos >= 5:
                        st.session_state.bloqueo_hasta = datetime.now() + timedelta(minutes=2)
                        st.session_state.intentos_fallidos = 0
                        st.error("🔒 Demasiados intentos fallidos. Cuenta bloqueada por 2 minutos.")
                    else:
                        st.error(f"❌ Credenciales inválidas ({intentos}/5 intentos)")
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
                        st.session_state.ultima_actividad = datetime.now()
                        st.session_state.intentos_fallidos = 0
                        st.session_state.bloqueo_hasta = None
                        
                        # Registrar
                        registrar_acceso(usuario_seleccionado, usuario_data['rol'], "LOGIN")
                        
                        logger.info(f"✅ Login exitoso: {usuario_seleccionado}")
                        st.success(f"✅ ¡Bienvenido {usuario_seleccionado}!")
                        st.rerun()
                    
                    except Exception as e:
                        logger.error(f"❌ Error: {e}", exc_info=True)
                        st.error(f"❌ Error iniciando sistema:\n{str(e)}")
        
        # Nota discreta de acceso (la gestión de usuarios es solo para admin)
        st.markdown(
            "<p style='text-align:center; color:#64748b; font-size:.78rem; "
            "margin-top:22px;'>Acceso restringido &middot; La gestión de usuarios "
            "está disponible para administradores</p>",
            unsafe_allow_html=True
        )

        # 🚧 Aviso de mantenimiento si el servidor está cerrado
        if not leer_estado_app():
            st.markdown(
                "<div style='text-align:center; margin-top:16px; padding:14px; "
                "background:#3a1d1d; border:1px solid #b91c1c; border-radius:10px; "
                "color:#fca5a5; font-weight:600;'>🚧 En mantenimiento</div>",
                unsafe_allow_html=True
            )

# ===== PANTALLA PRINCIPAL =====
def pantalla_principal():
    """Pantalla principal después de login"""

    # 🚧 Si el servidor está en mantenimiento, solo el Administrador puede entrar
    if not leer_estado_app() and st.session_state.rol != "Administrador":
        st.markdown(
            "<div style='text-align:center; margin-top:22vh;'>"
            "<h1 style='color:#ececf1;'>🚧 En mantenimiento</h1>"
            "<p style='color:#9a9a9a;'>El servidor está temporalmente cerrado. "
            "Por favor vuelve a intentarlo más tarde.</p></div>",
            unsafe_allow_html=True
        )
        st.stop()

    # Sidebar expandible con tema profesional
    with st.sidebar:
        # Logo de la empresa
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_column_width=True)

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
                    "— Inicio —",
                    "Gestionar Usuarios",
                    "Procesar PDFs",
                    "Estado de BD",
                    "Registros de Acceso",
                    "Estadísticas IA",
                    "Control del Servidor",
                    "Video a Manual"
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
    mostrar_admin = (
        st.session_state.rol == "Administrador"
        and admin_opcion
        and admin_opcion != "— Inicio —"
    )

    if mostrar_admin:
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
        elif admin_opcion == "Control del Servidor":
            mostrar_admin_servidor()
        elif admin_opcion == "Video a Manual":
            mostrar_admin_video()
    elif opcion == "💬 Chat":
        mostrar_chat()
    elif opcion == "📊 Estadísticas":
        mostrar_estadisticas()

def mostrar_chat():
    """Interfaz de chat estilo ChatGPT (oscuro, minimalista y fiel)"""

    # ===== TEMA OSCURO ESTILO CHATGPT =====
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"], section.main {
            background-color: #212121 !important;
        }
        /* Columna de conversacion centrada y estrecha */
        section.main .block-container {
            max-width: 900px;
            padding-top: 1.5rem;
            padding-bottom: 9rem;
        }
        section.main h1, section.main h2, section.main h3, section.main h4 {
            color: #ececf1 !important;
        }
        section.main .stMarkdown p, section.main .stMarkdown li,
        section.main .stMarkdown strong {
            color: #ececf1 !important;
            font-size: 1rem;
            line-height: 1.75;
        }
        section.main [data-testid="stCaptionContainer"] * { color: #9a9a9a !important; }

        /* Pantalla de bienvenida centrada */
        .welcome-screen { text-align: center; margin-top: 16vh; }
        .welcome-logo { width: 64px; height: auto; margin-bottom: 18px; }
        .welcome-title {
            color: #ececf1; font-weight: 600; font-size: 2rem;
            margin: 0; letter-spacing: -0.5px;
        }
        .welcome-sub { color: #9a9a9a; font-size: .95rem; margin-top: 8px; }

        /* Mensajes estilo ChatGPT */
        [data-testid="stChatMessage"] {
            background: transparent !important;
            padding: 10px 0 !important;
        }
        [data-testid="stChatMessage"] * { color: #ececf1 !important; }
        /* Avatar (logo) sin recortar: se ve completo y encuadrado */
        [data-testid="stChatMessage"] img {
            object-fit: contain !important;
            background: transparent !important;
            padding: 2px !important;
        }

        /* Barra inferior y caja de entrada estilo ChatGPT */
        [data-testid="stChatFloatingInputContainer"],
        div[class*="stChatFloatingInputContainer"],
        [data-testid="stBottom"],
        [data-testid="stBottom"] > div,
        [data-testid="stBottomBlockContainer"] {
            background-color: #212121 !important;
            border-top: none !important;
            box-shadow: none !important;
        }
        /* ===== Barra de busqueda estilo Gemini ===== */
        [data-testid="stChatInput"] {
            background: #1e1f20 !important;
            border: 1px solid #3c4043 !important;
            border-radius: 28px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
            padding: 8px 14px !important;
            transition: border-color .2s ease, box-shadow .2s ease;
        }
        [data-testid="stChatInput"]:focus-within {
            border-color: #8ab4f8 !important;
            box-shadow: 0 0 0 2px rgba(138, 180, 248, 0.30),
                        0 6px 26px rgba(0, 0, 0, 0.55) !important;
        }
        /* Quitar TODOS los bordes internos (elimina el segundo borde) */
        [data-testid="stChatInput"] *:not(button) {
            background: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        /* Boton de enviar circular con degradado */
        [data-testid="stChatInput"] button {
            background: linear-gradient(135deg, #8ab4f8, #4a7fe0) !important;
            border-radius: 50% !important;
            border: none !important;
            color: #ffffff !important;
            box-shadow: 0 2px 10px rgba(138, 180, 248, 0.5);
            transition: filter .2s ease, transform .1s ease;
        }
        [data-testid="stChatInput"] button:hover { filter: brightness(1.15); }
        [data-testid="stChatInput"] button:active { transform: scale(0.92); }
        [data-testid="stChatInput"] button svg {
            fill: #ffffff !important;
            color: #ffffff !important;
        }
        [data-testid="stChatInput"] textarea,
        textarea[data-testid="stChatInputTextArea"],
        [data-testid="stChatInput"] [data-baseweb="textarea"] textarea,
        section.main [data-testid="stChatInput"] textarea {
            background: transparent !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #8ab4f8 !important;
            opacity: 1 !important;
            font-size: 1.02rem !important;
            line-height: 1.5 !important;
            padding: 6px 8px !important;
        }
        [data-testid="stChatInput"] textarea::placeholder,
        textarea[data-testid="stChatInputTextArea"]::placeholder {
            color: #9a9aa8 !important;
            -webkit-text-fill-color: #9a9aa8 !important;
        }

        /* Expander de fuentes */
        section.main [data-testid="stExpander"] {
            border: 1px solid #3a3a3a !important;
            border-radius: 10px !important;
            background: #1a1a1a !important;
        }
        section.main [data-testid="stExpander"] summary,
        section.main [data-testid="stExpander"] summary * { color: #ececf1 !important; }

        /* Caja de entrada un poco más gruesa */
        [data-testid="stChatInput"] { padding: 10px 16px !important; }
        [data-testid="stChatInput"] textarea {
            min-height: 54px !important;
            padding-top: 10px !important;
        }

        /* Botón de adjuntar compacto (estilo clip), no una caja grande */
        [data-testid="stFileUploader"] { margin-bottom: 8px; }
        [data-testid="stFileUploader"] label { color: #9a9aa8 !important; font-size: .8rem; }
        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
            display: none !important;
        }
        [data-testid="stFileUploader"] section {
            padding: 6px 10px !important;
            min-height: 0 !important;
            background: #2f2f2f !important;
            border: 1px solid #4d4f5c !important;
            border-radius: 12px !important;
        }
        [data-testid="stFileUploader"] section button {
            background: linear-gradient(135deg, #8ab4f8, #4a7fe0) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    def _render_fuentes(sources):
        """Renderiza las fuentes como ventana de comandos / terminal."""
        if not sources:
            return
        with st.expander(f"📚 Fuentes ({len(sources)})"):
            for i, source in enumerate(sources, 1):
                archivo = html.escape(str(source.get('archivo', 'documento')))
                pagina = source.get('metadata', {}).get('page', 'N/A')
                st.markdown(f"""
<div class="terminal-bar">
<span class="dot red"></span>
<span class="dot yellow"></span>
<span class="dot green"></span>
<span class="title">fuente {i} &mdash; {archivo} &middot; pag. {pagina}</span>
</div>
""", unsafe_allow_html=True)
                st.code(source['contenido'], language="text")

    # Leer el historial vivo desde el chat_processor
    historial_actual = []
    if st.session_state.chat_processor:
        historial_actual = st.session_state.chat_processor.historial_local

    # Avatar del asistente: usa el logo de Corus (con respaldo a emoji)
    avatar_ia = str(LOGO_PATH) if LOGO_PATH.exists() else "🤖"

    if not historial_actual:
        # Pantalla de bienvenida centrada estilo ChatGPT
        logo_uri = _logo_data_uri()
        logo_html = f'<img src="{logo_uri}" class="welcome-logo"/>' if logo_uri else ''
        st.markdown(f"""
<div class="welcome-screen">
{logo_html}
<h1 class="welcome-title">¿En qué puedo ayudarte?</h1>
<p class="welcome-sub">Consulta documentos de parafiscales y pensiones con IA</p>
</div>
""", unsafe_allow_html=True)
    else:
        # Conversacion en orden cronologico (estilo ChatGPT)
        for msg in historial_actual[-30:]:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(str(msg.get('mensaje_original', '')))
            with st.chat_message("assistant", avatar=avatar_ia):
                if msg.get('exitoso'):
                    st.markdown(msg.get('respuesta', ''))
                    _render_fuentes(msg.get('sources'))
                else:
                    st.error(msg.get('respuesta', 'Error'))

    # Adjuntar imagen (opcional) para analizar casos de BPM / Service Manager / WetMethods
    imagen = st.file_uploader(
        "📎 Adjuntar imagen del caso (opcional)",
        type=["png", "jpg", "jpeg", "webp"],
        key="img_chat"
    )

    # Entrada fija abajo (estilo ChatGPT) - patron oficial, SIN st.rerun()
    user_input = st.chat_input("Escribe tu pregunta...")
    if user_input and user_input.strip():
        logger.info(f"📨 Mensaje de {st.session_state.usuario}: {user_input[:50]}")

        # Mostrar la pregunta del usuario de inmediato (con la imagen si la adjuntó)
        with st.chat_message("user", avatar="🧑"):
            if imagen is not None:
                st.image(imagen, width=300)
            st.markdown(user_input)

        # Generar y mostrar la respuesta del asistente
        with st.chat_message("assistant", avatar=avatar_ia):
            if imagen is not None:
                # ----- Caso con IMAGEN (análisis de visión) -----
                with st.spinner("Analizando la imagen..."):
                    try:
                        from vision_chat import analizar_imagen
                        # Grounding opcional con la documentación
                        ctx_doc = ""
                        try:
                            motor = st.session_state.motor_ia
                            if motor and getattr(motor, "vectorstore", None) and user_input.strip():
                                ds = motor.vectorstore.similarity_search(user_input, k=2)
                                ctx_doc = "\n\n".join(d.page_content for d in ds)
                        except Exception:
                            ctx_doc = ""
                        r = analizar_imagen(
                            user_input, imagen.getvalue(),
                            getattr(imagen, "type", "image/png"), ctx_doc
                        )
                        st.markdown(r)
                        # Guardar en el historial (como texto, para continuidad)
                        try:
                            st.session_state.chat_processor.historial_local.append({
                                "exitoso": True,
                                "mensaje_original": user_input + "  [imagen adjunta]",
                                "respuesta": r, "sources": [],
                                "timestamp": datetime.now().isoformat(),
                                "usuario": st.session_state.usuario,
                                "rol": st.session_state.rol, "modo": "VISION",
                            })
                        except Exception:
                            pass
                    except Exception as e:
                        logger.error(f"❌ Error visión: {e}", exc_info=True)
                        st.error(f"❌ Error analizando la imagen: {e}")
            else:
                # ----- Caso solo TEXTO (RAG normal) -----
                with st.spinner("Pensando..."):
                    try:
                        respuesta = st.session_state.chat_processor.procesar_mensaje(
                            mensaje=user_input,
                            contexto={'rol': st.session_state.rol}
                        )
                    except Exception as e:
                        logger.error(f"❌ Error: {e}", exc_info=True)
                        st.error(f"❌ Error procesando: {str(e)}")
                        return

                if respuesta.get('exitoso'):
                    st.markdown(respuesta.get('respuesta', ''))
                    _render_fuentes(respuesta.get('sources'))
                else:
                    st.error(respuesta.get('respuesta', 'Error'))


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

    # 🔐 Generador de contraseñas cifradas (para usar en Secrets, más seguro)
    with st.expander("🔐 Generar contraseña cifrada (hash) para Secrets"):
        st.caption("Escribe una contraseña y copia el hash resultante en tus Secrets. "
                   "Así no la guardas en texto plano.")
        pwd_plana = st.text_input("Contraseña a cifrar", type="password", key="gen_hash_pwd")
        if st.button("🔒 Generar hash", key="btn_gen_hash"):
            if not pwd_plana:
                st.warning("Escribe una contraseña primero.")
            else:
                try:
                    import bcrypt
                    h = bcrypt.hashpw(pwd_plana.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    st.success("✅ Hash generado. Cópialo en tus Secrets como 'password':")
                    st.code(h, language="text")
                    st.caption("Ejemplo en Secrets:")
                    st.code(
                        f'[usuarios.nombre]\npassword = "{h}"\nrol = "Analista"',
                        language="toml"
                    )
                except Exception as e:
                    st.error(f"No se pudo generar el hash: {e}")

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
    """Panel de procesamiento de PDFs (dinámico: una sección por carpeta del repo)."""
    st.markdown("## 📄 Procesar Documentos")

    carpetas = detectar_carpetas_documentos()
    if not carpetas:
        st.info("ℹ️ No se detectaron carpetas con PDFs en el repositorio. "
                "Sube una carpeta con PDFs a GitHub y aparecerá aquí automáticamente.")
        return

    st.caption(
        f"Se detectaron **{len(carpetas)}** carpeta(s) con documentos. "
        "Cada carpeta nueva que subas a GitHub aparecerá aquí automáticamente "
        "(y se indexa sola al iniciar la app)."
    )

    # Botón para procesar TODAS las carpetas
    if st.button("🔄 Procesar TODAS las carpetas", type="primary", use_container_width=True):
        processor = cargar_data_processor()
        if not processor:
            st.error("❌ Error cargando procesador")
        else:
            total = 0
            with st.spinner("⏳ Procesando todas las carpetas..."):
                for c in carpetas:
                    res = processor.procesar_carpeta(c, c)
                    if res.get('exito'):
                        total += res.get('chunks_creados', 0)
            st.success(f"✅ Listo. {total} fragmentos indexados en total.")

    st.divider()

    # Una sección independiente por cada carpeta
    for carpeta in carpetas:
        st.markdown(f"### 📁 {carpeta}")

        subs = subcarpetas_con_pdfs(carpeta)
        if subs:
            for nombre_sub, n in subs:
                st.markdown(f"&nbsp;&nbsp;&nbsp;📂 **{nombre_sub}** — {n} PDF(s)", unsafe_allow_html=True)
        else:
            st.caption("Sin subcarpetas con PDFs.")

        if st.button(f"🔄 Procesar '{carpeta}'", key=f"btn_proc_{carpeta}"):
            processor = cargar_data_processor()
            if not processor:
                st.error("❌ Error cargando procesador")
            else:
                with st.spinner(f"⏳ Procesando {carpeta}..."):
                    try:
                        resultado = processor.procesar_carpeta(carpeta, carpeta)
                        if resultado['exito']:
                            st.success(f"✅ {resultado['archivos_procesados']} archivos procesados")
                            st.info(f"📊 {resultado['chunks_creados']} chunks creados")
                        else:
                            st.error(f"❌ {resultado.get('error', 'Error desconocido')}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        st.divider()

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
def mostrar_admin_video():
    """Panel: convertir un video en el contenido de un manual (PDF)."""
    st.markdown("## 🎬 Video a Manual (PDF)")
    st.caption("Sube un video o audio, la IA lo transcribe, lo resume en formato de manual "
               "y genera un PDF descargable.")

    archivo = st.file_uploader(
        "Sube el video o audio",
        type=["mp4", "mov", "mkv", "webm", "m4a", "mp3", "wav", "mpeg", "mpga"],
        key="uploader_video"
    )
    # El título del caso se toma del NOMBRE DEL ARCHIVO (editable)
    titulo_def = os.path.splitext(archivo.name)[0] if archivo else "Manual"
    titulo = st.text_input(
        "Título del caso (se toma del nombre del archivo, puedes editarlo)",
        value=titulo_def,
        key=f"titulo_manual_{archivo.name if archivo else 'none'}"
    )

    st.caption("💡 Recomendado: videos de pocos minutos. Para videos largos puede tardar más.")

    if st.button("⚙️ Generar manual", type="primary", use_container_width=True):
        if not archivo:
            st.warning("Primero sube un archivo de video o audio.")
            return
        try:
            import tempfile
            from video_a_manual import procesar_video

            sufijo = "." + archivo.name.split(".")[-1].lower()
            with tempfile.NamedTemporaryFile(suffix=sufijo, delete=False) as tmp:
                tmp.write(archivo.getbuffer())
                ruta = tmp.name

            with st.spinner("⏳ Procesando: extrayendo audio, transcribiendo y resumiendo..."):
                resultado = procesar_video(ruta, titulo)

            try:
                os.remove(ruta)
            except Exception:
                pass

            st.success("✅ Manual generado")

            # Descargar PDF
            st.download_button(
                "⬇️ Descargar manual (PDF)",
                data=resultado["pdf"],
                file_name=f"{titulo.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            # Vista previa del manual
            with st.expander("👀 Vista previa del manual", expanded=True):
                st.markdown(resultado["manual"])

            # Transcripción completa
            with st.expander("📝 Transcripción completa"):
                st.text_area(
                    "Texto transcrito",
                    value=resultado["transcripcion"],
                    height=350,
                    label_visibility="collapsed"
                )

        except Exception as e:
            st.error(f"❌ Error procesando el video: {e}")

def mostrar_admin_servidor():
    """Panel para cerrar/activar el servidor (modo mantenimiento)."""
    st.markdown("## 🖥️ Control del Servidor")

    activo = leer_estado_app()

    if activo:
        st.success("🟢 El servidor está **ACTIVO**. Los usuarios pueden usar la aplicación.")
        st.caption("Al cerrar el servidor, los usuarios verán '🚧 En mantenimiento' en el login y no podrán ingresar (solo el administrador).")
        if st.button("🔴 Cerrar servidor", type="primary", use_container_width=True):
            if guardar_estado_app(False):
                st.warning("🚧 Servidor **CERRADO**. Los usuarios verán el mensaje de mantenimiento.")
                st.rerun()
            else:
                st.error("❌ No se pudo actualizar el estado.")
    else:
        st.error("🔴 El servidor está **CERRADO** (en mantenimiento). Los usuarios no pueden ingresar.")
        if st.button("🟢 Activar servidor", type="primary", use_container_width=True):
            if guardar_estado_app(True):
                st.success("✅ Servidor **ACTIVADO**. Los usuarios ya pueden ingresar.")
                st.rerun()
            else:
                st.error("❌ No se pudo actualizar el estado.")

    st.divider()
    st.caption(
        "ℹ️ Este interruptor afecta la instancia en ejecución de inmediato. "
        "Tras un redespliegue, el servidor vuelve a su estado guardado en el repositorio "
        "(estado_app.json). Para apagarlo de forma permanente desde tu PC, usa el script externo (.bat)."
    )

def main():
    """Función principal"""
    inicializar_sesion()
    
    if st.session_state.autenticado:
        # 🔒 Auto-logout por inactividad (15 minutos)
        ahora = datetime.now()
        ultima = st.session_state.get("ultima_actividad")
        if ultima and (ahora - ultima) > timedelta(minutes=15):
            try:
                registrar_acceso(st.session_state.usuario, st.session_state.rol, "TIMEOUT")
            except Exception:
                pass
            st.session_state.autenticado = False
            st.session_state.usuario = None
            st.session_state.rol = None
            st.session_state.motor_ia = None
            st.session_state.chat_processor = None
            st.session_state.historial = []
            st.session_state.ultima_actividad = None
            st.warning("⏱️ Tu sesión se cerró por inactividad (15 minutos). Inicia sesión nuevamente.")
            pantalla_login()
            return
        # Renovar el tiempo de actividad en cada interacción
        st.session_state.ultima_actividad = ahora
        pantalla_principal()
    else:
        pantalla_login()

if __name__ == "__main__":
    main()
