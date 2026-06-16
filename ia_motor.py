# ia_motor.py 
"""
Motor IA centralizado para CorusIntranetEngine v2.0
Implementa patrón Singleton con inicialización robusta y prevención de alucinaciones
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import HumanMessage, AIMessage
from langchain.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class CorusIntranetEngine:
    """
    Motor IA de Corus - Singleton Pattern
    Gestiona interacción con OpenAI y vectorstore
    """
    
    _instancia = None
    _inicializado = False
    
    def __new__(cls):
        """Implementar patrón Singleton"""
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia
    
    def __init__(self):
        """Inicialización segura con verificaciones"""
        if CorusIntranetEngine._inicializado:
            return
        
        logger.info("🚀 Inicializando CorusIntranetEngine...")
        
        # Validar API Key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ OPENAI_API_KEY no encontrada en .env\n"
                "Por favor crea archivo .env con: OPENAI_API_KEY=sk-..."
            )
        
        logger.info(f"✅ API Key detectada: {self.api_key[:20]}...")
        
        # Inicializar componentes
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.memory = None
        self.chain = None
        self.estado = "inicializando"
        self.estadisticas = {
            "queries_totales": 0,
            "queries_exitosas": 0,
            "queries_fallidas": 0,
            "tokens_usados": 0,
            "ultima_consulta": None
        }
        
        # Crear componentes
        try:
            self._crear_embeddings()
            self._cargar_vectorstore()
            self._crear_llm()
            self._crear_memoria()
            self._crear_cadena()
            
            self.estado = "listo"
            CorusIntranetEngine._inicializado = True
            logger.info("✅ CorusIntranetEngine inicializado correctamente")
        
        except Exception as e:
            self.estado = "error"
            logger.error(f"❌ Error en inicialización: {e}", exc_info=True)
            raise
    
    def _crear_embeddings(self):
        """Crear embeddings de OpenAI"""
        logger.info("🔄 Creando embeddings...")
        try:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.api_key
            )
            logger.info("✅ Embeddings creados")
        except Exception as e:
            logger.error(f"❌ Error creando embeddings: {e}")
            raise
    
    def _cargar_vectorstore(self):
        """Cargar o crear vectorstore"""
        logger.info("🔄 Cargando vectorstore...")
        try:
            db_path = "data/db/chroma_db"
            Path(db_path).mkdir(parents=True, exist_ok=True)
            
            self.vectorstore = Chroma(
                persist_directory=db_path,
                embedding_function=self.embeddings,
                collection_name="corus_documentos"
            )
            
            doc_count = self.vectorstore._collection.count()
            logger.info(f"✅ Vectorstore cargado ({doc_count} documentos)")
        
        except Exception as e:
            logger.error(f"⚠️ Error cargando vectorstore: {e}")
            self.vectorstore = None
    
    def _crear_llm(self):
        """Crear instancia de GPT-4o-mini"""
        logger.info("🔄 Creando LLM...")
        try:
            self.llm = ChatOpenAI(
                openai_api_key=self.api_key,
                model_name="gpt-4o-mini",
                temperature=0.0,
                max_tokens=2048,
                request_timeout=60
            )
            logger.info("✅ LLM creado")
        except Exception as e:
            logger.error(f"❌ Error creando LLM: {e}")
            raise
    
    def _crear_memoria(self):
        """Crear memoria de conversación"""
        logger.info("🔄 Creando memoria...")
        try:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer",
                human_prefix="Usuario",
                ai_prefix="Asistente"
            )
            logger.info("✅ Memoria creada")
        except Exception as e:
            logger.error(f"❌ Error creando memoria: {e}")
            raise
    
    def _crear_cadena(self):
        """Crear cadena de conversación con Prompt Corporativo Estricto"""
        logger.info("🔄 Creando cadena...")
        try:
            if self.vectorstore and self.llm:
                # 🚨 Prompt personalizado para evitar alucinaciones
                prompt_template = """Eres un Consultor y Analista de Procesos Senior en Corus.
Tu misión es resolver la duda técnica del usuario basándote EXCLUSIVAMENTE en la documentación provista.
Si no encuentras la respuesta exacta en los fragmentos extraídos, debes decir honestamente: "Compañero, tras revisar la base de datos corporativa, no logré ubicar el procedimiento explícito para este escenario." NO inventes información ni asumas pasos que no estén en el texto.

Documentos oficiales extraídos:
{context}

Pregunta del usuario: {question}
Respuesta experta (usa listas, negritas y formato claro para el analista):"""
                
                PROMPT = PromptTemplate(
                    template=prompt_template, input_variables=["context", "question"]
                )

                self.chain = ConversationalRetrievalChain.from_llm(
                    llm=self.llm,
                    retriever=self.vectorstore.as_retriever(search_kwargs={"k": 6}),
                    memory=self.memory,
                    return_source_documents=True,
                    combine_docs_chain_kwargs={"prompt": PROMPT},
                    verbose=False,
                    get_chat_history=lambda h: h
                )
                logger.info("✅ Cadena con retriever y prompt corporativo estricto creada")
            else:
                logger.warning("⚠️ Cadena sin retriever (no hay vectorstore)")
                self.chain = None
        
        except Exception as e:
            logger.error(f"❌ Error creando cadena: {e}")
            self.chain = None
    
    def query(self, pregunta: str, contexto: Dict = None) -> Dict[str, Any]:
        """Ejecutar query al motor IA"""
        try:
            if self.estado != "listo":
                return {
                    'exito': False,
                    'respuesta': "❌ Sistema no inicializado. Por favor recarga la página.",
                    'sources': [],
                    'error': "SISTEMA_NO_LISTO",
                    'timestamp': datetime.now().isoformat()
                }
            
            if not self.chain:
                logger.warning("⚠️ Chain no disponible, usando LLM directo")
                respuesta_llm = self.llm.invoke([
                    HumanMessage(content=pregunta)
                ])
                
                self.estadisticas['queries_exitosas'] += 1
                
                return {
                    'exito': True,
                    'respuesta': respuesta_llm.content,
                    'sources': [],
                    'modo': 'LLM_DIRECTO',
                    'timestamp': datetime.now().isoformat()
                }
            
            logger.info(f"🔍 Query: {pregunta[:100]}...")
            
            resultado = self.chain.invoke({
                "question": pregunta,
                "chat_history": self.memory.buffer
            })
            
            self.estadisticas['queries_totales'] += 1
            self.estadisticas['queries_exitosas'] += 1
            self.estadisticas['ultima_consulta'] = datetime.now().isoformat()
            
            sources = []
            if resultado.get('source_documents'):
                sources = [
                    {
                        'contenido': doc.page_content[:500],
                        'metadata': doc.metadata,
                        'archivo': doc.metadata.get('source', 'desconocido')
                    }
                    for doc in resultado['source_documents'][:3]
                ]
            
            return {
                'exito': True,
                'respuesta': resultado.get('answer', 'Sin respuesta'),
                'sources': sources,
                'modo': 'RAG',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Error en query: {e}", exc_info=True)
            self.estadisticas['queries_fallidas'] += 1
            
            return {
                'exito': False,
                'respuesta': f"❌ Error procesando pregunta: {str(e)}",
                'sources': [],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def obtener_estado(self) -> Dict[str, Any]:
        """Obtener estado actual del motor"""
        return {
            'estado': self.estado,
            'chain_activa': self.chain is not None,
            'vectorstore_activo': self.vectorstore is not None,
            'memoria_activa': self.memory is not None,
            'estadisticas': self.estadisticas
        }

# Singleton global
_motor_global = None

def obtener_motor() -> CorusIntranetEngine:
    """Obtener instancia global del motor"""
    global _motor_global
    if _motor_global is None:
        _motor_global = CorusIntranetEngine()
    return _motor_global
