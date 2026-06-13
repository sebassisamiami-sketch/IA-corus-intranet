import os
import sys
import warnings
import glob
import re
from typing import List, Optional, Set, Dict
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI

# --- PARCHES DE INFRAESTRUCTURA PARA STREAMLIT CLOUD ---
os.environ["ANONYMIZED_TELEMETRY"] = "False"
if "HOME" not in os.environ:
    os.environ["HOME"] = "/tmp"

try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# -------------------------------------------------------

class SistemaConfig:
    """Configuración centralizada 100% en RAM (Sin escritura en disco)."""
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

        # 1. Mapear la estructura actual del disco
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
        
        # 2. Ingesta directa a la memoria RAM
        for archivo in nuevos:
            partes = os.path.normpath(archivo).split(os.sep)
            mod = partes[0] if len(partes) >= 2 else "General"
            cat = partes[-2] if len(partes) >= 2 else "Raíz"
            
            try:
                reader = PdfReader(archivo)
                for i, pag in enumerate(reader.pages):
                    txt = self._limpiar_texto_pdf(pag.extract_text())
                    
                    # 🔒 FILTRO ESTRICTO: Previene el error de Pydantic NoneType
                    if txt and len(txt) > 5:
                        frags = text_splitter.split_text(txt)
                        frags_limpios = [f for f in frags if f and isinstance(f, str) and str(f).strip()]
                        
                        if frags_limpios:
                            enriquecidos = [f"[MÓDULO: {mod} | CARPETA: {cat} | PAG: {i+1}]\n{f}" for f in frags_limpios]
                            meta = [{"modulo": mod, "categoria": cat, "fuente": os.path.basename(archivo), "pagina": i+1}] * len(frags_limpios)
                            self.vector_db.add_texts(enriquecidos, meta)
                            
                # Registramos en la RAM que ya leímos este archivo
                self.archivos_procesados.add(archivo)
            except Exception as e: 
                print(f"❌ Error en la ingesta de {archivo}: {e}")
                
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
                print("⚠️ Alerta: No se encontró la OPENAI_API_KEY en los Secrets.")
        
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=self.config.MODELO_EMBEDDINGS)
            # INICIALIZACIÓN EFÍMERA: Sin 'persist_directory'. Vive 100% en RAM.
            self.vector_db = Chroma(embedding_function=self.embeddings)
            self.llm = ChatOpenAI(model=self.config.MODELO_LLM, temperature=self.config.TEMPERATURA_LLM)
        except Exception as e:
            print(f"❌ FALLO CRÍTICO DE CONEXIÓN: {e}")
            sys.exit(1)
            
        self.archivos_procesados = set()
        self.arbol_conocimiento = PipelineETL(self.vector_db, self.archivos_procesados).ejecutar_sincronizacion()
        todas_cats = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
        self.router = SupervisorEnrutamiento(self.llm, todas_cats)
        self.historial, self.cat_actual = [], None

    def procesar_consulta(self, consulta: str) -> str:
        clean = consulta.lower().strip()
        
        # 0. Comando Maestro de Reestructuración (Formateo Profundo en RAM)
        if clean == "formatear sistema":
            try:
                self.vector_db = Chroma(embedding_function=self.embeddings)
                self.archivos_procesados = set()
                self.arbol_conocimiento = {}
                self.router.categorias = set()
                return "⚠️ **SISTEMA:** Memoria RAM purgada. Escribe 'actualizar base' para volver a cargar los manuales."
            except Exception as e:
                return f"❌ Error al limpiar la memoria: {e}"

        saludos = ["hola", "hola como estas", "hola cómo estás", "buenos dias", "buenas tardes", "que tal", "saludos"]
        if clean in saludos or clean.startswith("hola "):
            return "Hola funcionario, ¿en qué te puedo ayudar?"

        comandos_actualizar = ["actualizar base", "cargar manuales", "actualizar manuales", "cargar nuevos archivos"]
        if any(c in clean for c in comandos_actualizar):
            print("\n🔄 [SISTEMA] Escaneando directorios en memoria...")
            etl = PipelineETL(self.vector_db, self.archivos_procesados)
            self.arbol_conocimiento = etl.ejecutar_sincronizacion()
            todas_cats = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
            self.router.categorias = todas_cats
            return "🤖 **SISTEMA:** ¡Sincronización completada en RAM! Los archivos fueron procesados sin errores de disco."

        frases_cierre = ["caso solucionado", "caso cerrado", "ya quedo", "gracias", "listo", "fin"]
        if any(f in clean for f in frases_cierre):
            self.historial, self.cat_actual = [], None
            return "🤖 **SISTEMA:** Caso cerrado formalmente. Estoy listo para procesar un nuevo caso."

        # --- FASE 1: ENRUTAMIENTO INTELIGENTE DOBLE ---
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

        # --- FASE 2: BÚSQUEDA SEMÁNTICA RAG ---
        if filtros:
            docs = self.vector_db.similarity_search(consulta, k=20, filter=filtros)
        else:
            docs = self.vector_db.similarity_search(consulta, k=20)

        docs_validos = [d.page_content for d in docs if d and d.page_content]
        contexto_aislado = "\n\n".join(docs_validos)
        contexto_previo = "\n".join(self.historial[-4:]) if self.historial else "Inicio de la conversación."

        prompt_final = f"""Eres un Consultor y Analista de Procesos Senior. 
Tu misión es conversar fluidamente con el usuario y proveer recomendaciones técnicas estructuradas basadas estrictamente en los documentos corporativos.

REGLAS DE ANÁLISIS:
1. Base de Conocimiento: Extrae los pasos usando el contexto de '{etiqueta_contexto}' provisto abajo.
2. Activación del Candado: Si los fragmentos no contienen información útil para el escenario, responde exactamente: "Compañero, revisando {etiqueta_contexto}, no encontré información documentada que nos sirva para este escenario específico."
3. Tono: Responde de forma estructurada, limpia y profesional en ESPAÑOL.

HISTORIAL PREVIO:
{contexto_previo}

DOCUMENTACIÓN EXTRAÍDA ({etiqueta_contexto}):
{contexto_aislado}

CONSULTA DEL ANALISTA: {consulta}"""

        res = ""
        try:
            for chunk in self.llm.stream(prompt_final):
                res += chunk.content
            
            self.historial.extend([f"Q: {consulta}", f"A: {res}"])
            return res
        except Exception as e:
            return f"❌ ERROR TÉCNICO EN EL LLAMADO DE LA API CLOUD: {e}"

if __name__ == "__main__":
    intranet_kms = CorusIntranetEngine()
    while True:
        try:
            consulta = input("\n👉 Analista: ")
            if consulta.lower().strip() in ['exit', 'salir', 'quit']: break
            if not consulta.strip(): continue
            salida = intranet_kms.procesar_consulta(consulta)
            if salida: print(salida)
        except KeyboardInterrupt: 
            break
