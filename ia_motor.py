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
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
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
        self.prompt_str = ""
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
            from langchain.embeddings import OpenAIEmbeddings
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
            import openai
            openai.api_key = self.api_key
            
            self.llm = ChatOpenAI(
                openai_api_key=self.api_key,
                model_name="gpt-3.5-turbo",
                temperature=0.0,
                max_tokens=2048,  # Respuestas mas completas
                request_timeout=90
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
Responde la consulta del usuario utilizando la documentación interna que aparece abajo.

Instrucciones:
- Construye una respuesta clara, completa y bien estructurada (pasos numerados, negritas y, si aparecen en el texto, las consultas SQL exactas).
- Usa la información de los documentos aunque sea parcial; siempre ofrece la mejor respuesta posible con lo que haya disponible. NO te disculpes ni digas que no encontraste el procedimiento.
- No inventes datos, pasos ni consultas que no aparezcan en la documentación.
- Responde directamente, sin saludos ("Hola") ni despedidas.

Documentación interna:
{context}

Consulta: {question}

Respuesta:"""
                
                self.prompt_str = prompt_template
                PROMPT = PromptTemplate(
                    template=prompt_template, input_variables=["context", "question"]
                )

                self.chain = ConversationalRetrievalChain.from_llm(
                    llm=self.llm,
                    retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),  # Reducido de 6 a 3
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
        """Ejecutar query al motor IA.

        Para EVITAR mezclar casos:
        - Cada pregunta es independiente (sin memoria de conversacion).
        - La respuesta usa SOLO el documento mas relevante (no combina PDFs).
        """
        try:
            if self.estado != "listo":
                return {
                    'exito': False,
                    'respuesta': "❌ Sistema no inicializado. Por favor recarga la página.",
                    'sources': [],
                    'error': "SISTEMA_NO_LISTO",
                    'timestamp': datetime.now().isoformat()
                }

            # Sin vectorstore -> LLM directo (fallback)
            if not self.vectorstore:
                logger.warning("⚠️ Vectorstore no disponible, usando LLM directo")
                respuesta_llm = self.llm.invoke([HumanMessage(content=pregunta)])
                self.estadisticas['queries_exitosas'] += 1
                return {
                    'exito': True,
                    'respuesta': respuesta_llm.content,
                    'sources': [],
                    'modo': 'LLM_DIRECTO',
                    'timestamp': datetime.now().isoformat()
                }

            logger.info(f"🔍 Query: {pregunta[:100]}...")

            # 1) Recuperar documentos relevantes (con score de distancia)
            try:
                docs_scored = self.vectorstore.similarity_search_with_score(pregunta, k=4)
            except Exception:
                docs_scored = [(d, 0.0) for d in self.vectorstore.similarity_search(pregunta, k=4)]
            docs = [d for d, _ in docs_scored]
            best_score = docs_scored[0][1] if docs_scored else None
            logger.info(f"🔎 Mejor distancia: {best_score}")

            self.estadisticas['queries_totales'] += 1
            self.estadisticas['ultima_consulta'] = datetime.now().isoformat()

            # Guarda de relevancia: si no hay coincidencia o es debil, no forzar un caso
            UMBRAL_DISTANCIA = 0.55
            if not docs or (best_score is not None and best_score > UMBRAL_DISTANCIA):
                self.estadisticas['queries_exitosas'] += 1
                return {
                    'exito': True,
                    'respuesta': (
                        "No encontré un caso que coincida con tu consulta. "
                        "¿Puedes indicarme el proceso? Por ejemplo: documentos en blanco, "
                        "cambio de información, elaborar/cargar HT, error por notificación, "
                        "pasar a cobros, validar denuncias o indicar etapa BPM."
                    ),
                    'sources': [],
                    'modo': 'RAG',
                    'timestamp': datetime.now().isoformat()
                }

            # 2) 🔒 Identificar el documento mas relevante (NO mezclar casos)
            fuente_principal = docs[0].metadata.get('source')

            # 3) Traer TODOS los fragmentos de ese documento para una
            #    respuesta COMPLETA (ordenados por chunk_id)
            chunks_doc = []
            try:
                data = self.vectorstore._collection.get(
                    where={"source": fuente_principal}
                )
                textos = data.get('documents') or []
                metas = data.get('metadatas') or []
                pares = list(zip(textos, metas))
                pares.sort(key=lambda x: (x[1] or {}).get('chunk_id', 0))
                chunks_doc = pares
            except Exception as e:
                logger.warning(f"⚠️ No se pudieron traer todos los chunks: {e}")

            if not chunks_doc:
                chunks_doc = [
                    (d.page_content, d.metadata)
                    for d in docs
                    if d.metadata.get('source') == fuente_principal
                ]

            # 4) Construir contexto completo (con tope de seguridad de tokens)
            contexto_texto = "\n\n".join(t for t, _ in chunks_doc)
            if len(contexto_texto) > 12000:
                contexto_texto = contexto_texto[:12000]
            prompt_final = self.prompt_str.format(
                context=contexto_texto, question=pregunta
            )

            # 5) Generar respuesta
            respuesta_llm = self.llm.invoke([HumanMessage(content=prompt_final)])
            self.estadisticas['queries_exitosas'] += 1

            sources = [
                {
                    'contenido': t,
                    'metadata': m or {},
                    'archivo': (m or {}).get('source', 'desconocido')
                }
                for t, m in chunks_doc
            ]

            return {
                'exito': True,
                'respuesta': respuesta_llm.content,
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
