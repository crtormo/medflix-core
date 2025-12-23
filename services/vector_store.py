import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os
from pathlib import Path

class VectorStoreService:
    def __init__(self, db_path: str = "./data/chroma_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="medflix_papers")

    def add_document(self, 
                     doc_id: str, 
                     text: str, 
                     metadata: Dict, 
                     embeddings: Optional[List[float]] = None):
        """
        Agrega un documento a la colección.
        Si no se proveen embeddings, ChromaDB usará ef (embedding function) por defecto (all-MiniLM-L6-v2).
        """
        # Asegurarse de que metadata no tenga valores None, ChromaDB no lo soporta bien
        clean_metadata = {k: v for k, v in metadata.items() if v is not None}
        
        self.collection.add(
            documents=[text],
            metadatas=[clean_metadata],
            ids=[doc_id],
            embeddings=[embeddings] if embeddings else None
        )

    def check_duplicate(self, file_hash: str) -> bool:
        """
        Verifica si un archivo ya existe basado en su hash SHA-256.
        Buscamos en metadata donde hash == file_hash.
        """
        results = self.collection.get(
            where={"hash": file_hash}
        )
        return len(results['ids']) > 0

    def check_doi_duplicate(self, doi: str) -> bool:
        """
        Verifica si un paper ya existe basado en su DOI.
        """
        if not doi:
            return False
            
        results = self.collection.get(
            where={"doi": doi}
        )
        return len(results['ids']) > 0

    def query_similar(self, query_text: str, n_results: int = 5) -> Dict:
        """
        Busca documentos similares.
        """
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
