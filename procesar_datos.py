import os
import sys
import warnings
import glob
import re
from typing import List, Set
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Desactivación de alertas de paralelismo
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class SistemaConfig:
    """Constantes globales del sistema de gestión del conocimiento (KMS)."""
    CARPETA_DB: str = "./chroma_db"
    ARCHIVO_REGISTRO: str = "archivos_indexados.txt"
    MODELO_EMBEDDINGS: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200

class PipelineETL:
    """Módulo avanzado de Extracción, Transformación y Carga (ETL) con Auto-Sanación y Context Grounding."""
    def __init__(self, vector_db: Chroma):
        self.vector_db = vector_db
        self.config = SistemaConfig()

    def _limpiar_texto_pdf(self, texto: str) -> str:
        """Sanitiza el texto eliminando ruido y caracteres nulos que rompen la matemática vectorial."""
        if not texto:
            return ""
        texto = texto.replace('\x00', '')
        texto = re.sub(r'(?<!\n)\n(?!\n)', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

    def ejecutar_sincronizacion(self) -> Set[str]:
        print("\n==========================================================")
        print("⚙️ [MÓDULO ETL] INICIANDO PROCESAMIENTO DE DATOS CORUS")
        print("==========================================================")
        print("🔄 [ETL] Iniciando escaneo profundo del repositorio...")
        
        # 🔥 Mecanismo de Auto-Sanación V2 (Detección real de Vectores)
        db_vacia = True
        try:
            if len(self.vector_db.get()['ids']) > 0:
                db_vacia = False
        except Exception:
            pass

        if os.path.exists(self.config.ARCHIVO_REGISTRO) and db_vacia:
            print("⚠️ [SISTEMA] Inconsistencia detectada: Base de datos vectorial VACÍA pero registro TXT activo.")
            print("🛠️ [SISTEMA] Auto-sanando infraestructura... Forzando re-indexación completa.")
            os.remove(self.config.ARCHIVO_REGISTRO)
            
        archivos_pdf: List[str] = glob.glob("**/*.pdf", recursive=True)
        
        procesados: Set[str] = set()
        if os.path.exists(self.config.ARCHIVO_REGISTRO):
            with open(self.config.ARCHIVO_REGISTRO, "r", encoding="utf-8") as f:
                procesados = set(f.read().splitlines())
                
        nuevos_archivos: List[str] = [a for a in archivos_pdf if a not in procesados]
        categorias_detectadas: Set[str] = set()

        # Registro estricto de categorías basado en rutas absolutas
        for archivo in archivos_pdf:
            ruta_absoluta = os.path.abspath(archivo)
            carpeta_padre = os.path.basename(os.path.dirname(ruta_absoluta))
            if carpeta_padre and "chroma_db" not in ruta_absoluta:
                categorias_detectadas.add(carpeta_padre)

        if not nuevos_archivos:
            print("💾 [ETL] Base de datos vectorial alineada. Sin novedades.")
            return categorias_detectadas

        print(f"⚡ [ETL] Detectados {len(nuevos_archivos)} documento(s). Ejecutando sanitización y Context Grounding...")
        
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " ", ""],
            chunk_size=self.config.CHUNK_SIZE, 
            chunk_overlap=self.config.CHUNK_OVERLAP,
            length_function=len
        )
        
        for archivo in nuevos_archivos:
            ruta_absoluta = os.path.abspath(archivo)
            nombre_archivo = os.path.basename(ruta_absoluta)
            categoria = os.path.basename(os.path.dirname(ruta_absoluta))
            
            if not categoria or categoria == os.path.basename(os.getcwd()) or "chroma_db" in ruta_absoluta:
                categoria = "General"
                
            categorias_detectadas.add(categoria)
            print(f"   📥 Ingestando: {nombre_archivo} ➔ [Categoría Física: {categoria}]")
            
            try:
                reader = PdfReader(archivo)
                fragmentos_procesados = 0
                
                for num_pagina, pagina in enumerate(reader.pages):
                    texto_crudo = pagina.extract_text()
                    texto_limpio = self._limpiar_texto_pdf(texto_crudo)
                    
                    if texto_limpio:
                        fragmentos_base = text_splitter.split_text(texto_limpio)
                        fragmentos_enriquecidos = []
                        metadatos_lote = []
                        
                        for frag in fragmentos_base:
                            texto_enriquecido = f"[DOMINIO_DEL_CASO: {categoria} | DOCUMENTO_FUENTE: {nombre_archivo} | PAGINA: {num_pagina + 1}]\n{frag}"
                            fragmentos_enriquecidos.append(texto_enriquecido)
                            
                            metadatos_lote.append({
                                "categoria": categoria, 
                                "fuente": nombre_archivo,
                                "pagina": num_pagina + 1 
                            })
                        
                        self.vector_db.add_texts(texts=fragmentos_enriquecidos, metadatas=metadatos_lote)
                        fragmentos_procesados += len(fragmentos_enriquecidos)
                
                if fragmentos_procesados > 0:
                    with open(self.config.ARCHIVO_REGISTRO, "a", encoding="utf-8") as f:
                        f.write(archivo + "\n")
                else:
                    print(f"   ⚠️ Advertencia: No se pudo extraer texto legible de {nombre_archivo}.")
                    
            except Exception as e:
                print(f"   ❌ Fallo crítico al procesar la fuente {nombre_archivo}: {e}")
                
        print("✅ [ETL] Sanitización e ingesta terminadas con éxito.\n")
        return categorias_detectadas

# --- EJECUCIÓN INDEPENDIENTE DEL MÓDULO ---
if __name__ == "__main__":
    try:
        config = SistemaConfig()
        print("Conectando con el motor de Embeddings...")
        embeddings = HuggingFaceEmbeddings(model_name=config.MODELO_EMBEDDINGS)
        vector_db = Chroma(persist_directory=config.CARPETA_DB, embedding_function=embeddings)
        
        # Ejecutamos el pipeline
        pipeline = PipelineETL(vector_db)
        pipeline.ejecutar_sincronizacion()
        
    except Exception as e:
        print(f"\n❌ Error fatal al iniciar el módulo ETL: {e}")