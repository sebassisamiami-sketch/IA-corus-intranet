import os
import sys
import warnings
import glob
import re
import shutil
import time
import logging
import traceback
from typing import List, Optional, Set, Dict, Tuple
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI

# =====================================================================
# 1. PARCHES DE INFRAESTRUCTURA Y CONFIGURACIÓN DE LOGS
# =====================================================================
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_CORE_ALLOW_RESET"] = "TRUE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

if "HOME" not in os.environ:
    os.environ["HOME"] = "/tmp"

try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

warnings.filterwarnings("ignore")

# Configuración de Logging Empresarial
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CorusEngine")

# =====================================================================
# 2. DEFINICIÓN DE ESTRUCTURAS Y CONFIGURACIÓN
# =====================================================================
class SistemaConfig:
    """Clase estática que contiene la parametrización global del sistema."""
    CARPETA_DB: str = "/tmp/corus_chroma_db"
    MODELO_EMBEDDINGS: str = "sentence-transformers/all-MiniLM-L6-v2"
    MODELO_LLM: str = "gpt-4o-mini"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200
    TEMPERATURA_LLM: float = 0.0
    TIMEOUT_CONSULTA: int = 45

class MonitorSistema:
    """Audita el estado del entorno y los permisos antes de iniciar la IA."""
    @staticmethod
    def verificar_entorno() -> bool:
        logger.info("Iniciando chequeo de salud del sistema (Health Check)...")
        # 1. Verificar permisos de la carpeta temporal
        try:
            if not os.path.exists(SistemaConfig.CARPETA_DB):
                os.makedirs(SistemaConfig.CARPETA_DB, exist_ok=True)
            test_file = os.path.join(SistemaConfig.CARPETA_DB, ".test_write")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info("✅ Permisos de escritura en volumen virtual /tmp confirmados.")
        except Exception as e:
            logger.error(f"❌ Fallo crítico de permisos en Linux: {e}")
            return False
            
        # 2. Verificar API Key
        if "OPENAI_API_KEY" not in os.environ or len(os.environ["OPENAI_API_KEY"]) < 10:
            try:
                import streamlit as st
                os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
                logger.info("✅ Llave de OpenAI cargada desde Streamlit Secrets.")
            except Exception:
                logger.critical("❌ No se detectó OPENAI_API_KEY en el entorno.")
                return False
                
        return True

# =====================================================================
# 3. PIPELINE DE EXTRACCIÓN (ETL) Y GESTIÓN DE ARCHIVOS
# =====================================================================
class PipelineETL:
    """Se encarga de la Extracción, Transformación y Carga de PDFs a la VectorDB."""
    def __init__(self, vector_db: Chroma, archivos_procesados: set):
        self.vector_db = vector_db
        self.config = SistemaConfig()
        self.archivos_procesados = archivos_procesados

    def _limpiar_texto_pdf(self, texto: str) -> str:
        """Aplica expresiones regulares para sanitizar el OCR extraído."""
        if not texto: return ""
        try:
            texto = str(texto).replace('\x00', '')
            texto = re.sub(r'(?<!\n)\n(?!\n)', ' ', texto) # Une saltos de línea huérfanos
            texto = re.sub(r'\s+', ' ', texto) # Elimina espacios múltiples
            return texto.strip()
        except Exception as e:
            logger.warning(f"Error menor limpiando texto: {e}")
            return ""

    def ejecutar_sincronizacion(self) -> Dict[str, Set[str]]:
        """Busca PDFs nuevos, los procesa y actualiza el árbol de conocimiento."""
        logger.info("Iniciando escaneo de directorio corporativo...")
        archivos_pdf = glob.glob("**/*.pdf", recursive=True)
        nuevos = [a for a in archivos_pdf if a not in self.archivos_procesados]
        arbol_conocimiento = {}

        # Mapeo del árbol existente (incluso sin archivos nuevos)
        for archivo in archivos_pdf:
            if "chroma_db" in archivo or ".git" in archivo or "__pycache__" in archivo: continue
            partes = os.path.normpath(archivo).split(os.sep)
            mod = partes[0] if len(partes) >= 2 else "Documentos Sueltos"
            cat = partes[-2] if len(partes) >= 2 else "Raíz Principal"
            
            if mod not in arbol_conocimiento:
                arbol_conocimiento[mod] = set()
            arbol_conocimiento[mod].add(cat)

        if not nuevos: 
            logger.info("No se detectaron manuales nuevos. Sincronización omitida.")
            return arbol_conocimiento

        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " ", ""], 
            chunk_size=self.config.CHUNK_SIZE, 
            chunk_overlap=self.config.CHUNK_OVERLAP
        )
        
        archivos_exitosos = 0
        archivos_fallidos = 0

        for archivo in nuevos:
            partes = os.path.normpath(archivo).split(os.sep)
            mod = partes[0] if len(partes) >= 2 else "Documentos Sueltos"
            cat = partes[-2] if len(partes) >= 2 else "Raíz Principal"
            
            try:
                reader = PdfReader(archivo)
                texto_total_archivo = 0
                for i, pag in enumerate(reader.pages):
                    txt = self._limpiar_texto_pdf(pag.extract_text())
                    
                    if txt and len(txt) > 5:
                        frags = text_splitter.split_text(txt)
                        frags_limpios = [f for f in frags if f and isinstance(f, str) and str(f).strip()]
                        
                        if frags_limpios:
                            texto_total_archivo += len(frags_limpios)
                            enriquecidos = [f"[MÓDULO: {mod} | CARPETA: {cat} | PAG: {i+1}]\n{f}" for f in frags_limpios]
                            meta = [{"modulo": mod, "categoria": cat, "fuente": os.path.basename(archivo), "pagina": i+1}] * len(frags_limpios)
                            self.vector_db.add_texts(enriquecidos, meta)
                            
                self.archivos_procesados.add(archivo)
                archivos_exitosos += 1
                logger.info(f"✅ Ingestado: {archivo} ({texto_total_archivo} frags)")
            except Exception as e:
                archivos_fallidos += 1
                logger.error(f"❌ Archivo corrupto o ilegible ({archivo}): {e}")
                
        logger.info(f"ETL Finalizado. Éxitos: {archivos_exitosos} | Fallos: {archivos_fallidos}")
        return arbol_conocimiento

# =====================================================================
# 4. ENRUTAMIENTO Y LÓGICA DE NEGOCIO
# =====================================================================
class SupervisorEnrutamiento:
    """Agente de IA que decide en qué subcarpeta debe buscar la información."""
    def __init__(self, llm: ChatOpenAI, categorias: Set[str]):
        self.llm = llm
        self.categorias = categorias

    def determinar_dominio(self, pregunta: str) -> Optional[str]:
        if not self.categorias: 
            return None
            
        categorias_str = ', '.join(self.categorias)
        prompt = f"""
        Como Enrutador de Sistema, analiza esta consulta: '{pregunta}'.
        Compara la consulta con estas subcarpetas disponibles: {categorias_str}.
        Responde ÚNICAMENTE con el nombre exacto de la subcarpeta que mejor coincida.
        Si la consulta es muy genérica o no tiene relación, responde: DESCONOCIDO.
        """
        
        try:
            resp = self.llm.invoke(prompt).content.strip()
            for cat in self.categorias:
                if cat.lower() in resp.lower(): 
                    return cat
            return None
        except Exception as e:
            logger.error(f"Fallo en el Supervisor de Enrutamiento: {e}")
            return None

# =====================================================================
# 5. MOTOR PRINCIPAL (CEREBRO CENTRAL)
# =====================================================================
class CorusIntranetEngine:
    """Clase principal que orquesta la RAG (Retrieval-Augmented Generation)."""
    
    def __init__(self):
        logger.info("Inicializando Motor Corus Intranet...")
        self.config = SistemaConfig()
        
        if not MonitorSistema.verificar_entorno():
            logger.critical("SISTEMA DETENIDO POR FALLO DE ENTORNO.")
            sys.exit(1)

        try:
            logger.info("Cargando modelo de incrustaciones (Embeddings)...")
            self.embeddings = HuggingFaceEmbeddings(model_name=self.config.MODELO_EMBEDDINGS)
            
            logger.info("Conectando a base de datos vectorial ChromaDB...")
            self.vector_db = Chroma(persist_directory=self.config.CARPETA_DB, embedding_function=self.embeddings)
            
            logger.info("Instanciando LLM (Cerebro Semántico)...")
            self.llm = ChatOpenAI(model=self.config.MODELO_LLM, temperature=self.config.TEMPERATURA_LLM)
        except Exception as e:
            logger.critical(f"Fallo en inicialización de modelos de IA: {e}")
            logger.critical(traceback.format_exc())
            sys.exit(1)
            
        self.archivos_procesados = set()
        
        # 🚨 Auto-Sincronización Silenciosa al arranque
        etl = PipelineETL(self.vector_db, self.archivos_procesados)
        self.arbol_conocimiento = etl.ejecutar_sincronizacion()
        
        try:
            # Si el disco está vacío (Reinicio de Streamlit), forzar sincronización total
            datos_existentes = self.vector_db.get()
            if not datos_existentes or 'ids' not in datos_existentes or len(datos_existentes['ids']) == 0:
                logger.warning("Base de datos detectada como vacía. Forzando ETL...")
                self.archivos_procesados.clear()
                self.arbol_conocimiento = etl.ejecutar_sincronizacion()
        except Exception as e:
            logger.error(f"Error validando la integridad de ChromaDB: {e}")
            
        todas_cats = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
        # IMPORTANTE: Eliminada la importación circular que rompía la aplicación.
        self.router = SupervisorEnrutamiento(self.llm, todas_cats)
        logger.info("Motor Corus Intranet en línea y operativo.")

    def _ejecutar_formateo_seguro(self) -> str:
        """Borra la base de datos de manera tolerante a fallos y bloqueos de SO."""
        try:
            try:
                # Borrado lógico preferido
                self.vector_db.delete_collection()
                logger.info("Colección ChromaDB borrada lógicamente.")
            except Exception as e:
                logger.warning(f"Aviso al borrar colección: {e}")
            
            # Pausa para liberar handles del disco (Linux tmpfs)
            time.sleep(1.5)
            
            # Borrado físico si existe
            if os.path.exists(self.config.CARPETA_DB):
                shutil.rmtree(self.config.CARPETA_DB, ignore_errors=True)
            os.makedirs(self.config.CARPETA_DB, exist_ok=True)
            
            # Reinstanciación limpia
            self.vector_db = Chroma(persist_directory=self.config.CARPETA_DB, embedding_function=self.embeddings)
            self.archivos_procesados.clear()
            self.arbol_conocimiento.clear()
            self.router.categorias.clear()
            
            return "⚠️ **SISTEMA:** Base de datos compartida purgada con éxito de forma segura. Escribe 'actualizar base' para reindexar."
        except Exception as e:
            error_detallado = traceback.format_exc()
            logger.error(f"Error crítico en formateo: {error_detallado}")
            return f"❌ Error crítico de infraestructura al limpiar: {str(e)}"

    def procesar_consulta(self, consulta: str, contexto_previo: str, rol_usuario: str) -> str:
        """Función principal de respuesta (Entrypoint del Chat)."""
        clean = consulta.lower().strip()
        logger.info(f"Procesando consulta de {rol_usuario} | Longitud: {len(consulta)} chars")
        
        # --- 1. FILTRO DE SALUDOS ---
        saludos = ["hola", "hola como estas", "hola cómo estás", "buenos dias", "buenas tardes", "que tal", "saludos"]
        if clean in saludos or clean.startswith("hola "):
            return f"¡Hola {rol_usuario}! ¿En qué te puedo ayudar hoy con la gestión de flujos y procesos?"

        # --- 2. FILTRO DE CIERRE DE CASOS (LIBERADOR DE FLUJO) ---
        frases_cierre = ["gracias", "caso cerrado", "ya quedo", "listo", "fin", "muchas gracias", "ok gracias"]
        if any(f == clean for f in frases_cierre) or any(clean.startswith(f) for f in frases_cierre):
            logger.info("Comando de cierre detectado. Abortando búsqueda vectorial.")
            return "🤖 **SISTEMA:** Caso cerrado formalmente. Memoria de contexto asegurada. Estoy listo para procesar un nuevo ticket o consulta."

        # --- 3. GESTIÓN DE COMANDOS DE ADMINISTRADOR ---
        if rol_usuario == "Administrador":
            if clean == "diagnostico":
                try:
                    datos = self.vector_db.get()
                    total_frags = len(datos['ids']) if datos and 'ids' in datos else 0
                    archivos = list(self.archivos_procesados)
                    resumen = f"🛠️ **REPORTE TÉCNICO E INVENTARIO:**\n- PDFs en memoria: **{len(archivos)}**\n- Fragmentos vectorizados: **{total_frags}**\n- Subcarpetas Mapeadas: {list(self.router.categorias)}"
                    return resumen
                except Exception as e:
                    return f"❌ Error recuperando diagnóstico: {e}"

            if clean == "formatear sistema":
                logger.warning("Usuario Administrador solicitó Hard Reset de la Base de Datos.")
                return self._ejecutar_formateo_seguro()

            comandos_actualizar = ["actualizar base", "cargar manuales", "actualizar manuales", "sincronizar"]
            if any(c in clean for c in comandos_actualizar):
                logger.info("Usuario Administrador solicitó recálculo de ETL.")
                etl = PipelineETL(self.vector_db, self.archivos_procesados)
                self.arbol_conocimiento = etl.ejecutar_sincronizacion()
                self.router.categorias = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
                return "🤖 **SISTEMA:** ¡Sincronización RAG completada! Base de datos compartida actualizada con éxito."
        elif clean in ["diagnostico", "formatear sistema", "actualizar base", "sincronizar"]:
            logger.warning(f"Intento de vulneración: Usuario {rol_usuario} intentó usar comandos admin.")
            return "🚫 **ACCESO DENEGADO:** Privilegios insuficientes. Este comando es exclusivo de Administradores de TI."

        # --- FASE 1: DETERMINACIÓN DE CONTEXTO (ROUTING) ---
        filtros = {}
        etiqueta_contexto = "Toda la documentación corporativa"

        modulo_detectado = next((mod for mod in self.arbol_conocimiento.keys() if mod.lower().replace("manual", "").strip() in clean and mod.lower().replace("manual", "").strip() != ""), None)

        if modulo_detectado:
            filtros["modulo"] = modulo_detectado
            etiqueta_contexto = f"Módulo: {modulo_detectado}"
        else:
            cat_detectada = self.router.determinar_dominio(consulta)
            if cat_detectada:
                filtros["categoria"] = cat_detectada
                etiqueta_contexto = f"Carpeta/Proceso: {cat_detectada}"

        # --- FASE 2: EXTRACCIÓN RAG (ESTRATEGIA FALLBACK / ALTA DISPONIBILIDAD) ---
        docs = []
        logger.info(f"Búsqueda Fase 1: Intentando coincidencia estricta en [{etiqueta_contexto}]")
        
        if filtros:
            docs = self.vector_db.similarity_search(consulta, k=20, filter=filtros)
            
        docs_validos = [d.page_content for d in docs if d and d.page_content]

        if not docs_validos:
            logger.warning("Búsqueda Fase 1 fallida. Activando Protocolo Fallback (Ampliación de espectro).")
            docs = self.vector_db.similarity_search(consulta, k=20)
            docs_validos = [d.page_content for d in docs if d and d.page_content]
            if docs_validos:
                etiqueta_contexto = "Búsqueda Ampliada (Toda la base de datos)"
        
        if not docs_validos:
            logger.error("Búsqueda Fase 2 fallida. No hay documentos legibles.")
            return f"🤖 **SISTEMA:** Busqué exhaustivamente en {etiqueta_contexto}, pero no encontré registros legibles. *(Verifique si el PDF subido es una imagen escaneada que requiera OCR previo).*."

        # --- FASE 3: GENERACIÓN AUMENTADA (INFERENCIA LLM) ---
        contexto_aislado = "\n\n".join(docs_validos)
        
        prompt_final = f"""Eres un Consultor y Analista de Procesos Senior en Corus. 
Tu misión es conversar fluidamente y resolver la duda técnica del usuario de forma precisa y estructurada.

REGLAS ESTRICTAS:
1. Extrae y formatea tu respuesta basándote EXCLUSIVAMENTE en la siguiente documentación extraída de '{etiqueta_contexto}'.
2. Si los fragmentos NO contienen la respuesta directa a la pregunta, debes ser honesto y decir exactamente: "Compañero, tras revisar {etiqueta_contexto}, no logré ubicar el procedimiento o solución explícita para este escenario en la documentación actual."
3. Usa listas, negritas y formato markdown para que el analista entienda fácilmente el proceso.

HISTORIAL PREVIO DEL CASO ACTUAL:
{contexto_previo}

DOCUMENTACIÓN OFICIAL (EXTRACCIÓN):
{contexto_aislado}

PREGUNTA DEL USUARIO: {consulta}"""

        res = ""
        try:
            logger.info("Iniciando Streaming de respuesta desde el motor LLM...")
            for chunk in self.llm.stream(prompt_final):
                res += chunk.content
            return res
        except Exception as e:
            logger.critical(f"Fallo en la conexión de Inferencia API: {e}")
            return f"❌ ERROR TÉCNICO EN LA RED: No se pudo generar la respuesta. Detalle: {str(e)}"
