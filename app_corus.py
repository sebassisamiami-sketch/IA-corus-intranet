# app_corus.py - Aplicación Principal Streamlit
"""
CorusIntranetEngine v2.0
Sistema de Intranet con IA para consultas de documentos corporativos
Arquitectura modular con gestión de sesiones y autenticación
"""

import streamlit as st
import logging
import os
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Importar módulos de la aplicación
try:
    from ia_motor import CorusIntranetEngine
    from chat_procesos import ChatProcessor
    from procesar_datos import DataProcessor
except ImportError as e:
    st.error(f"❌ Error de importación: {e}")
    st.stop()

# ===== CONFIGURACIÓN GLOBAL =====

# Cargar variables de entorno
load_dotenv()

# Crear directorios necesarios
DIRECTORIOS = ["data/pdfs", "data/db", "data/sessions", "logs"]
for directorio in DIRECTORIOS:
    Path(directorio).mkdir(parents=True, exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== CREDENCIALES (CAMBIAR EN PRODUCCIÓN) =====
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
    * {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    }
    
    .login-container {
        background: rgba(255, 255, 255, 0.95);
        padding: 40px;
        border-radius: 15px;
        backdrop-filter: blur(10px);
        max-width: 400px;
        margin: 50px auto;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        color: #333;
    }
    
    .login-container h1, .login-container h3 {
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
    
    .success-box {
        background: rgba(76, 175, 80, 0.2);
        border-left: 4px solid #4CAF50;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .error-box {
        background: rgba(244, 67, 54, 0.2);
        border-left: 4px solid #f44336;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .message-user {
        background: rgba(102, 126, 234, 0.3);
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        text-align: right;
    }
    
    .message-ai {
        background: rgba(255, 255, 255, 0.1);
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
    }
    
    .header-title {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ===== GESTIÓN DE SESIÓN =====

def inicializar_sesion():
    """Inicializar variables de sesión"""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.session_state.rol = None
        st.session_state.chat_processor = None
        st.session_state.motor_ia = None
        st.session_state.historial = []
        st.session_state.ultimo_acceso = None
        st.session_state.inicio_sesion = None

def verificar_autenticacion() -> bool:
    """Verificar si el usuario está autenticado"""
    return st.session_state.autenticado

def registrar_acceso(usuario: str, rol: str, accion: str = "LOGIN"):
    """Registrar acceso en CSV"""
    try:
        archivo_log = "logs/registro_conexiones.csv"
        archivo_existe = os.path.exists(archivo_log)
        
        with open(archivo_log, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            if not archivo_existe:
                writer.writerow(['Timestamp', 'Usuario', 'Rol', 'Acción', 'IP'])
            
            writer.writerow([
                datetime.now().isoformat(),
                usuario,
                rol,
                accion,
                'local'  # En producción, obtener IP real
            ])
    except Exception as e:
        logger.error(f"Error registrando acceso: {e}")

# ===== PANTALLA DE LOGIN =====

def pantalla_login():
    """Renderizar pantalla de login"""
    
    # Centrar contenido
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        
        st.markdown("# 🤖 Corus Intranet Engine")
        st.markdown("## v2.0")
        st.markdown("### Sistema de IA Corporativo")
        
        st.markdown("---")
        
        with st.form("login_form", clear_on_submit=True):
            usuario = st.text_input(
                "👤 Usuario",
                placeholder="Ingresa tu usuario"
            )
            
            rol = st.selectbox(
                "🔐 Rol",
                ["Analista", "Administrador"],
                help="Selecciona tu rol en la organización"
            )
            
            contraseña = st.text_input(
                "🔑 Contraseña",
                type="password",
                placeholder="Ingresa tu contraseña"
            )
            
            col1_btn, col2_btn = st.columns(2)
            with col1_btn:
                submit = st.form_submit_button(
                    "🔓 Iniciar Sesión",
                    use_container_width=True
                )
            with col2_btn:
                st.form_submit_button(
                    "ℹ️ Ayuda",
                    use_container_width=True,
                    disabled=True
                )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Procesar login
        if submit:
            if not usuario or not contraseña:
                st.error("❌ Por favor completa todos los campos")
                return
            
            # Validar credenciales
            if contraseña == CREDENCIALES.get(rol):
                # Login exitoso
                st.session_state.autenticado = True
                st.session_state.usuario = usuario
                st.session_state.rol = rol
                st.session_state.inicio_sesion = datetime.now()
                st.session_state.ultimo_acceso = datetime.now()
                
                # Registrar acceso
                registrar_acceso(usuario, rol, "LOGIN")
                
                # Inicializar módulos
                try:
                    with st.spinner("⏳ Inicializando sistema..."):
                        st.session_state.motor_ia = CorusIntranetEngine()
                        st.session_state.motor_ia.load_vectorstore()
                        st.session_state.motor_ia.setup_chain()
                        
                        st.session_state.chat_processor = ChatProcessor(usuario, rol)
                        st.session_state.chat_processor._cargar_memoria_usuario()
                        st.session_state.historial = st.session_state.chat_processor.historial_local
                        
                        logger.info(f"✅ {usuario} ({rol}) autenticado exitosamente")
                    
                    st.success(f"✅ ¡Bienvenido {usuario}!")
                    st.rerun()
                
                except Exception as e:
                    logger.error(f"Error inicializando: {e}")
                    st.error(f"❌ Error inicializando sistema: {e}")
            else:
                st.error("❌ Credenciales inválidas")
                logger.warning(f"Intento de login fallido para usuario: {usuario}")

# ===== PANTALLA PRINCIPAL (POST-LOGIN) =====

def pantalla_principal():
    """Renderizar pantalla principal después de login"""
    
    # ===== SIDEBAR =====
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.usuario}")
        st.markdown(f"**Rol:** `{st.session_state.rol}`")
        
        if st.session_state.inicio_sesion:
            tiempo_sesion = datetime.now() - st.session_state.inicio_sesion
            st.markdown(f"⏱️ Sesión: {tiempo_sesion.seconds // 60}m")
        
        st.markdown("---")
        
        # Opciones generales
        st.markdown("### 📋 Opciones")
        
        if st.button("🧹 Limpiar Historial", use_container_width=True):
            if st.session_state.chat_processor:
                st.session_state.chat_processor.limpiar_historial()
                st.session_state.historial = []
                st.success("✅ Historial limpiado")
                st.rerun()
        
        if st.button("📊 Ver Estadísticas", use_container_width=True):
            st.session_state.mostrar_stats = not st.session_state.get('mostrar_stats', False)
            st.rerun()
        
        st.markdown("---")
        
        # Panel Administrativo (solo administradores)
        if st.session_state.rol == "Administrador":
            st.markdown("### ⚙️ Panel Administrativo")
            
            if st.button("📥 Procesar PDFs", use_container_width=True, key="procesar_pdfs"):
                st.session_state.procesar_pdfs_modal = True
            
            if st.button("📊 Ver BD Documentos", use_container_width=True):
                st.session_state.mostrar_bd_modal = True
            
            st.markdown("---")
        
        # Cerrar sesión
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
            registrar_acceso(st.session_state.usuario, st.session_state.rol, "LOGOUT")
            
            st.session_state.autenticado = False
            st.session_state.usuario = None
            st.session_state.rol = None
            st.session_state.motor_ia = None
            st.session_state.chat_processor = None
            st.session_state.historial = []
            
            logger.info(f"✅ Sesión cerrada para {st.session_state.usuario}")
            st.rerun()
    
    # ===== CONTENIDO PRINCIPAL =====
    
    st.markdown("""
    <div class='header-title'>
        <h1>💬 Chat IA Corus</h1>
        <p>Consulta documentos corporativos con inteligencia artificial</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar estadísticas si se solicita
    if st.session_state.get('mostrar_stats', False):
        with st.expander("📊 Estadísticas de Uso", expanded=True):
            if st.session_state.chat_processor:
                stats = st.session_state.chat_processor.obtener_estadisticas()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📨 Mensajes", stats['total_mensajes'])
                with col2:
                    st.metric("✅ Exitosos", stats['exitosos'])
                with col3:
                    st.metric("❌ Fallidos", stats['fallidos'])
                with col4:
                    st.metric("📊 Tasa Éxito", stats['tasa_exito'])
                
                st.markdown(f"**Promedio de respuesta:** {stats['promedio_respuesta_caracteres']} caracteres")
    
    # Modal procesamiento de PDFs (Admin)
    if st.session_state.get('procesar_pdfs_modal', False):
        with st.container():
            st.markdown("### 📥 Procesar Documentos PDF")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📂 PDFs Disponibles")
                try:
                    processor = DataProcessor()
                    pdfs = processor.listar_pdfs()
                    
                    if pdfs:
                        for nombre, tamaño in pdfs:
                            st.markdown(f"📄 **{nombre}** ({tamaño:.1f} KB)")
                    else:
                        st.info("No hay PDFs en data/pdfs/")
                except Exception as e:
                    st.error(f"Error: {e}")
            
            with col2:
                st.markdown("#### 🔧 Opciones de Procesamiento")
                
                modo = st.radio("Modo:", ["Crear nuevo", "Agregar a existente"])
                
                if st.button("▶️ Iniciar Procesamiento", use_container_width=True):
                    with st.spinner("⏳ Procesando documentos..."):
                        try:
                            processor = DataProcessor()
                            resultado = processor.procesar_todos(
                                modo="create" if modo == "Crear nuevo" else "add"
                            )
                            
                            if resultado['exitoso']:
                                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                                st.markdown(f"### {resultado['mensaje']}")
                                
                                detalles = resultado['detalles']
                                col1_d, col2_d, col3_d = st.columns(3)
                                
                                with col1_d:
                                    st.metric("📄 PDFs", detalles.get('pdfs_procesados', 0))
                                with col2_d:
                                    st.metric("📄 Documentos", detalles.get('documentos_cargados', 0))
                                with col3_d:
                                    st.metric("⏱️ Tiempo (s)", detalles.get('tiempo_segundos', 0))
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                logger.info(f"Procesamiento exitoso por {st.session_state.usuario}")
                            else:
                                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                                st.markdown(f"### {resultado['mensaje']}")
                                st.markdown('</div>', unsafe_allow_html=True)
                        
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                            logger.error(f"Error procesando: {e}")
            
            st.markdown("---")
            if st.button("Cerrar", use_container_width=True):
                st.session_state.procesar_pdfs_modal = False
                st.rerun()
    
    # Modal BD Documentos (Admin)
    if st.session_state.get('mostrar_bd_modal', False):
        with st.container():
            st.markdown("### 📊 Base de Datos de Documentos")
            
            try:
                processor = DataProcessor()
                stats_bd = processor.obtener_estadisticas()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📄 PDFs Disponibles", stats_bd['pdfs_disponibles'])
                with col2:
                    st.metric("📚 Documentos", stats_bd['total_documentos'])
                with col3:
                    st.metric("💾 Tamaño BD", f"{stats_bd['tamaño_db_mb']} MB")
                with col4:
                    st.metric("⏱️ Último Update", 
                             stats_bd['ultima_actualizacion'][:10] 
                             if stats_bd['ultima_actualizacion'] != 'Nunca' 
                             else 'Nunca')
                
                if st.button("🗑️ Limpiar BD (PELIGROSO)", use_container_width=True):
                    if st.checkbox("✓ Confirmar limpieza"):
                        with st.spinner("Limpiando..."):
                            processor.limpiar_vectorstore()
                            st.success("✅ BD limpiada")
                            st.rerun()
            
            except Exception as e:
                st.error(f"Error: {e}")
            
            st.markdown("---")
            if st.button("Cerrar", use_container_width=True, key="cerrar_bd"):
                st.session_state.mostrar_bd_modal = False
                st.rerun()
    
    # ===== ÁREA DE CHAT =====
    st.markdown("### 💬 Conversación")
    
    # Input del usuario
    col_input, col_button = st.columns([0.85, 0.15])
    
    with col_input:
        user_input = st.text_input(
            "Escribe tu pregunta:",
            placeholder="Ejemplo: ¿Cuáles son las políticas de seguridad?",
            label_visibility="collapsed"
        )
    
    with col_button:
        enviar = st.button("📤", help="Enviar mensaje", use_container_width=True)
    
    # Procesar mensaje
    if enviar and user_input:
        with st.spinner("⏳ Procesando tu pregunta..."):
            try:
                respuesta = st.session_state.chat_processor.procesar_mensaje(
                    mensaje=user_input,
                    contexto={
                        'rol': st.session_state.rol
                    }
                )
                
                st.session_state.historial.append(respuesta)
                
                if respuesta['exitoso']:
                    st.success("✅ Respuesta generada")
                else:
                    st.warning(f"⚠️ Error: {respuesta.get('error', {}).get('mensaje', 'Desconocido')}")
                
                st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error procesando mensaje: {e}")
                logger.error(f"Error: {e}")
    
    # Mostrar historial de conversación
    st.markdown("### 📜 Historial")
    
    if st.session_state.historial:
        # Botón para limpiar
        col_hist_1, col_hist_2 = st.columns([0.8, 0.2])
        with col_hist_2:
            if st.button("🗑️", help="Limpiar historial"):
                st.session_state.chat_processor.limpiar_historial()
                st.session_state.historial = []
                st.rerun()
        
        # Mostrar mensajes en orden inverso (más recientes primero)
        for msg in reversed(st.session_state.historial):
            with st.container():
                # Mensaje del usuario
                st.markdown(f"""
                <div class='message-user'>
                    <strong>👤 Tú:</strong> {msg['mensaje_original']}
                </div>
                """, unsafe_allow_html=True)
                
                # Respuesta de IA
                if msg['exitoso']:
                    st.markdown(f"""
                    <div class='message-ai'>
                        <strong>🤖 IA:</strong> {msg['respuesta']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Mostrar fuentes si existen
                    if msg['sources']:
                        with st.expander("📚 Fuentes"):
                            for source in msg['sources']:
                                st.markdown(f"""
                                - **Archivo:** {source.get('source', 'N/A')}
                                - **Página:** {source.get('página', 'N/A')}
                                - **Vista previa:** {source.get('contenido_preview', 'N/A')[:100]}...
                                """)
                else:
                    st.markdown(f"""
                    <div class='error-box'>
                        <strong>❌ Error:</strong> {msg['respuesta']}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Timestamp
                st.caption(f"⏱️ {msg['timestamp'][:16]}")
                st.divider()
    else:
        st.info("💭 No hay mensajes aún. ¡Haz una pregunta para empezar!")

# ===== FUNCIÓN MAIN =====

def main():
    """Función principal de la aplicación"""
    
    # Inicializar sesión
    inicializar_sesion()
    
    # Renderizar pantalla correspondiente
    if verificar_autenticacion():
        pantalla_principal()
    else:
        pantalla_login()

if __name__ == "__main__":
    main()
