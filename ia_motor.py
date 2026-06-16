# ia_motor.py - Motor Central de IA (Singleton)

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain

logger = logging.getLogger(__name__)

class CorusIntranetEngine:
    """Motor central de la Intranet Corus - Patrón Singleton"""
    
    _instance: Optional['CorusIntranetEngine'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CorusIntranetEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializar el motor IA"""
        if self._initialized:
            return
        
        self._initialized = True
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("❌ OPENAI_API_KEY no configurada en .env")
        
        # Inicializar LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=self.api_key
        )
        
        # Inicializar embeddings
        self.embeddings = OpenAIEmbeddings(api_key=self.api_key)
        
        # Inicializar vectorstore
        self.vectorstore = None
        self.chain = None
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        logger.info("✅ CorusIntranetEngine inicializado")
    
    def load_vectorstore(self, db_path: str = "data/db/chroma_db"):
        """Cargar o crear vectorstore"""
        try:
            if os.path.exists(db_path):
                self.vectorstore = Chroma(
                    persist_directory=db_path,
                    embedding_function=self.embeddings
                )
                logger.info(f"✅ Vectorstore cargado desde {db_path}")
            else:
                logger.warning(f"⚠️ Base de datos no encontrada en {db_path}")
                os.makedirs(db_path, exist_ok=True)
        except Exception as e:
            logger.error(f"❌ Error cargando vectorstore: {e}")
            raise
    
    def setup_chain(self):
        """Configurar cadena RAG"""
        try:
            if not self.vectorstore:
                self.load_vectorstore()
            
            self.chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
                memory=self.memory,
                verbose=True
            )
            logger.info("✅ Cadena RAG configurada")
        except Exception as e:
            logger.error(f"❌ Error configurando cadena: {e}")
            raise
    
    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """Realizar consulta al motor IA"""
        try:
            if not self.chain:
                self.setup_chain()
            
            response = self.chain({"question": question})
            return {
                "respuesta": response.get("answer", "No hay respuesta"),
                "sources": response.get("source_documents", []),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Error en consulta: {e}")
            return {
                "respuesta": f"Error: {str(e)}",
                "sources": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def get_memory(self) -> List[Dict[str, str]]:
        """Obtener historial de memoria"""
        return self.memory.chat_memory.messages if self.memory else []
    
    def clear_memory(self):
        """Limpiar memoria"""
        self.memory.clear()
        logger.info("✅ Memoria limpiada")
