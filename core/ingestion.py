import hashlib
import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Tuple, Dict, Optional

class IngestionService:
    def __init__(self):
        pass

    def compute_file_hash(self, file_path: Path) -> str:
        """Calcula el hash SHA-256 de un archivo para detección de duplicados."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Leer en chunks para no saturar memoria con archivos grandes
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def extract_doi(self, text: str) -> Optional[str]:
        """Intenta extraer un DOI del texto usando regex."""
        # Regex común para DOIs
        doi_pattern = r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b'
        match = re.search(doi_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def process_pdf(self, file_path: Path) -> Dict:
        """
        Procesa un PDF para extraer texto, metadatos y detectar DOI.
        Retorna un diccionario con la información extraída.
        """
        doc = fitz.open(file_path)
        full_text = ""
        
        # Extraer texto de todas las páginas
        for page in doc:
            full_text += page.get_text()

        # Extraer metadatos básicos del PDF
        metadata = doc.metadata
        
        # Intentar extraer DOI del texto
        doi = self.extract_doi(full_text)
        
        # Calcular hash
        file_hash = self.compute_file_hash(file_path)

        return {
            "file_name": file_path.name,
            "hash": file_hash,
            "doi": doi,
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "page_count": doc.page_count,
            "content": full_text,
            "file_path": str(file_path)
        }
