# =====================================================================
# CorusIntranetEngine v2.0 - APP PRINCIPAL
# =====================================================================
# Fecha: 2026
# Descripción: Interfaz RAG integrada con autenticación, gestión de sesiones
#              y memoria de largo plazo basada en disco.
# =====================================================================

import streamlit as st
import time
import os
import datetime
import glob
import json
import logging
import warnings
from pathlib import Path
from typing import List, Dict, Optional

# Suprimir warnings
warnings.filterwarnings('ignore')

# ========== IMPORTAR MÓDULO PRINCIPAL ==========
try:
    from chat_procesos import CorusIntranetEngine
except ImportError as e:
    st.error(f"❌ Error importando módulo: {e}")
    st.stop()

# ========== CONFIGURACIÓN DE LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== CONSTANTES ==========
ARCHIVO_ESTADO = "estado_servidor.txt"
ARCHIVO_LOGS = "registro_conexiones.csv"
ARCHIVO_MEMORIA_CHATS = "memoria_largo_plazo.json"
LIMITE_ADVERTENCIA = 300      # 5 minutos
LIMITE_EXPULSION = 360        # 6 minutos
INTERVALO_AUTOREFRESH = 30000  # 30 segundos

# ========== DIRECTORIOS ==========
DIRS_REQUERIDOS = ["data/pdfs", "data/db", "data/sessions", "logs"]
for directorio in DIRS_REQUERIDOS:
    Path(directorio).mkdir(parents=True, exist_ok=True)

# =====================================================================
# 1. CONFIGURACIÓN DE PÁGINA
# =====================================================================

st.set_page_config(
    page_title="IA Corus - Procesos",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 2. FUNCIONES AUXILIARES
# =====================================================================

def verificar_estado_servidor() -> bool:
    """Verifica si el servidor está activo."""
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                estado = f.read().strip()
                return estado != "OFFLINE"
        except Exception as e:
            logger.error(f"Error verificando estado: {e}")
            return True
    return True


def cargar_memoria_disco(usuario_clave: str) -> List[Dict]:
    """
    Carga el historial de chat desde disco para un usuario específico.
    
    Args:
        usuario_clave: Identificador único del usuario (usuario_rol)
    
    Returns:
        Lista de mensajes del historial o lista vacía si no existe
    """
    if not os.path.exists(ARCHIVO_MEMORIA_CHATS):
        return []
    
    try:
        with open(ARCHIVO_MEMORIA_CHATS, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(usuario_clave, [])
    except Exception as e:
        logger.warning(f"Error cargando memoria para {usuario_clave}: {e}")
        return []


def guardar_memoria_disco(usuario_clave: str, historial: List[Dict]) -> None:
    """
    Guarda el historial de chat en disco de forma persistente.
    
    Args:
        usuario_clave: Identificador único del usuario (usuario_rol)
        historial: Lista de mensajes a guardar
    """
    try:
        # Cargar datos existentes
        data = {}
        if os.path.exists(ARCHIVO_MEMORIA_CHATS):
            try:
                with open(ARCHIVO_MEMORIA_CHATS, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        
        # Actualizar con nuevo historial
        data[usuario_clave] = historial
        
        # Guardar
        with open(ARCHIVO_MEMORIA_CHATS, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Memoria guardada para {usuario_clave}")
    except Exception as e:
        logger.error(f"Error guardando memoria: {e}")


def registrar_acceso(usuario: str, rol: str) -> None:
    """
    Registra un acceso en el archivo de logs.
    
    Args:
        usuario: Nombre del usuario
        rol: Rol del usuario (Analista/Administrador)
    """
    try:
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario_limpio = usuario.replace(",", " ").strip()
        
        with open(ARCHIVO_LOGS, "a", encoding="utf-8") as f:
            f.write(f"{ahora},{usuario_limpio},{rol}\n")
        
        logger.info(f"Acceso registrado: {usuario_limpio} ({rol})")
    except Exception as e:
        logger.error(f"Error registrando acceso: {e}")


def obtener_ultimos_logs(lineas: int = 50) -> List[Dict]:
    """Obtiene los últimos accesos registrados."""
    if not os.path.exists(ARCHIVO_LOGS):
        return []
    
    try:
        with open(ARCHIVO_LOGS, "r", encoding="utf-8") as f:
            todas_lineas = f.readlines()
        
        datos = []
        for linea in reversed(todas_lineas[-lineas:]):
            partes = linea.strip().split(",")
            if len(partes) == 3:
                datos.append({
                    "Fecha/Hora": partes[0],
                    "Usuario": partes[1],
                    "Rol": partes[2]
                })
        return datos
    except Exception as e:
        logger.error(f"Error leyendo logs: {e}")
        return []


def cambiar_estado_servidor(nuevo_estado: str) -> None:
    """Cambia el estado del servidor."""
    try:
        if nuevo_estado == "OFFLINE":
            with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
                f.write("OFFLINE")
        else:
            if os.path.exists(ARCHIVO_ESTADO):
                os.remove(ARCHIVO_ESTADO)
        logger.info(f"Estado del servidor cambiado a: {nuevo_estado}")
    except Exception as e:
        logger.error(f"Error cambiando estado: {e}")


def obtener_estructura_pdfs() -> Dict[str, set]:
    """
    Obtiene la estructura de carpetas de PDFs disponibles.
    
    Returns:
        Diccionario con estructura de directorios
    """
    secciones = {}
    try:
        for ruta in glob.glob("**/*.pdf", recursive=True):
            # Filtrar rutas indeseadas
            if any(x in ruta for x in ["chroma_db", ".git", "__pycache__", ".venv", "venv"]):
                continue
            
            partes = os.path.normpath(ruta).split(os.sep)
            if len(partes) >= 2:
                raiz = partes[0]
                subcat = partes[-2] if len(partes) > 2 else "General"
                
                if raiz not in secciones:
                    secciones[raiz] = set()
                secciones[raiz].add(subcat)
    except Exception as e:
        logger.warning(f"Error obteniendo estructura de PDFs: {e}")
    
    return secciones


# =====================================================================
# 3. INICIALIZACIÓN DE SESIÓN
# =====================================================================

# Estado de autenticación
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "usuario_identidad" not in st.session_state:
    st.session_state.usuario_identidad = ""

if "rol_usuario" not in st.session_state:
    st.session_state.rol_usuario = "Analista"

if "es_admin" not in st.session_state:
    st.session_state.es_admin = False

if "ultimo_acceso" not in st.session_state:
    st.session_state.ultimo_acceso = time.time()

if "dialogo_abierto" not in st.session_state:
    st.session_state.dialogo_abierto = False

if "historial_pantalla" not in st.session_state:
    st.session_state.historial_pantalla = []

if "pensando" not in st.session_state:
    st.session_state.pensando = False

if "motor_ia" not in st.session_state:
    st.session_state.motor_ia = None

# =====================================================================
# 4. DIÁLOGOS DE INTERFAZ
# =====================================================================

@st.dialog("👁️ Monitor de Accesos Corporativos")
def mostrar_monitor_conexiones():
    """Muestra el diálogo del monitor de conexiones."""
    st.markdown("### Últimos Accesos Registrados")
    
    datos = obtener_ultimos_logs(100)
    if datos:
        st.dataframe(
            datos,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        st.info(f"📊 Total de accesos registrados: {len(datos)}")
    else:
        st.info("⚠️ Aún no hay conexiones registradas.")


@st.dialog("⚠️ Alerta de Inactividad")
def mostrar_ventana_caducidad():
    """Muestra alerta de sesión por caducar."""
    st.session_state.dialogo_abierto = True
    
    st.warning(
        "⏰ Tu sesión está a punto de cerrarse por seguridad tras 5 minutos sin actividad.",
        icon="⏰"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Mantener en línea", use_container_width=True, key="btn_mantener"):
            st.session_state.ultimo_acceso = time.time()
            st.session_state.dialogo_abierto = False
            st.rerun()
    
    with col2:
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_cerrar"):
            st.session_state.autenticado = False
            st.session_state.es_admin = False
            st.session_state.dialogo_abierto = False
            st.rerun()


# =====================================================================
# 5. CARGA DEL MOTOR IA (SINGLETON)
# =====================================================================

@st.cache_resource(show_spinner=False)
def cargar_motor_central() -> "CorusIntranetEngine":
    """
    Carga el motor IA una única vez (cached).
    
    Returns:
        Instancia del CorusIntranetEngine
    """
    try:
        logger.info("Inicializando CorusIntranetEngine...")
        motor = CorusIntranetEngine()
        logger.info("Motor IA cargado exitosamente")
        return motor
    except Exception as e:
        logger.error(f"Error cargando motor IA: {e}")
        st.error(f"❌ Error al inicializar el sistema: {str(e)}")
        st.stop()


# =====================================================================
# 6. PANEL DE LOGIN
# =====================================================================

if not st.session_state.autenticado:
    # Verificar estado del servidor
    sitio_activo = verificar_estado_servidor()
    
    # Interfaz de login
    st.title("🏢 Acceso Restringido - CorusIntranetEngine")
    st.divider()
    
    if not sitio_activo:
        st.error("⚠️ SISTEMA EN MANTENIMIENTO - Por favor, intente más tarde.")
    
    # Formulario de login
    with st.form("formulario_login", border=True):
        st.markdown("### Autenticación de Usuario")
        
        usuario_input = st.text_input(
            "Nombre y Apellido:",
            placeholder="Ej. Juan Pérez",
            help="Ingresa tu nombre completo"
        )
        
        pwd = st.text_input(
            "Contraseña:",
            type="password",
            help="Contraseña de acceso corporativo"
        )
        
        btn_ingresar = st.form_submit_button(
            "🔐 Iniciar Sesión",
            use_container_width=True,
            type="primary"
        )
        
        if btn_ingresar:
            if not usuario_input.strip() or not pwd:
                st.warning("⚠️ Por favor, completa todos los campos.")
            
            elif not sitio_activo:
                st.error("❌ Sistema en mantenimiento.")
            
            # Verificar credenciales
            elif pwd == "FarmeoAura*26*****":
                nombre_formateado = usuario_input.strip().replace(" ", "_")
                registrar_acceso(usuario_input.strip(), "Analista")
                
                st.session_state.update(
                    autenticado=True,
                    usuario_identidad=nombre_formateado,
                    rol_usuario="Analista",
                    es_admin=False,
                    ultimo_acceso=time.time()
                )
                
                # Cargar memoria desde disco
                clave = f"{nombre_formateado}_Analista"
                st.session_state.historial_pantalla = cargar_memoria_disco(clave)
                
                st.success("✅ Autenticación exitosa. Redirigiendo...")
                time.sleep(1)
                st.rerun()
            
            elif pwd == "Pipeline**2038******":
                nombre_formateado = usuario_input.strip().replace(" ", "_")
                registrar_acceso(usuario_input.strip(), "Administrador")
                
                st.session_state.update(
                    autenticado=True,
                    usuario_identidad=nombre_formateado,
                    rol_usuario="Administrador",
                    es_admin=True,
                    ultimo_acceso=time.time()
                )
                
                # Cargar memoria desde disco
                clave = f"{nombre_formateado}_Administrador"
                st.session_state.historial_pantalla = cargar_memoria_disco(clave)
                
                st.success("✅ Autenticación exitosa. Redirigiendo...")
                time.sleep(1)
                st.rerun()
            
            else:
                st.error("❌ Contraseña incorrecta.")
    
    st.divider()
    st.caption("🔒 Acceso restringido a personal autorizado de Corus | v2.0")
    st.stop()

# =====================================================================
# 7. INTERFAZ PRINCIPAL (POST-LOGIN)
# =====================================================================

# Verificar estado del servidor
sitio_activo = verificar_estado_servidor()

# Expulsar usuarios si servidor está offline (excepto admins)
if not sitio_activo and not st.session_state.es_admin:
    st.session_state.autenticado = False
    st.rerun()

# Cargar motor IA
motor_ia = cargar_motor_central()
clave_memoria_actual = f"{st.session_state.usuario_identidad}_{st.session_state.rol_usuario}"

# ========== ESTILOS CSS ==========
st.markdown("""
    <style>
    /* Ocultar elementos por defecto */
    #MainMenu, footer, .stAppDeployButton {
        visibility: hidden;
        display: none !important;
    }
    
    header {
        background: transparent !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(20px) !important;
    }
    
    /* Cards */
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
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.2);
    }
    
    .folder-icon {
        color: #60a5fa;
        font-size: 18px;
    }
    
    .folder-text {
        color: #e2e8f0;
        font-size: 14px;
        font-weight: 500;
    }
    
    /* Tips */
    .tip-container {
        background: rgba(59, 130, 246, 0.05);
        border-left: 3px solid #3b82f6;
        padding: 15px;
        border-radius: 5px;
        margin-top: 20px;
    }
    
    .tip-text {
        font-size: 13px;
        color: #94a3b8;
    }
    
    /* Botones */
    div.stButton > button {
        background: rgba(128, 128, 128, 0.1) !important;
        color: #f8fafc !important;
        border-radius: 10px !important;
        text-transform: uppercase;
        font-size: 12px;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        background: rgba(128, 128, 128, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ========== HEADER ==========
col1, col2 = st.columns([1, 4])

with col1:
    if os.path.exists("logo_corus.png"):
        st.image("logo_corus.png", width=100)
    else:
        st.markdown("<h1>🏢</h1>", unsafe_allow_html=True)

with col2:
    st.title("Asistente Virtual Corus")
    st.caption(
        f"🔐 **{st.session_state.rol_usuario}** | "
        f"👤 **{st.session_state.usuario_identidad.replace('_', ' ')}**"
    )

st.divider()

# ========== SIDEBAR ==========
with st.sidebar:
    # Panel Admin
    if st.session_state.es_admin:
        st.markdown("### 🚨 PANEL MAESTRO")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("👁️ CONEXIONES", use_container_width=True):
                mostrar_monitor_conexiones()
        
        with col2:
            if sitio_activo:
                if st.button("🔴 APAGAR", use_container_width=True):
                    cambiar_estado_servidor("OFFLINE")
                    st.rerun()
            else:
                if st.button("🟢 ACTIVAR", use_container_width=True):
                    cambiar_estado_servidor("ONLINE")
                    st.rerun()
        
        st.markdown("---")
    
    # Sección de configuración
    st.markdown("### 🛠️ Configuración")
    
    # Estructura de PDFs
    secciones = obtener_estructura_pdfs()
    if secciones:
        st.markdown("#### 📁 Documentación Disponible")
        for raiz in sorted(secciones.keys()):
            with st.expander(f"📂 {raiz}", expanded=False):
                for subcat in sorted(secciones[raiz]):
                    st.markdown(
                        f'<div class="folder-card">'
                        f'<span class="folder-icon">📄</span>'
                        f'<span class="folder-text">{subcat}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
    
    st.markdown("---")
    
    # Botones de control
    st.markdown("#### 🎛️ Control de Sesión")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpiar Chat", use_container_width=True):
            st.session_state.historial_pantalla = []
            guardar_memoria_disco(clave_memoria_actual, [])
            st.success("✅ Chat limpiado")
            st.rerun()
    
    with col2:
        if st.button("🚪 Salir", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.markdown("---")
    st.caption("🔒 CorusIntranetEngine v2.0")

# ========== ÁREA DE CHAT ==========
st.markdown("### 💬 Consultorio Virtual")

# Inicializar historial si está vacío
if not st.session_state.historial_pantalla:
    st.session_state.historial_pantalla = [{
        "rol": "assistant",
        "contenido": (
            f"¡Hola **{st.session_state.usuario_identidad.replace('_', ' ')}**! 👋\n\n"
            f"Bienvenido de vuelta. Tu historial ha sido restaurado exitosamente en tu rol de "
            f"**{st.session_state.rol_usuario}**.\n\n"
            f"¿En qué caso vamos a trabajar hoy?"
        )
    }]

# Mostrar historial
for msg in st.session_state.historial_pantalla:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["contenido"])

# ========== INPUT DE USUARIO ==========
if consulta := st.chat_input("Escribe tu consulta...", key="input_chat"):
    st.session_state.ultimo_acceso = time.time()
    st.session_state.pensando = True
    
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(consulta)
    
    # Agregar al historial
    st.session_state.historial_pantalla.append({
        "rol": "user",
        "contenido": consulta
    })
    
    # Guardar inmediatamente
    guardar_memoria_disco(clave_memoria_actual, st.session_state.historial_pantalla)
    
    # Procesar con IA
    with st.chat_message("assistant"):
        with st.spinner("🔍 Consultando documentación..."):
            try:
                # Construir contexto
                contexto_usuario_actual = "\n".join([
                    f"{m['rol'].upper()}: {m['contenido']}"
                    for m in st.session_state.historial_pantalla[-5:-1]
                ])
                
                # Procesar consulta
                respuesta = motor_ia.procesar_consulta(
                    consulta,
                    contexto_usuario_actual,
                    st.session_state.rol_usuario
                )
                
                # Mostrar respuesta
                st.markdown(respuesta)
                
                # Guardar respuesta
                st.session_state.historial_pantalla.append({
                    "rol": "assistant",
                    "contenido": respuesta
                })
                
                # Persistir en disco
                guardar_memoria_disco(clave_memoria_actual, st.session_state.historial_pantalla)
                
                logger.info(f"Consulta procesada para {st.session_state.usuario_identidad}")
            
            except Exception as e:
                error_msg = f"❌ Error al procesar consulta: {str(e)}"
                st.error(error_msg)
                logger.error(f"Error procesando consulta: {e}", exc_info=True)
    
    st.session_state.pensando = False
    st.rerun()

# ========== AUTOREFRESH SILENCIOSO ==========
if not st.session_state.pensando:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(
            interval=INTERVALO_AUTOREFRESH,
            limit=None,
            key="reloj_sesion"
        )
    except ImportError:
        pass  # Si no está instalado streamlit_autorefresh, continuar sin él

# ========== CONTROL DE TIMEOUT ==========
tiempo_inactivo = time.time() - st.session_state.ultimo_acceso

if tiempo_inactivo >= LIMITE_EXPULSION:
    # Tiempo de sesión expirado
    st.session_state.autenticado = False
    st.rerun()

elif tiempo_inactivo >= LIMITE_ADVERTENCIA:
    # Mostrar advertencia
    if not st.session_state.dialogo_abierto:
        mostrar_ventana_caducidad()

# =====================================================================
# FIN DEL SCRIPT
# =====================================================================
