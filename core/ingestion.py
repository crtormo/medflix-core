import hashlib
import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Tuple, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self):
        pass

    def compute_file_hash(self, file_path: Path) -> str:
        """Calcula el hash SHA-256 de un archivo para detección de duplicados."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def extract_doi(self, text: str) -> Optional[str]:
        """Intenta extraer un DOI del texto usando regex."""
        doi_pattern = r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b'
        match = re.search(doi_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def generate_thumbnail(self, doc: fitz.Document, file_name: str) -> Optional[str]:
        """Genera un thumbnail de la primera página del PDF."""
        try:
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3))  # Escalar a 30%
            output_dir = Path("data/thumbnails")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            thumb_name = f"{Path(file_name).stem}_thumb.png"
            thumb_path = output_dir / thumb_name
            pix.save(str(thumb_path))
            return str(thumb_path)
        except Exception as e:
            logger.error(f"Error generando thumbnail: {e}")
            return None

    def process_pdf(self, file_path: Path) -> Dict:
        """
        Procesa un PDF para extraer texto, metadatos, imágenes y generar thumbnail.
        """
        doc = fitz.open(file_path)
        full_text = ""
        
        # Extraer texto de todas las páginas (limitamos a primeras 30 para evitar sobrecarga)
        for i, page in enumerate(doc):
            if i < 30:
                full_text += page.get_text()
            else:
                break

        # Metadatos básicos del PDF
        metadata = doc.metadata
        
        # Intentar extraer DOI
        doi = self.extract_doi(full_text)
        
        # Hash
        file_hash = self.compute_file_hash(file_path)
        
        # Thumbnail
        thumbnail_path = self.generate_thumbnail(doc, file_path.name)

        return {
            "file_name": file_path.name,
            "hash": file_hash,
            "doi": doi,
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "creation_date": metadata.get("creationDate", ""),
            "page_count": doc.page_count,
            "content": full_text,
            "file_path": str(file_path),
            "thumbnail_path": thumbnail_path
        }

