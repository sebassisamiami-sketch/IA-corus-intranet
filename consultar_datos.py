# ARCHIVO NO USADO EN PRODUCCIÓN - Solo para debugging local
# Comentado para evitar dependencias de sentence-transformers

"""
import os
import warnings
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import Chroma
from langchain.embeddings.base import Embeddings
from typing import List

# Apagar advertencias molestas de paralelismo en la terminal
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class SentenceTransformerEmbeddings(Embeddings):
    """Wrapper para usar sentence-transformers con LangChain"""
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()

class QAInspector:
    """Herramienta de depuración y auditoría para la base de datos vectorial de Corus."""
    def __init__(self):
        print("\n==========================================================")
        print("🔬 [QA CONSOLE] INSPECTOR DE VECTORES EN BRUTO")
        print("==========================================================")
        
        self.carpeta_db = "./chroma_db"
        
        # Validación de infraestructura
        if not os.path.exists(self.carpeta_db):
            print("❌ ERROR CRÍTICO: No existe la base de datos vectorial.")
            print("🛠️ ACCIÓN: Ejecuta 'procesar_datos.py' primero para indexar los manuales.")
            exit()
            
        print("⏳ Conectando con el motor de embeddings local...")
        try:
            self.embeddings = SentenceTransformerEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self.vector_db = Chroma(persist_directory=self.carpeta_db, embedding_function=self.embeddings)
            
            # Mostrar estadísticas rápidas de salud de la BD
            total_vectores = len(self.vector_db.get()['ids'])
            print(f"✅ Conexión exitosa. Total de fragmentos indexados listos para auditoría: {total_vectores}")
        except Exception as e:
            print(f"❌ Error al conectar con ChromaDB: {e}")
            exit()

    def inspeccionar(self):
        """Bucle interactivo para auditar fragmentos matemáticos sin intervención del LLM."""
        print("\n==========================================================")
        print(" Escribe tu consulta para ver cómo reacciona la base de datos.")
        print(" Escribe 'salir' para terminar la auditoría.")
        print("==========================================================\n")
        
        while True:
            try:
                pregunta = input("🔍 Consulta de auditoría: ")
                
                if pregunta.lower().strip() in ['salir', 'exit', 'quit']:
                    print("\n🔒 Cerrando inspector de calidad. ¡Hasta pronto!")
                    break
                if not pregunta.strip():
                    continue
                    
                print("\nBuscando los 3 fragmentos matemáticamente más cercanos (k=3)...")
                # Extraemos los mejores resultados
                resultados = self.vector_db.similarity_search(pregunta, k=3)
                
                if not resultados:
                    print("⚠️ No se encontraron coincidencias en la base de datos.")
                    continue
                    
                # Despliegue de resultados con trazabilidad absoluta
                for i, doc in enumerate(resultados):
                    meta = doc.metadata
                    categoria = meta.get('categoria', 'Desconocida')
                    fuente = meta.get('fuente', 'Desconocida')
                    pagina = meta.get('pagina', '?')
                    
                    print(f"\n--- 📄 MATCH #{i+1} ---")
                    print(f"📂 DOMINIO: {categoria} | 📄 ARCHIVO: {fuente} | 📑 PÁG: {pagina}")
                    print("-" * 60)
                    print(doc.page_content)
                    print("-" * 60)
                    
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupción detectada. Cerrando inspector...")
                break

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    inspector = QAInspector()
    inspector.inspeccionar()