"""
CORUS INTRANET ENGINE v2.0
Sistema RAG Robusto para Intranet Empresarial
Autor: DevOps Team
Versión: 2.0.0
"""

import os
import sys
import json
import re
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# =====================================================================
# IMPORTACIONES PRINCIPALES
# =====================================================================

import streamlit as st
from dotenv import load_dotenv

# PDF
from pypdf import PdfReader

# LLM & Embeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Vector DB
import chromadb
from chromadb.config import Settings

# =====================================================================
# CONFIGURACIÓN GLOBAL
# =====================================================================

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
DB_DIR = DATA_DIR / "db"
CACHE_DIR = DATA_DIR / "cache"
SESSIONS_DIR = DATA_DIR / "sessions"
LOGS_DIR = PROJECT_ROOT / "logs"

# Crear directorios
for dir_path in [PDF_DIR, DB_DIR, CACHE_DIR, SESSIONS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# =====================================================================
# CONFIGURACIÓN DE LOGGING
# =====================================================================

def setup_logger(name: str) -> logging.Logger:
    """Configura logger con rotación"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # File handler con rotación
    log_file = LOGS_DIR / f"{name}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger("corus_engine")

# =====================================================================
# CLASE: VECTOR STORE MANAGER
# =====================================================================

class VectorStoreManager:
    """Gestor robusto de ChromaDB con persistencia y validación"""
    
    def __init__(self):
        self.db_path = str(DB_DIR)
        self.metadata_file = DB_DIR / "metadata.json"
        self.collection_name = "corus_documents"
        
        # Configurar ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
        )
        
        self.collection = self._get_or_create_collection()
        self.metadata = self._load_metadata()
        
        logger.info(f"✅ VectorStore inicializado en {self.db_path}")
    
    def _get_or_create_collection(self):
        """Obtiene o crea colección de forma segura"""
        try:
            collection = self.client.get_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"📦 Colección recuperada")
        except:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                get_or_create=True
            )
            logger.info(f"📦 Nueva colección creada")
        
        return collection
    
    def _load_metadata(self) -> Dict:
        """Carga metadatos de versiones"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"documents": {}, "vectors": 0}
    
    def _save_metadata(self):
        """Persiste metadatos"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error guardando metadatos: {e}")
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Calcula hash de archivo"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error calculando hash: {e}")
            return ""
    
    def add_documents(self, documents: List[Dict], file_path: str) -> bool:
        """Añade documentos con validación de duplicados"""
        try:
            file_hash = self._compute_file_hash(file_path)
            file_name = Path(file_path).name
            
            # Detectar cambios
            if file_name in self.metadata["documents"]:
                if self.metadata["documents"][file_name] == file_hash:
                    logger.info(f"⏭️  {file_name} sin cambios, omitido")
                    return True
                else:
                    logger.info(f"🔄 {file_name} modificado, actualizando...")
                    self._delete_documents_by_source(file_name)
            
            # Validar documentos
            valid_docs = [
                d for d in documents 
                if d.get("content") and len(d.get("content", "").strip()) > 10
            ]
            
            if not valid_docs:
                logger.warning(f"⚠️  No hay documentos válidos en {file_name}")
                return False
            
            # Insertar
            ids = [d["id"] for d in valid_docs]
            contents = [d["content"] for d in valid_docs]
            metadatas = [d.get("metadata", {}) for d in valid_docs]
            
            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )
            
            # Actualizar metadatos
            self.metadata["documents"][file_name] = file_hash
            self.metadata["vectors"] = self.collection.count()
            self._save_metadata()
            
            logger.info(f"✅ {len(valid_docs)} fragmentos de {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error añadiendo documentos: {e}")
            return False
    
    def search(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """Búsqueda similarity"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                where=filter_dict if filter_dict else None
            )
            
            if not results or not results["documents"] or not results["documents"][0]:
                return []
            
            documents = results["documents"][0]
            distances = results["distances"][0] if results["distances"] else [0] * len(documents)
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
            ids = results["ids"][0] if results["ids"] else [f"doc_{i}" for i in range(len(documents))]
            
            return [
                {
                    "id": id_,
                    "content": doc,
                    "metadata": meta,
                    "distance": float(dist)
                }
                for id_, doc, meta, dist in zip(ids, documents, metadatas, distances)
            ]
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            return []
    
    def _delete_documents_by_source(self, source: str):
        """Elimina documentos de una fuente"""
        try:
            results = self.collection.get(
                where={"source": source}
            )
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"🗑️  {len(results['ids'])} docs eliminados")
        except Exception as e:
            logger.warning(f"⚠️  Error limpiando docs: {e}")
    
    def reset_database(self) -> bool:
        """Hard reset de la base de datos"""
        try:
            self.client.reset()
            self.metadata = {"documents": {}, "vectors": 0}
            self._save_metadata()
            self.collection = self._get_or_create_collection()
            logger.warning("⚠️  Base de datos reseteada")
            return True
        except Exception as e:
            logger.error(f"❌ Error reseteando BD: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas"""
        return {
            "total_vectors": self.collection.count(),
            "total_documents": len(self.metadata["documents"]),
            "documents": self.metadata["documents"]
        }

# =====================================================================
# CLASE: ETL PIPELINE
# =====================================================================

class ETLPipeline:
    """Pipeline ETL robusto"""
    
    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " ", ""],
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
    
    def _clean_text(self, text: str) -> str:
        """Limpia texto extraído de PDF"""
        if not text:
            return ""
        
        # Eliminar caracteres de control
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        
        # Eliminar líneas muy cortas
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 3]
        text = ' '.join(lines)
        
        return text.strip()
    
    def process_pdf(self, pdf_path: str) -> bool:
        """Procesa un PDF individual"""
        try:
            logger.info(f"📄 Procesando: {pdf_path}")
            
            reader = PdfReader(pdf_path)
            documents = []
            
            if not reader.pages:
                logger.warning(f"⚠️  {pdf_path} sin páginas")
                return False
            
            file_name = Path(pdf_path).name
            
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text() or ""
                    text = self._clean_text(text)
                    
                    if not text or len(text) < 10:
                        continue
                    
                    # Chunking
                    chunks = self.text_splitter.split_text(text)
                    
                    for chunk_num, chunk in enumerate(chunks, 1):
                        if not chunk.strip():
                            continue
                        
                        doc_id = f"{file_name}_{page_num}_{chunk_num}"
                        
                        documents.append({
                            "id": doc_id,
                            "content": chunk,
                            "metadata": {
                                "source": file_name,
                                "page": page_num,
                                "chunk": chunk_num,
                                "file_path": str(pdf_path)
                            }
                        })
                    
                except Exception as e:
                    logger.error(f"  ❌ Error página {page_num}: {e}")
                    continue
            
            if not documents:
                logger.warning(f"⚠️  No se extrajeron documentos")
                return False
            
            # Guardar
            success = self.vector_store.add_documents(documents, pdf_path)
            
            if success:
                logger.info(f"✅ {len(documents)} fragmentos indexados")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error crítico: {e}")
            return False
    
    def sync_all_pdfs(self) -> Dict:
        """Sincroniza todos los PDFs"""
        logger.info("🔄 Iniciando sincronización...")
        
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "files": []
        }
        
        if not PDF_DIR.exists():
            logger.warning(f"📁 Directorio no existe")
            return stats
        
        pdf_files = list(PDF_DIR.glob("**/*.pdf"))
        
        if not pdf_files:
            logger.info("📁 No hay PDFs")
            return stats
        
        logger.info(f"📁 Encontrados {len(pdf_files)} PDFs")
        
        for pdf_path in pdf_files:
            stats["total"] += 1
            
            if self.process_pdf(str(pdf_path)):
                stats["success"] += 1
                stats["files"].append(str(pdf_path))
            else:
                stats["failed"] += 1
        
        logger.info(f"✅ Completado: {stats['success']}/{stats['total']} exitosas")
        
        return stats

# =====================================================================
# CLASE: ADVANCED RETRIEVER
# =====================================================================

class AdvancedRetriever:
    """Retriever con validación y reranking"""
    
    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store
    
    def _calculate_relevance_score(self, doc: Dict, query: str) -> float:
        """Calcula score de relevancia"""
        score = 1.0 - doc["distance"]
        
        # Boost por coincidencia de palabras
        query_words = set(query.lower().split())
        content_words = set(doc["content"].lower().split())
        word_overlap = len(query_words & content_words) / len(query_words) if query_words else 0
        
        score += word_overlap * 0.3
        
        return min(score, 2.0)
    
    def retrieve(
        self,
        query: str,
        k: int = 5,
        module_filter: Optional[str] = None,
        min_score: float = 0.3
    ) -> List[Dict]:
        """Recupera documentos relevantes"""
        logger.info(f"🔍 Buscando: '{query[:50]}...'")
        
        # Filtro opcional
        filter_dict = None
        if module_filter:
            filter_dict = {"module": module_filter}
        
        # Búsqueda
        raw_results = self.vector_store.search(query, k=k*2, filter_dict=filter_dict)
        
        if not raw_results:
            logger.warning(f"⚠️  Sin resultados")
            return []
        
        # Reranking
        ranked = [
            {
                **doc,
                "relevance_score": self._calculate_relevance_score(doc, query)
            }
            for doc in raw_results
        ]
        
        # Filtrar por score
        ranked = [d for d in ranked if d["relevance_score"] >= min_score]
        
        # Ordenar
        ranked = sorted(ranked, key=lambda x: x["relevance_score"], reverse=True)[:3]
        
        logger.info(f"✅ {len(ranked)} documentos recuperados")
        
        return ranked

# =====================================================================
# CLASE: RAG GENERATOR
# =====================================================================

class RAGGenerator:
    """Generador RAG con validación"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("⚠️ OPENAI_API_KEY no configurada")
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            timeout=30,
            api_key=api_key
        )
    
    def _build_system_prompt(self) -> str:
        """Construye prompt del sistema"""
        return """Eres un Asesor Senior de Procesos en Corus.

CRITERIOS ESTRICTOS:
1. Responde SOLO basándote en la documentación proporcionada
2. Si no encuentras información: "No encontré información específica sobre esto en la documentación"
3. Usa formato markdown con listas y negritas
4. Sé conciso pero completo
5. Proporciona pasos numerados para procedimientos"""
    
    def generate(
        self,
        query: str,
        retrieved_docs: list,
        session_context: str,
        user_id: str = "anónimo"
    ) -> str:
        """Genera respuesta con RAG"""
        try:
            # Contexto de documentos
            doc_context = "\n\n".join([
                f"[Fuente: {doc['metadata'].get('source', 'Unknown')} - "
                f"Página {doc['metadata'].get('page', '?')}]\n{doc['content']}"
                for doc in retrieved_docs
            ])
            
            if not doc_context.strip():
                return "❌ No encontré documentación relevante. Reformula tu pregunta."
            
            # Prompt
            prompt = f"""{self._build_system_prompt()}

CONTEXTO PREVIO:
{session_context}

DOCUMENTACIÓN:
{doc_context}

PREGUNTA: {query}

RESPUESTA:"""
            
            logger.info(f"🤖 Generando respuesta...")
            
            # Streaming
            response = ""
            for chunk in self.llm.stream(prompt):
                response += chunk.content
            
            if not response.strip():
                return "❌ Generación fallida. Intenta reformular."
            
            logger.info(f"✅ Respuesta generada ({len(response)} chars)")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error en generación: {e}")
            return f"❌ Error: {str(e)[:100]}"

# =====================================================================
# CLASE: SESSION MANAGER
# =====================================================================

class SessionManager:
    """Gestiona sesiones persistentes"""
    
    def __init__(self):
        self.sessions_dir = SESSIONS_DIR
        self.sessions_dir.mkdir(exist_ok=True)
    
    def _get_session_file(self, user_id: str) -> Path:
        """Ruta del archivo de sesión"""
        return self.sessions_dir / f"{user_id}.json"
    
    def create_session(self, user_id: str, role: str) -> Dict:
        """Crea una nueva sesión"""
        session = {
            "user_id": user_id,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "context_history": [],
            "query_count": 0
        }
        
        self.save_session(user_id, session)
        logger.info(f"✅ Sesión creada para {user_id}")
        
        return session
    
    def get_session(self, user_id: str) -> Optional[Dict]:
        """Recupera sesión de usuario"""
        session_file = self._get_session_file(user_id)
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session = json.load(f)
            
            # Verificar timeout (1 hora)
            last_activity = datetime.fromisoformat(session["last_activity"])
            if datetime.now() - last_activity > timedelta(seconds=3600):
                logger.info(f"⏰ Sesión de {user_id} expirada")
                self.delete_session(user_id)
                return None
            
            return session
        except Exception as e:
            logger.error(f"❌ Error recuperando sesión: {e}")
            return None
    
    def save_session(self, user_id: str, session: Dict):
        """Guarda sesión"""
        try:
            session["last_activity"] = datetime.now().isoformat()
            
            with open(self._get_session_file(user_id), 'w') as f:
                json.dump(session, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error guardando sesión: {e}")
    
    def add_to_context(self, user_id: str, query: str, response: str):
        """Añade interacción al contexto"""
        session = self.get_session(user_id)
        if session:
            session["context_history"].append({
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "response": response[:500]
            })
            
            # Mantener últimas 10
            session["context_history"] = session["context_history"][-10:]
            session["query_count"] += 1
            
            self.save_session(user_id, session)
    
    def delete_session(self, user_id: str):
        """Elimina sesión"""
        try:
            self._get_session_file(user_id).unlink(missing_ok=True)
            logger.info(f"🗑️  Sesión de {user_id} eliminada")
        except Exception as e:
            logger.error(f"❌ Error eliminando sesión: {e}")
    
    def get_context_string(self, user_id: str) -> str:
        """Retorna contexto como string"""
        session = self.get_session(user_id)
        if not session or not session["context_history"]:
            return "Sin historial previo."
        
        context = "HISTORIAL:\n"
        for interaction in session["context_history"][-5:]:
            context += f"\nQ: {interaction['query']}\nA: {interaction['response']}\n"
        
        return context

# =====================================================================
# CONFIGURACIÓN STREAMLIT
# =====================================================================

st.set_page_config(
    page_title="Corus Intranet Engine",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# INICIALIZACIÓN CON CACHE
# =====================================================================

@st.cache_resource
def init_vector_store():
    """Inicializa VectorStore una sola vez"""
    return VectorStoreManager()

@st.cache_resource
def init_etl_pipeline():
    """Inicializa ETL"""
    vector_store = init_vector_store()
    return ETLPipeline(vector_store)

@st.cache_resource
def init_retriever():
    """Inicializa Retriever"""
    vector_store = init_vector_store()
    return AdvancedRetriever(vector_store)

@st.cache_resource
def init_generator():
    """Inicializa Generator"""
    try:
        return RAGGenerator()
    except ValueError as e:
        logger.error(str(e))
        return None

@st.cache_resource
def init_session_manager():
    """Inicializa SessionManager"""
    return SessionManager()

# =====================================================================
# APLICACIÓN PRINCIPAL
# =====================================================================

def main():
    """Función principal"""
    
    # Sidebar - Autenticación
    st.sidebar.title("🔐 Autenticación")
    user_name = st.sidebar.text_input("Nombre de usuario", value="Usuario")
    role = st.sidebar.selectbox("Rol", ["Usuario", "Administrador"])
    
    # Validar API Key
    if not os.getenv("OPENAI_API_KEY"):
        st.error("❌ OPENAI_API_KEY no configurada. Verifica tu .env")
        return
    
    # Inicializar componentes
    vector_store = init_vector_store()
    etl = init_etl_pipeline()
    retriever = init_retriever()
    generator = init_generator()
    session_mgr = init_session_manager()
    
    if generator is None:
        st.error("❌ Error inicializando Generator. Verifica OPENAI_API_KEY")
        return
    
    # Crear/recuperar sesión
    if "session" not in st.session_state:
        user_id = f"{user_name}_{role}".replace(" ", "_")
        session = session_mgr.get_session(user_id)
        
        if session is None:
            session = session_mgr.create_session(user_id, role)
        
        st.session_state.session = session
        st.session_state.user_id = user_id
    
    # =====================================================================
    # HEADER Y ESTADÍSTICAS
    # =====================================================================
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🤖 Corus Intranet Engine v2.0")
        st.markdown(f"**{user_name}** | `{role}`")
    
    with col2:
        stats = vector_store.get_stats()
        st.metric("📦 Vectores", stats["total_vectors"])
    
    with col3:
        st.metric("📄 Documentos", stats["total_documents"])
    
    # =====================================================================
    # PANEL ADMINISTRADOR
    # =====================================================================
    
    if role == "Administrador":
        with st.sidebar:
            st.divider()
            st.subheader("⚙️ Admin Panel")
            
            col_sync, col_reset = st.columns(2)
            
            with col_sync:
                if st.button("🔄 Sincronizar PDFs", use_container_width=True):
                    with st.spinner("Sincronizando..."):
                        sync_stats = etl.sync_all_pdfs()
                        st.success(f"✅ {sync_stats['success']}/{sync_stats['total']} completados")
            
            with col_reset:
                if st.button("🗑️ Reset BD", use_container_width=True):
                    if st.confirm("¿Confirmar reset?"):
                        vector_store.reset_database()
                        st.cache_resource.clear()
                        st.success("✅ BD reseteada")
                        st.rerun()
            
            with st.expander("📊 Diagnóstico"):
                st.json(stats)
                st.info(f"📁 PDFs: {list(PDF_DIR.glob('**/*.pdf'))}")
    
    # =====================================================================
    # CHAT INTERFACE
    # =====================================================================
    
    st.divider()
    st.subheader("💬 Consulta Base de Conocimiento")
    
    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Mostrar mensajes
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input de usuario
    user_query = st.chat_input("¿Qué necesitas saber?")
    
    if user_query:
        # Añadir a histórico
        st.session_state.messages.append({"role": "user", "content": user_query})
        
        with st.chat_message("user"):
            st.markdown(user_query)
        
        # Procesar consulta
        with st.chat_message("assistant"):
            with st.spinner("🔍 Buscando información..."):
                try:
                    # Retrieval
                    docs = retriever.retrieve(user_query)
                    
                    if not docs:
                        response = "❌ No encontré documentación relevante. Intenta reformular tu pregunta."
                    else:
                        # Contexto de sesión
                        session_context = session_mgr.get_context_string(st.session_state.user_id)
                        
                        # Generation
                        response = generator.generate(
                            query=user_query,
                            retrieved_docs=docs,
                            session_context=session_context,
                            user_id=st.session_state.user_id
                        )
                        
                        # Guardar en sesión
                        session_mgr.add_to_context(st.session_state.user_id, user_query, response)
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    logger.error(f"Error procesando query: {e}", exc_info=True)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 12px; padding: 20px;'>
    🔐 Corus Intranet Engine v2.0 | © 2024 | Production Ready
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
