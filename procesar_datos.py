# procesar_datos.py - Procesamiento de Datos y Documentos
"""
Módulo de procesamiento de documentos PDF y creación de vectorstore
Gestiona carga, división y almacenamiento de embeddings
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

# Configurar logging
logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Procesador de datos y documentos PDF
    Gestiona carga, división, vectorización e indexación de documentos
    """
    
    def __init__(
        self, 
        pdf_dir: str = "data/pdfs", 
        db_path: str = "data/db/chroma_db",
        api_key: Optional[str] = None
    ):
        """
        Inicializar procesador de datos
        
        Args:
            pdf_dir: Directorio de PDFs
            db_path: Ruta de la base de datos Chroma
            api_key: API key de OpenAI (si no está en .env)
        
        Raises:
            ValueError: Si no hay API key disponible
        """
        self.pdf_dir = pdf_dir
        self.db_path = db_path
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("❌ OPENAI_API_KEY no configurada")
        
        # Crear directorios si no existen
        Path(pdf_dir).mkdir(parents=True, exist_ok=True)
        Path(db_path).mkdir(parents=True, exist_ok=True)
        
        # Estadísticas
        self.stats = {
            'pdfs_procesados': 0,
            'total_documentos': 0,
            'total_chunks': 0,
            'tiempo_procesamiento': 0,
            'ultima_actualizacion': None
        }
        
        self._cargar_estadisticas()
        logger.info(f"✅ DataProcessor inicializado")
        logger.info(f"   📂 PDFs: {pdf_dir}")
        logger.info(f"   🗂️ DB: {db_path}")
    
    def _cargar_estadisticas(self):
        """Cargar estadísticas previas desde archivo"""
        stats_file = Path(self.db_path) / "estadisticas.json"
        try:
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                logger.info(f"✅ Estadísticas cargadas: {self.stats['pdfs_procesados']} PDFs")
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cargar estadísticas: {e}")
    
    def _guardar_estadisticas(self):
        """Guardar estadísticas actual en archivo"""
        try:
            stats_file = Path(self.db_path) / "estadisticas.json"
            self.stats['ultima_actualizacion'] = datetime.now().isoformat()
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando estadísticas: {e}")
    
    def listar_pdfs(self) -> List[Tuple[str, int]]:
        """
        Listar todos los PDFs disponibles
        
        Returns:
            Lista de tuplas (nombre_archivo, tamaño_kb)
        """
        pdfs = []
        
        try:
            pdf_dir = Path(self.pdf_dir)
            
            if not pdf_dir.exists():
                logger.warning(f"⚠️ Directorio {self.pdf_dir} no existe")
                return pdfs
            
            for pdf_file in pdf_dir.glob("*.pdf"):
                tamaño_kb = pdf_file.stat().st_size / 1024
                pdfs.append((pdf_file.name, tamaño_kb))
            
            return sorted(pdfs, key=lambda x: x[0])
        
        except Exception as e:
            logger.error(f"❌ Error listando PDFs: {e}")
            return pdfs
    
    def cargar_pdfs(self, filtro: Optional[str] = None) -> Tuple[List[Document], int]:
        """
        Cargar todos los PDFs del directorio
        
        Args:
            filtro: Opcional - filtrar por nombre de archivo
        
        Returns:
            Tupla (lista de documentos, número de páginas totales)
        """
        documentos = []
        total_paginas = 0
        
        try:
            pdf_dir = Path(self.pdf_dir)
            
            if not pdf_dir.exists():
                logger.warning(f"⚠️ Directorio {self.pdf_dir} no existe")
                return documentos, total_paginas
            
            archivos_pdf = list(pdf_dir.glob("*.pdf"))
            
            if not archivos_pdf:
                logger.warning(f"⚠️ No se encontraron PDFs en {self.pdf_dir}")
                return documentos, total_paginas
            
            logger.info(f"📂 Encontrados {len(archivos_pdf)} archivos PDF")
            
            for pdf_file in archivos_pdf:
                # Aplicar filtro si existe
                if filtro and filtro.lower() not in pdf_file.name.lower():
                    continue
                
                try:
                    logger.info(f"📄 Cargando {pdf_file.name}...")
                    
                    loader = PyPDFLoader(str(pdf_file))
                    docs = loader.load()
                    
                    # Agregar metadata
                    for doc in docs:
                        doc.metadata['source'] = pdf_file.name
                        doc.metadata['ruta_completa'] = str(pdf_file)
                    
                    documentos.extend(docs)
                    total_paginas += len(docs)
                    
                    logger.info(f"✅ {pdf_file.name}: {len(docs)} páginas")
                
                except Exception as e:
                    logger.error(f"❌ Error cargando {pdf_file.name}: {e}")
                    continue
            
            logger.info(f"✅ Total: {len(documentos)} documentos, {total_paginas} páginas")
            return documentos, total_paginas
        
        except Exception as e:
            logger.error(f"❌ Error en cargar_pdfs: {e}")
            return documentos, total_paginas
    
    def dividir_documentos(
        self, 
        documentos: List[Document],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Document]:
        """
        Dividir documentos en chunks procesables
        
        Args:
            documentos: Lista de documentos
            chunk_size: Tamaño de cada chunk
            chunk_overlap: Superposición entre chunks
        
        Returns:
            Lista de chunks
        """
        try:
            if not documentos:
                logger.warning("⚠️ Sin documentos para dividir")
                return []
            
            logger.info(f"✂️ Dividiendo {len(documentos)} documentos...")
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
                length_function=len
            )
            
            chunks = splitter.split_documents(documentos)
            
            logger.info(f"✅ {len(chunks)} chunks creados")
            self.stats['total_chunks'] = len(chunks)
            
            return chunks
        
        except Exception as e:
            logger.error(f"❌ Error dividiendo documentos: {e}")
            return []
    
    def crear_vectorstore(
        self, 
        documentos: List[Document],
        modo: str = "create"
    ) -> bool:
        """
        Crear o actualizar vectorstore de Chroma
        
        Args:
            documentos: Lista de documentos/chunks
            modo: 'create' (nuevo) o 'add' (agregar a existente)
        
        Returns:
            True si éxito, False si falla
        """
        try:
            if not documentos:
                logger.warning("⚠️ Sin documentos para vectorizar")
                return False
            
            logger.info(f"🔧 {'Creando' if modo == 'create' else 'Actualizando'} vectorstore...")
            logger.info(f"   📊 {len(documentos)} documentos")
            
            # Crear embeddings
            embeddings = OpenAIEmbeddings(
                api_key=self.api_key,
                model="text-embedding-3-small"
            )
            
            if modo == "create":
                # Crear nuevo vectorstore
                vectorstore = Chroma.from_documents(
                    documents=documentos,
                    embedding=embeddings,
                    persist_directory=self.db_path,
                    collection_name="corus_documentos"
                )
            else:
                # Cargar existente y agregar
                vectorstore = Chroma(
                    persist_directory=self.db_path,
                    embedding_function=embeddings,
                    collection_name="corus_documentos"
                )
                vectorstore.add_documents(documentos)
            
            # Persistir
            vectorstore.persist()
            
            logger.info(f"✅ Vectorstore guardado en {self.db_path}")
            self.stats['pdfs_procesados'] += 1
            self.stats['total_documentos'] = len(documentos)
            self._guardar_estadisticas()
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error creando vectorstore: {e}")
            return False
    
    def procesar_todos(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        modo: str = "create"
    ) -> Dict[str, Any]:
        """
        Pipeline completo: cargar → dividir → vectorizar
        
        Args:
            chunk_size: Tamaño de chunks
            chunk_overlap: Superposición entre chunks
            modo: 'create' o 'add'
        
        Returns:
            Dict con resultados del procesamiento
        """
        inicio = datetime.now()
        
        try:
            logger.info("🚀 Iniciando procesamiento completo de datos...")
            
            # 1. Cargar PDFs
            logger.info("📥 Paso 1: Cargando PDFs...")
            documentos, total_paginas = self.cargar_pdfs()
            
            if not documentos:
                logger.warning("⚠️ No se cargaron documentos")
                return {
                    'exitoso': False,
                    'mensaje': 'No se encontraron PDFs para procesar',
                    'detalles': {}
                }
            
            # 2. Dividir documentos
            logger.info("✂️ Paso 2: Dividiendo documentos...")
            chunks = self.dividir_documentos(
                documentos,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            if not chunks:
                logger.warning("⚠️ Error al dividir documentos")
                return {
                    'exitoso': False,
                    'mensaje': 'Error al dividir documentos',
                    'detalles': {}
                }
            
            # 3. Vectorizar
            logger.info("🔧 Paso 3: Creando vectorstore...")
            exito = self.crear_vectorstore(chunks, modo=modo)
            
            tiempo_total = (datetime.now() - inicio).total_seconds()
            self.stats['tiempo_procesamiento'] = tiempo_total
            
            if exito:
                resultado = {
                    'exitoso': True,
                    'mensaje': '✅ Procesamiento completado exitosamente',
                    'detalles': {
                        'pdfs_procesados': len(self.listar_pdfs()),
                        'documentos_cargados': len(documentos),
                        'paginas_totales': total_paginas,
                        'chunks_creados': len(chunks),
                        'tiempo_segundos': round(tiempo_total, 2),
                        'base_datos': self.db_path
                    }
                }
                logger.info(f"✅ Procesamiento completado en {tiempo_total:.2f}s")
                return resultado
            else:
                return {
                    'exitoso': False,
                    'mensaje': 'Error al crear vectorstore',
                    'detalles': {}
                }
        
        except Exception as e:
            logger.error(f"❌ Error en procesar_todos: {e}")
            return {
                'exitoso': False,
                'mensaje': f'Error durante procesamiento: {str(e)}',
                'detalles': {}
            }
    
    def procesar_pdf_individual(self, nombre_archivo: str) -> Dict[str, Any]:
        """
        Procesar un PDF individual
        
        Args:
            nombre_archivo: Nombre del archivo PDF
        
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            logger.info(f"📄 Procesando PDF individual: {nombre_archivo}")
            
            # Cargar solo este PDF
            pdf_path = Path(self.pdf_dir) / nombre_archivo
            
            if not pdf_path.exists():
                return {
                    'exitoso': False,
                    'mensaje': f'Archivo no encontrado: {nombre_archivo}'
                }
            
            loader = PyPDFLoader(str(pdf_path))
            docs = loader.load()
            
            # Dividir
            chunks = self.dividir_documentos(docs)
            
            # Vectorizar (agregar al existente)
            exito = self.crear_vectorstore(chunks, modo="add")
            
            return {
                'exitoso': exito,
                'mensaje': f'{"✅" if exito else "❌"} PDF procesado',
                'detalles': {
                    'archivo': nombre_archivo,
                    'paginas': len(docs),
                    'chunks': len(chunks)
                }
            }
        
        except Exception as e:
            logger.error(f"❌ Error procesando PDF: {e}")
            return {
                'exitoso': False,
                'mensaje': f'Error: {str(e)}'
            }
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de procesamiento
        
        Returns:
            Dict con estadísticas
        """
        pdfs = self.listar_pdfs()
        
        return {
            'pdfs_disponibles': len(pdfs),
            'pdfs_procesados': self.stats.get('pdfs_procesados', 0),
            'total_documentos': self.stats.get('total_documentos', 0),
            'total_chunks': self.stats.get('total_chunks', 0),
            'tiempo_procesamiento_segundos': self.stats.get('tiempo_procesamiento', 0),
            'ultima_actualizacion': self.stats.get('ultima_actualizacion', 'Nunca'),
            'tamaño_db_mb': self._obtener_tamaño_db(),
            'directorio_pdfs': self.pdf_dir,
            'directorio_db': self.db_path
        }
    
    def _obtener_tamaño_db(self) -> float:
        """Obtener tamaño de la base de datos en MB"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.db_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            
            return round(total_size / (1024 * 1024), 2)
        except Exception as e:
            logger.warning(f"⚠️ Error calculando tamaño: {e}")
            return 0.0
    
    def limpiar_vectorstore(self) -> bool:
        """
        Limpiar y reiniciar vectorstore
        
        Returns:
            True si éxito, False si falla
        """
        try:
            import shutil
            
            if os.path.exists(self.db_path):
                shutil.rmtree(self.db_path)
                Path(self.db_path).mkdir(parents=True, exist_ok=True)
                
                self.stats = {
                    'pdfs_procesados': 0,
                    'total_documentos': 0,
                    'total_chunks': 0,
                    'tiempo_procesamiento': 0,
                    'ultima_actualizacion': None
                }
                self._guardar_estadisticas()
                
                logger.info("🗑️ Vectorstore limpiado")
                return True
        
        except Exception as e:
            logger.error(f"❌ Error limpiando vectorstore: {e}")
        
        return False
