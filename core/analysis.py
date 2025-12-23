from .ingestion import IngestionService
from services.groq_service import GroqService
from services.vector_store import VectorStoreService
from pathlib import Path
from typing import Dict, Any

class AnalysisCore:
    def __init__(self):
        self.ingestion = IngestionService()
        self.vector_store = VectorStoreService()
        # Inicializar GroqService de manera lazy o segura para no fallar si no hay key en tiempo de import
        try:
            self.groq = GroqService()
        except ValueError:
            print("Warning: Groq API Key not found. AI features will be disabled.")
            self.groq = None

    def process_and_analyze(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        
        # 1. Ingesta básica
        doc_data = self.ingestion.process_pdf(path)
        
        # 2. Verificar duplicados por Hash
        if self.vector_store.check_duplicate(doc_data['hash']):
            return {"status": "duplicate", "reason": "hash_match", "data": doc_data}
            
        # 3. Verificar duplicados por DOI (si existe)
        if doc_data.get('doi') and self.vector_store.check_doi_duplicate(doc_data['doi']):
            return {"status": "duplicate", "reason": "doi_match", "data": doc_data}

        # 4. Análisis IA (si Groq está disponible)
        analysis_result = ""
        snippets = {}
        
        if self.groq:
            # Auditoría
            analysis_result = self.groq.epistemological_audit(doc_data['content'])
            # Snippets
            snippets = self.groq.generate_snippets(doc_data['content'])
        
        # 5. Guardar en Vector Store
        # Combinamos el contenido con el análisis para mejorar la búsqueda semántica sobre la "calidad" del paper
        combined_text_for_embedding = f"{doc_data['content']}\n\n--- AI ANALYSIS ---\n{analysis_result}"
        
        # Generar ID único (usamos el hash)
        doc_id = doc_data['hash']
        
        # Metadata enriquecida
        metadata = {
            "title": doc_data['title'],
            "author": doc_data['author'],
            "doi": doc_data['doi'],
            "hash": doc_data['hash'],
            "n_study": snippets.get('n_study', 'N/A'),
            "study_type": snippets.get('study_type', 'Unknown'),
            # Guardamos los primeros 100 chars del analisis como preview en metadata si queremos
        }

        self.vector_store.add_document(
            doc_id=doc_id,
            text=combined_text_for_embedding,
            metadata=metadata
        )

        return {
            "status": "success",
            "doc_id": doc_id,
            "metadata": metadata,
            "analysis": analysis_result,
            "snippets": snippets
        }
