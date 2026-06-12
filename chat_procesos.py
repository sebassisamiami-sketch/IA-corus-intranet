import os
import sys

# --- PARCHES DE INFRAESTRUCTURA PARA STREAMLIT CLOUD ---
os.environ["ANONYMIZED_TELEMETRY"] = "False"
if "HOME" not in os.environ:
    os.environ["HOME"] = "/tmp"

try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
# -------------------------------------------------------

import warnings
import glob
import re
from typing import List, Optional, Set, Dict
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class SistemaConfig:
    CARPETA_DB: str = "./chroma_db"
    ARCHIVO_REGISTRO: str = "archivos_indexados.txt"
    MODELO_EMBEDDINGS: str = "sentence-transformers/all-MiniLM-L6-v2"
    MODELO_LLM: str = "gpt-4o-mini"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200
    TEMPERATURA_LLM: float = 0.0  

class PipelineETL:
    def __init__(self, vector_db: Chroma):
        self.vector_db = vector_db
        self.config = SistemaConfig()

    def _limpiar_texto_pdf(self, texto: str) -> str:
        if texto is None: return ""
        texto = str(texto).replace('\x00', '')
        texto = re.sub(r'(?<!\n)\n(?!\n)', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

    def ejecutar_sincronizacion(self) -> Dict[str, Set[str]]:
        db_vacia = True
        try:
            datos_db = self.vector_db.get()
            if datos_db and datos_db.get('ids') and len(datos_db['ids']) > 0: 
                db_vacia = False
        except Exception: 
            pass

        if os.path.exists(self.config.ARCHIVO_REGISTRO) and db_vacia:
            os.remove(self.config.ARCHIVO_REGISTRO)
            
        archivos_pdf = glob.glob("**/*.pdf", recursive=True)
        procesados = set(open(self.config.ARCHIVO_REGISTRO, "r", encoding="utf-8").read().splitlines()) if os.path.exists(self.config.ARCHIVO_REGISTRO) else set()
        nuevos = [a for a in archivos_pdf if a not in procesados]
        
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
                for i, pag in enumerate(reader.pages):
                    txt = self._limpiar_texto_pdf(pag.extract_text())
                    
                    # 🔒 FILTRO ESTRICTO: Solo si hay texto real, lo procesamos
                    if txt and len(txt) > 5:
                        frags = text_splitter.split_text(txt)
                        # Segunda validación: quitamos fragmentos vacíos o nulos
                        frags_limpios = [f for f in frags if f and str(f).strip()]
                        
                        if frags_limpios:
                            enriquecidos = [f"[MÓDULO: {mod} | CARPETA: {cat} | PAG: {i+1}]\n{f}" for f in frags_limpios]
                            meta = [{"modulo": mod, "categoria": cat, "fuente": os.path.basename(archivo), "pagina": i+1}] * len(frags_limpios)
                            self.vector_db.add_texts(enriquecidos, meta)
                            
                with open(self.config.ARCHIVO_REGISTRO, "a", encoding="utf-8") as f: 
                    f.write(archivo + "\n")
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
        
        if not os.path.exists(self.config.CARPETA_DB):
            os.makedirs(self.config.CARPETA_DB, exist_ok=True)

        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=self.config.MODELO_EMBEDDINGS)
            self.vector_db = Chroma(persist_directory=self.config.CARPETA_DB, embedding_function=self.embeddings)
            self.llm = ChatOpenAI(model=self.config.MODELO_LLM, temperature=self.config.TEMPERATURA_LLM)
        except Exception as e:
            print(f"❌ FALLO CRÍTICO DE CONEXIÓN: {e}")
            sys.exit(1)
            
        self.arbol_conocimiento = PipelineETL(self.vector_db).ejecutar_sincronizacion()
        todas_cats = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
        self.router = SupervisorEnrutamiento(self.llm, todas_cats)
        self.historial, self.cat_actual = [], None

    def procesar_consulta(self, consulta: str) -> str:
        clean = consulta.lower().strip()
        
        # 0. Comando Maestro de Reestructuración (Formateo Profundo)
        if clean == "formatear sistema":
            try:
                # Destruye la base de datos vieja
                self.vector_db.delete_collection()
                # La reconstruye desde cero inmediatamente para evitar errores de conexión
                self.vector_db = Chroma(persist_directory=self.config.CARPETA_DB, embedding_function=self.embeddings)
                if os.path.exists(self.config.ARCHIVO_REGISTRO): 
                    os.remove(self.config.ARCHIVO_REGISTRO)
                self.arbol_conocimiento = {}
                self.router.categorias = set()
                return "⚠️ **SISTEMA:** Base de datos destruida y purgada. Por favor, escribe 'actualizar base' para reindexar limpiamente."
            except Exception as e:
                return f"❌ Error al formatear la base de datos: {e}"

        saludos = ["hola", "hola como estas", "hola cómo estás", "buenos dias", "buenas tardes", "que tal", "saludos"]
        if clean in saludos or clean.startswith("hola "):
            return "Hola funcionario, ¿en qué te puedo ayudar?"

        comandos_actualizar = ["actualizar base", "cargar manuales", "actualizar manuales", "cargar nuevos archivos"]
        if any(c in clean for c in comandos_actualizar):
            print("\n🔄 [SISTEMA] Escaneando directorios y metadatos...")
            etl = PipelineETL(self.vector_db)
            self.arbol_conocimiento = etl.ejecutar_sincronizacion()
            todas_cats = {cat for cats in self.arbol_conocimiento.values() for cat in cats}
            self.router.categorias = todas_cats
            return "🤖 **SISTEMA:** ¡Sincronización completada! Los archivos fueron procesados y purgados de errores."

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

        # Filtro de seguridad post-extracción para ignorar "Nones" si Chroma llega a fallar
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
