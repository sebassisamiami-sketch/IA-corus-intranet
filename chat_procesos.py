import os
import sys

# --- PARCHES DE INFRAESTRUCTURA PARA STREAMLIT CLOUD ---
# 1. Parche de Telemetría: Evita el error "NoneType" al buscar la carpeta HOME en Linux
os.environ["ANONYMIZED_TELEMETRY"] = "False"
if "HOME" not in os.environ:
    os.environ["HOME"] = "/tmp"

# 2. Parche de SQLite: Streamlit Cloud usa una versión antigua incompatible con ChromaDB
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
# -------------------------------------------------------

import warnings
import glob
import re
from typing import List, Optional, Set
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI

# Desactivación de alertas de paralelismo para mantener la consola limpia
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class SistemaConfig:
    """Configuración centralizada de la infraestructura KMS corporativa."""
    CARPETA_DB: str = "./chroma_db"
    ARCHIVO_REGISTRO: str = "archivos_indexados.txt"
    MODELO_EMBEDDINGS: str = "sentence-transformers/all-MiniLM-L6-v2"
    MODELO_LLM: str = "gpt-4o-mini"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200
    TEMPERATURA_LLM: float = 0.0  # Determinismo absoluto para evitar alucinaciones operativas

class PipelineETL:
    """Módulo de Extracción, Transformación y Carga con sincronización en caliente."""
    def __init__(self, vector_db: Chroma):
        self.vector_db = vector_db
        self.config = SistemaConfig()

    def _limpiar_texto_pdf(self, texto: str) -> str:
        if not texto: return ""
        texto = texto.replace('\x00', '')
        texto = re.sub(r'(?<!\n)\n(?!\n)', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

    def ejecutar_sincronizacion(self) -> Set[str]:
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
        categorias = set()

        for a in archivos_pdf:
            c = os.path.basename(os.path.dirname(os.path.abspath(a)))
            if c and "chroma_db" not in a: 
                categorias.add(c)

        if not nuevos: 
            return categorias

        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " ", ""], 
            chunk_size=self.config.CHUNK_SIZE, 
            chunk_overlap=self.config.CHUNK_OVERLAP
        )
        
        for archivo in nuevos:
            cat = os.path.basename(os.path.dirname(os.path.abspath(archivo)))
            try:
                reader = PdfReader(archivo)
                for i, pag in enumerate(reader.pages):
                    txt = self._limpiar_texto_pdf(pag.extract_text())
                    if txt:
                        frags = text_splitter.split_text(txt)
                        enriquecidos = [f"[DOMINIO: {cat} | PAG: {i+1}]\n{f}" for f in frags]
                        meta = [{"categoria": cat, "fuente": os.path.basename(archivo), "pagina": i+1}] * len(frags)
                        self.vector_db.add_texts(enriquecidos, meta)
                with open(self.config.ARCHIVO_REGISTRO, "a", encoding="utf-8") as f: 
                    f.write(archivo + "\n")
            except Exception as e: 
                print(f"❌ Error en la ingesta de {archivo}: {e}")
        return categorias

class SupervisorEnrutamiento:
    """Módulo clasificador encargado de mapear consultas a subcarpetas físicas."""
    def __init__(self, llm: ChatOpenAI, categorias: Set[str]):
        self.llm = llm
        self.categorias = categorias

    def determinar_dominio(self, pregunta: str) -> Optional[str]:
        if not self.categorias: 
            return None
        prompt = f"Determina la categoría física para la consulta: '{pregunta}'. Categorías disponibles: {', '.join(self.categorias)}. Responde EXCLUSIVAMENTE con el nombre limpio de la categoría. Si no hay relación obvia, responde: DESCONOCIDO."
        
        resp = self.llm.invoke(prompt).content.strip()
        for cat in self.categorias:
            if cat.lower() in resp.lower(): 
                return cat
        return None

class CorusIntranetEngine:
    """Controlador central de orquestación y lógica RAG multi-capa."""
    def __init__(self):
        self.config = SistemaConfig()
        
        # --- CONFIGURACIÓN SEGURA DE API KEY PARA PRODUCCIÓN ---
        if "OPENAI_API_KEY" not in os.environ or os.environ["OPENAI_API_KEY"] in ["#", "sk-pega-tu-clave-aqui"]:
            try:
                import streamlit as st
                os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
            except Exception:
                print("⚠️ Alerta: No se encontró la OPENAI_API_KEY en los Secrets de la plataforma.")
        
        if not os.path.exists(self.config.CARPETA_DB):
            os.makedirs(self.config.CARPETA_DB, exist_ok=True)

        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=self.config.MODELO_EMBEDDINGS)
            self.vector_db = Chroma(persist_directory=self.config.CARPETA_DB, embedding_function=self.embeddings)
            self.llm = ChatOpenAI(model=self.config.MODELO_LLM, temperature=self.config.TEMPERATURA_LLM)
        except Exception as e:
            print(f"❌ FALLO CRÍTICO DE CONEXIÓN CON LOS SERVICIOS DE IA: {e}")
            sys.exit(1)
            
        self.categorias = PipelineETL(self.vector_db).ejecutar_sincronizacion()
        self.router = SupervisorEnrutamiento(self.llm, self.categorias)
        self.historial, self.cat_actual = [], None

    def procesar_consulta(self, consulta: str) -> str:
        clean = consulta.lower().strip()
        
        # FASE 0.1: Interceptor de Saludos Institucionales
        saludos = ["hola", "hola como estas", "hola cómo estás", "buenos dias", "buenas tardes", "que tal", "saludos"]
        if clean in saludos or clean.startswith("hola "):
            return "Hola funcionario, ¿en qué te puedo ayudar?"

        # FASE 0.15: Protocolo de Soporte Emocional y Contención Laboral
        palabras_emocionales = [
            "estres", "estrés", "estresado", "ansiedad", "cansado", "triste", 
            "me siento mal", "problema personal", "abrumado", "deprimido", "ayuda emocional", 
            "no puedo mas", "frustrado", "quemado", "agotado", "desesperado", "presion", "presión"
        ]
        if any(p in clean for p in palabras_emocionales):
            print("\n💙 [SISTEMA] Activando Línea de Apoyo al Funcionario...")
            prompt_apoyo = f"""Eres un asistente corporativo empático. El analista acaba de expresar una carga emocional o estrés: "{consulta}". 
            Da una respuesta humana, cálida y reconfortante en un máximo de 2 párrafos cortos. Valida lo que siente, recuérdale respirar profundamente y sugiere de forma profesional tomar un breve descanso, un café o acudir al equipo humano si requiere soporte adicional. No menciones aspectos técnicos, ni manuales de procesos."""
            try:
                respuesta_apoyo = self.llm.invoke(prompt_apoyo).content
                self.historial.extend([f"Q: {consulta}", f"A: [Apoyo emocional brindado]"])
                return f"💙 **LÍNEA DE APOYO CORPORATIVA:**\n\n{respuesta_apoyo}"
            except Exception as e: 
                return f"❌ ERROR DE CONEXIÓN CLOUD: {e}"

        # FASE 0.18: Protocolo contra Inyecciones y Fuga de Secretos (Guardrails)
        patrones_riesgo = [
            "ignora las instrucciones", "ignora las reglas", "cambia de rol", "system prompt",
            "dame la contraseña", "password", "ver credenciales", "hackear", "vulnerar",
            "script malicioso", "inyectar codigo", "delete de base", "drop database", "bypassear manual"
        ]
        if any(patron in clean for patron in patrones_riesgo):
            print("\n🚨 [SEGURIDAD] Intento de vulneración o inyección perimetral interceptado.")
            self.historial.extend([f"Q: {consulta}", "A: [Bloqueado por infracción de seguridad]"])
            return "🚨 **PROTOCOLO DE SEGURIDAD:**\nAcceso denegado. La consulta infringe las políticas de seguridad del sistema o contiene comandos de alteración de directivas."

        # FASE 0.2: Sincronización Incrementales en Caliente (Hot-Reload)
        comandos_actualizar = ["actualizar base", "cargar manuales", "actualizar manuales", "cargar nuevos archivos"]
        if any(c in clean for c in comandos_actualizar):
            print("\n🔄 [SISTEMA] Escaneando directorios en busca de nuevos archivos PDF...")
            etl = PipelineETL(self.vector_db)
            nuevas_categorias = etl.ejecutar_sincronizacion()
            self.categorias.update(nuevas_categorias)
            self.router.categorias = self.categorias
            return "🤖 **SISTEMA:** ¡Sincronización en caliente completada! Los nuevos manuales detectados han sido indexados con éxito."

        # FASE 0.3: Cierre de Sesión e Higienización del Buffer
        frases_cierre_compuestas = ["caso solucionado", "caso cerrado", "ya quedo", "ya quedó"]
        cierre_exacto = ["gracias", "ok", "listo", "perfecto", "fin", "excelente"]
        if (clean in cierre_exacto) or any(f in clean for f in frases_cierre_compuestas):
            self.historial, self.cat_actual = [], None
            return "🤖 **SISTEMA:** Caso cerrado formalmente y buffer de memoria RAM liberado. Estoy listo para procesar un nuevo caso."

        # --- FASE 1: ENRUTAMIENTO DINÁMICO GLOBAL ---
        cat_detectada = self.router.determinar_dominio(consulta)
        cat = cat_detectada if cat_detectada else self.cat_actual

        # Ya no bloqueamos la consulta si no hay categoría. Simplemente la registramos.
        if cat and self.cat_actual != cat:
            self.historial, self.cat_actual = [], cat
            print(f"🧹 [SISTEMA] Cambio de contexto detectado. Inicializando dominio: /{cat}")

        if cat:
            print(f"📊 [ENRUTADOR] Búsqueda enfocada en la subcarpeta: /{cat}")
            etiqueta_contexto = cat
        else:
            print("🌍 [ENRUTADOR] Categoría no especificada. Activando BÚSQUEDA GLOBAL.")
            etiqueta_contexto = "toda la documentación corporativa"

        # FASE 2: Interceptación y Extracción Relacional Directa (Bypass de Costos)
        comandos_literal = ["informacion completa", "información completa", "archivo original", "texto completo", "literal", "documento completo"]
        es_literal = any(c in clean for c in comandos_literal)
        
        if es_literal:
            # Aquí sí pedimos categoría, para no colapsar la RAM imprimiendo todos los PDFs de la empresa
            if not cat:
                return "🤖 **SISTEMA:** Para extraer un documento completo literal, necesito que me indiques de qué carpeta o manual estamos hablando."
                
            print(f"\n📦 [SISTEMA] Extrayendo compilación lineal completa desde el disco local...")
            datos_bd = self.vector_db.get(where={"categoria": cat})
            
            if not datos_bd or not datos_bd.get('documents'):
                return f"🤖 **SISTEMA:** No se encontraron registros indexados en la categoría '{cat}'."
            
            chunks_ordenados = sorted(
                zip(datos_bd['documents'], datos_bd['metadatas']),
                key=lambda x: (x[1].get('fuente', ''), x[1].get('pagina', 0))
            )
            
            texto_reconstruido = ""
            fuente_actual = ""
            
            for doc_text, metadata in chunks_ordenados:
                fuente = metadata.get('fuente', 'Manual_Procesos.pdf')
                pagina = metadata.get('pagina', '?')
                
                if fuente != fuente_actual:
                    texto_reconstruido += f"\n\n===================================================\n📖 FUENTE ORIGEN: {fuente}\n==================================================="
                    fuente_actual = fuente
                    
                texto_reconstruido += f"\n\n[Página {pagina}]\n{doc_text}"
                
            self.historial.extend([f"Q: {consulta}", "A: [Se entregó el documento original ordenado en pantalla]"])
            return f"### 📄 COMPILACIÓN LITERAL DEL ARCHIVO EN DISCO (/{cat})\n{texto_reconstruido}"

        # --- FASE 3: BÚSQUEDA SEMÁNTICA RAG (LOCAL O GLOBAL) ---
        if cat:
            # Búsqueda filtrada por carpeta
            docs = self.vector_db.similarity_search(consulta, k=20, filter={"categoria": cat})
        else:
            # Búsqueda global en toda la base de datos (sin filtro)
            docs = self.vector_db.similarity_search(consulta, k=20)

        contexto_aislado = "\n\n".join([d.page_content for d in docs])
        contexto_previo = "\n".join(self.historial[-4:]) if self.historial else "Inicio de la conversación."

        prompt_final = f"""Eres un Consultor y Analista de Procesos Senior. 
Tu misión es conversar fluidamente con el usuario, resolver sus dudas operativas del negocio y proveer recomendaciones técnicas estructuradas basadas estrictamente en los documentos corporativos.

REGLAS DE ANÁLISIS Y CONVERSACIÓN (CERO ALUCINACIONES):
1. Base de Conocimiento: Extrae los pasos, validaciones, flujos o rutas operativas que ayuden al analista usando el contexto de '{etiqueta_contexto}' provisto abajo.
2. Flexibilidad Analítica: Si la solución idéntica palabra por palabra no aparece, evalúa la información relacionada, pistas o variables dentro de los fragmentos para estructurar una recomendación útil orientada al problema. 
3. Blindaje de Entorno: Está terminantemente prohibido inventar sistemas, botones, nombres de servidores o credenciales que no se mencionen textualmente en los fragmentos.
4. Activación del Candado: Únicamente en caso de que los fragmentos de '{etiqueta_contexto}' no contengan absolutamente ninguna relación, dato o pista útil frente al escenario consultado, responderás exactamente con este texto: "Compañero, revisando {etiqueta_contexto}, no encontré información documentada que nos sirva para este escenario específico."
5. Tono: Responde como un colega experto de forma estructurada, limpia y profesional en ESPAÑOL.

HISTORIAL DE LA SESIÓN ACTUAL:
{contexto_previo}

DOCUMENTACIÓN EXTRAÍDA ({etiqueta_contexto}):
{contexto_aislado}

ANÁLISIS O CONSULTA REQUERIDA POR EL ANALISTA: {consulta}"""

        print(f"\n🤖 EXPERTO ({etiqueta_contexto}):\n" + "-"*50)
        res = ""
        try:
            for chunk in self.llm.stream(prompt_final):
                print(chunk.content, end="", flush=True)
                res += chunk.content
            print("\n" + "-" * 50)
            
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
