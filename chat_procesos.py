import os
import sys
import warnings
import glob
import re
import shutil
from typing import List, Optional, Set, Dict
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI

# --- PARCHES DE INFRAESTRUCTURA ---
os.environ["ANONYMIZED_TELEMETRY"] = "False"
# Permiso explícito para poder resetear ChromaDB sin que marque error
os.environ["CHROMA_CORE_ALLOW_RESET"] = "TRUE"

if "HOME" not in os.environ:
    os.environ["HOME"] = "/tmp"

try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class SistemaConfig:
    # 🚨 Base de datos en memoria compartida de Linux
    CARPETA_DB: str = "/tmp/corus_chroma_db"
    MODELO_EMBEDDINGS: str = "sentence-transformers/all-MiniLM-L6-v2"
    MODELO_LLM: str = "gpt-4o-mini"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200
    TEMPERATURA_LLM: float = 0.0  

class PipelineETL:
    def __init__(self, vector_db: Chroma, archivos_procesados: set):
        self.vector_db = vector_db
        self.config = SistemaConfig()
        self.archivos_procesados = archivos_procesados

    def _limpiar_texto_pdf(self, texto: str) -> str:
        if texto is None: return ""
        texto = str(texto).replace('\x00', '')
        texto = re.sub(r'(?<!\n)\n(?!\n)', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

    def ejecutar_sincronizacion(self) -> Dict[str, Set[str]]:
        archivos_pdf = glob.glob("**/*.pdf", recursive=True)
        nuevos = [a for a in archivos_pdf if a not in self.archivos_procesados]
        arbol_conocimiento = {}

        for a in archivos_pdf:
            if "chroma_db" in a or ".git" in a or "__pycache__" in a: continue
            partes = os.path.normpath(a).split(os.sep)
            if len(partes) >= 2:
                mod, cat = partes[0], partes[-2]
            else:
                mod, cat = "General", "Raíz"
            
            if mod not in arbol_conocimiento:
                arbol_conocimiento[mod] = set()
            arbol_conocimiento[mod].add(cat)

        if not nuevos: 
            return arbol_conocimiento

        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " ", ""], 
            chunk_size=self.config.CHUNK_SIZE, 
            chunk_overlap=self.config.CHUNK_OVERLAP
        )
        
        for archivo in nuevos:
            partes = os.path.normpath(archivo).split(os.sep)
            mod = partes[0] if len(partes) >= 2 else "General"
            cat = partes[-2] if len(partes) >= 2 else "Raíz"
            
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
                print(f"✅ Ingestado: {archivo} ({texto_total_archivo} fragmentos)")
            except Exception as e: 
                print(f"❌ Error leyendo {archivo}: {e}")
                
        return arbol_conocimiento

class SupervisorEnrutamiento:
    def __init__(self, llm: ChatOpenAI, categorias: Set[str]):
        self.llm = llm
        self.categorias = categorias

    def determinar_dominio(self, pregunta: str) -> Optional[str]:
        if not self.categorias: 
            return None
        prompt = f"Determina la subcarpeta física más probable para la consulta: '{pregunta}'. Opciones: {', '.join(self.categorias)}. Responde EXCLUSIVAMENTE con el nombre de la carpeta. Si no hay relación obvia, responde: DESCONOCIDO."
        
        resp = self.llm.invoke(prompt).content.strip()
        for cat in self.categorias:
            if cat.lower() in resp.lower(): 
                return cat
        return None

class CorusIntranetEngine:
    def __init__(self):
        self.config = SistemaConfig()
        
        if "OPENAI_API_KEY" not in os.environ or os.environ["OPENAI_API_KEY"] in ["#", "sk-pega-tu-clave-aqui"]:
            try:
                import streamlit as st
                os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
            except Exception:
                pass
        
        # Crear la carpeta temporal si no existe de forma segura
        if not os.path.exists(self.config.CARPETA_DB):
            os.makedirs(self.config.CARPETA_DB, exist_ok=True)

        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=self.config.MODELO_EMBEDDINGS)
            self.vector_db = Chroma(persist_directory=self.config.CARPETA_DB, embedding_function=self.embeddings)
            self.llm = ChatOpenAI(model=self.config.MODELO_LLM, temperature=self.config.TEMPERATURA_LLM)
        except Exception as e:
            print(f"❌ FALLO CRÍTICO DE CONEXIÓN: {e}")
            sys.exit(1)
            
        self.archivos_procesados = set()
        self.arbol_conocimiento = PipelineETL(self.vector_db, self.archivos_procesados).ejecutar_sincronizacion()
        todas_cats = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
        self.router = SupervisorEnrutamiento(self.llm, todas_cats)

    def procesar_consulta(self, consulta: str, contexto_previo: str, rol_usuario: str) -> str:
        clean = consulta.lower().strip()
        
        # --- 1. FILTRO DE SALUDOS ---
        saludos = ["hola", "hola como estas", "hola cómo estás", "buenos dias", "buenas tardes", "que tal", "saludos"]
        if clean in saludos or clean.startswith("hola "):
            return f"¡Hola {rol_usuario}! ¿En qué te puedo ayudar hoy con tus flujos y procesos?"

        # --- 2. FILTRO DE CIERRE Y LIBERACIÓN DE MEMORIA ---
        frases_cierre = ["gracias", "caso cerrado", "ya quedo", "listo", "fin", "muchas gracias"]
        if any(f in clean for f in frases_cierre):
            return "🤖 **SISTEMA:** Caso cerrado formalmente. Memoria de contexto liberada. Estoy listo para procesar un nuevo caso, ¿en qué te puedo ayudar?"

        # --- 3. COMANDOS DE ADMINISTRADOR ---
        if rol_usuario == "Administrador":
            if clean == "diagnostico":
                try:
                    datos = self.vector_db.get()
                    total_frags = len(datos['ids']) if datos and 'ids' in datos else 0
                    archivos = list(self.archivos_procesados)
                    return f"🛠️ **REPORTE TÉCNICO COMPARTIDO:**\n- Archivos PDF procesados: {len(archivos)}\n- Fragmentos extraídos: **{total_frags}**\n- Estructura: {list(self.arbol_conocimiento.keys())}"
                except Exception as e:
                    return f"❌ Error en diagnóstico: {e}"

            if clean == "formatear sistema":
                try:
                    # 🚨 BORRADO LÓGICO SEGURO (Evita el bloqueo de Streamlit Cloud)
                    try:
                        self.vector_db.delete_collection()
                    except:
                        pass
                    
                    # Se re-instancia la base de datos limpia
                    self.vector_db = Chroma(persist_directory=self.config.CARPETA_DB, embedding_function=self.embeddings)
                    self.archivos_procesados = set()
                    self.arbol_conocimiento = {}
                    self.router.categorias = set()
                    
                    return "⚠️ **SISTEMA:** Base de datos compartida purgada con éxito de forma segura. Escribe 'actualizar base' para volver a cargar."
                except Exception as e:
                    return f"❌ Error crítico al limpiar la base de datos: {e}"

            comandos_actualizar = ["actualizar base", "cargar manuales", "actualizar manuales"]
            if any(c in clean for c in comandos_actualizar):
                etl = PipelineETL(self.vector_db, self.archivos_procesados)
                self.arbol_conocimiento = etl.ejecutar_sincronizacion()
                todas_cats = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
                self.router.categorias = todas_cats
                return "🤖 **SISTEMA:** ¡Sincronización completada! Ahora TODOS los usuarios pueden ver esta información."
        elif clean in ["diagnostico", "formatear sistema", "actualizar base"]:
            return "🚫 **ACCESO DENEGADO:** Este comando es exclusivo para Administradores."

        # --- FASE 1: ENRUTAMIENTO DOBLE ---
        filtros = {}
        modulo_detectado = None
        etiqueta_contexto = "toda la documentación corporativa"

        for mod in self.arbol_conocimiento.keys():
            mod_limpio = mod.lower().replace("manual", "").strip()
            if mod_limpio and (mod_limpio in clean or mod.lower() in clean):
                modulo_detectado = mod
                break

        if modulo_detectado:
            filtros["modulo"] = modulo_detectado
            etiqueta_contexto = f"el Módulo: {modulo_detectado}"
        else:
            cat_detectada = self.router.determinar_dominio(consulta)
            if cat_detectada:
                filtros["categoria"] = cat_detectada
                etiqueta_contexto = f"la subcarpeta: {cat_detectada}"

        # --- FASE 2: BÚSQUEDA RAG (MÁS FLEXIBLE / FALLBACK) ---
        docs = []
        if filtros:
            # Intento 1: Buscar estrictamente en la carpeta que mencionó el usuario
            docs = self.vector_db.similarity_search(consulta, k=20, filter=filtros)
            
        docs_validos = [d.page_content for d in docs if d and d.page_content]

        # 🚨 LÓGICA DE RESPALDO (FALLBACK STRATEGY)
        if not docs_validos:
            # Intento 2: Si la búsqueda estricta falla (o no hubo filtros), buscamos en TODOS los documentos
            docs = self.vector_db.similarity_search(consulta, k=20)
            docs_validos = [d.page_content for d in docs if d and d.page_content]
            if docs_validos:
                etiqueta_contexto = "toda la base de datos (ampliando la búsqueda para encontrar coincidencias)"
        
        if not docs_validos:
            return f"🤖 **SISTEMA:** Busqué en {etiqueta_contexto}, pero no encontré registros legibles. *(Verifica si los PDF son imágenes escaneadas que requieran OCR)*."

        contexto_aislado = "\n\n".join(docs_validos)

        prompt_final = f"""Eres un Consultor y Analista de Procesos Senior. 
Tu misión es conversar fluidamente con el usuario y proveer recomendaciones técnicas.

REGLAS:
1. Extrae los pasos usando el contexto de '{etiqueta_contexto}' provisto abajo.
2. Si los fragmentos no contienen información útil para el escenario, responde exactamente: "Compañero, revisando {etiqueta_contexto}, no encontré información documentada que nos sirva para este escenario específico."
3. Responde de forma profesional en ESPAÑOL.

HISTORIAL PREVIO DE ESTA SESIÓN:
{contexto_previo}

DOCUMENTACIÓN EXTRAÍDA ({etiqueta_contexto}):
{contexto_aislado}

CONSULTA DEL USUARIO: {consulta}"""

        res = ""
        try:
            for chunk in self.llm.stream(prompt_final):
                res += chunk.content
            return res
        except Exception as e:
            return f"❌ ERROR TÉCNICO API: {e}"
