# ia_motor.py - Motor IA Singleton
"""
Motor IA centralizado para CorusIntranetEngine
Implementa patrón Singleton para una única instancia
"""

import logging
import os
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

class CorusIntranetEngine:
    """
    Motor IA de Corus - Singleton
    Gestiona la interacción con OpenAI y vectorstore
    """
    
    _instancia = None
    
    def __new__(cls):
        """Implementar patrón Singleton"""
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._inicializar()
        return cls._instancia
    
    def _inicializar(self):
        """Inicialización única"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("❌ OPENAI_API_KEY no configurada en .env")
        
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.memory = None
        self.chain = None
        
        logger.info("✅ CorusIntranetEngine inicializado")
    
    def load_vectorstore(self) -> bool:
        """Cargar vectorstore desde disco"""
        try:
            db_path = "data/db/chroma_db"
            
            if not os.path.exists(db_path):
                logger.warning(f"⚠️ BD no existe en {db_path}")
                return False
            
            self.embeddings = OpenAIEmbeddings(
                api_key=self.api_key,
                model="text-embedding-3-small"
            )
            
            self.vectorstore = Chroma(
                persist_directory=db_path,
                embedding_function=self.embeddings,
                collection_name="corus_documentos"
            )
            
            logger.info("✅ Vectorstore cargado")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error cargando vectorstore: {e}")
            return False
    
    def setup_chain(self) -> bool:
        """Configurar la cadena de conversación"""
        try:
            # Crear LLM
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=2048
            )
            
            # Crear memoria
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            
            # Crear cadena
            if self.vectorstore:
                self.chain = ConversationalRetrievalChain.from_llm(
                    llm=self.llm,
                    retriever=self.vectorstore.as_retriever(
                        search_kwargs={"k": 3}
                    ),
                    memory=self.memory,
                    return_source_documents=True,
                    verbose=False
                )
            else:
                logger.warning("⚠️ Vectorstore no disponible, cadena sin retriever")
                self.chain = None
            
            logger.info("✅ Chain configurada")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error configurando chain: {e}")
            return False
    
    def query(self, pregunta: str) -> Dict[str, Any]:
        """
        Ejecutar query al motor IA
        
        Args:
            pregunta: Pregunta del usuario
        
        Returns:
            Dict con respuesta y sources
        """
        try:
            if not self.chain:
                return {
                    'respuesta': "⚠️ Sistema no inicializado. Contacta al administrador.",
                    'sources': [],
                    'error': True
                }
            
            resultado = self.chain({"question": pregunta})
            
            return {
                'respuesta': resultado.get('answer', 'Sin respuesta'),
                'sources': resultado.get('source_documents', []),
                'error': False
            }
        
        except Exception as e:
            logger.error(f"❌ Error en query: {e}")
            return {
                'respuesta': f"❌ Error: {str(e)}",
                'sources': [],
                'error': True
            }
