"""
Servicio de Generación de Referencias para MedFlix Core
Genera citas académicas en formato Vancouver/APA usando citeproc-py
"""
from typing import Dict, Optional
from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc.source.json import CiteProcJSON
from citeproc_styles import get_style_filepath
import json


class ReferenceGenerator:
    """Genera referencias bibliográficas en diferentes formatos."""
    
    def __init__(self, default_style: str = "vancouver"):
        """
        Args:
            default_style: Estilo por defecto ('vancouver', 'apa', 'chicago-author-date')
        """
        self.default_style = default_style
    
    def generate_citation(self, metadata: Dict, style: Optional[str] = None) -> str:
        """
        Genera una cita formateada a partir de metadatos del paper.
        
        Args:
            metadata: Diccionario con title, author, doi, year, etc.
            style: Estilo de cita ('vancouver', 'apa', etc.)
            
        Returns:
            Cita formateada como string
        """
        style = style or self.default_style
        
        # Construir datos JSON para citeproc
        csl_data = self._build_csl_json(metadata)
        
        if not csl_data:
            return self._fallback_citation(metadata)
        
        try:
            # Cargar estilo
            style_path = get_style_filepath(style)
            bib_style = CitationStylesStyle(style_path, validate=False)
            
            # Crear fuente de datos
            bib_source = CiteProcJSON([csl_data])
            
            # Crear bibliografía
            bibliography = CitationStylesBibliography(bib_style, bib_source)
            
            # Registrar cita
            citation = Citation([CitationItem(csl_data['id'])])
            bibliography.register(citation)
            
            # Generar bibliografía
            bib_entries = bibliography.bibliography()
            
            if bib_entries:
                return str(bib_entries[0])
            
        except Exception as e:
            print(f"Error generando cita con citeproc: {e}")
        
        return self._fallback_citation(metadata)
    
    def _build_csl_json(self, metadata: Dict) -> Optional[Dict]:
        """Construye el JSON en formato CSL a partir de metadatos."""
        if not metadata.get('title'):
            return None
        
        csl_item = {
            "id": metadata.get('hash', 'unknown'),
            "type": "article-journal",
            "title": metadata.get('title', 'Sin título'),
        }
        
        # Autor(es)
        author_str = metadata.get('author', '')
        if author_str:
            authors = []
            for name in author_str.split(','):
                name = name.strip()
                if name:
                    parts = name.rsplit(' ', 1)
                    if len(parts) == 2:
                        authors.append({"family": parts[1], "given": parts[0]})
                    else:
                        authors.append({"family": name})
            if authors:
                csl_item["author"] = authors
        
        # DOI
        if metadata.get('doi'):
            csl_item["DOI"] = metadata['doi']
        
        # Año (intentar extraer de metadata o usar actual)
        if metadata.get('year'):
            csl_item["issued"] = {"date-parts": [[int(metadata['year'])]]}
        
        return csl_item
    
    def _fallback_citation(self, metadata: Dict) -> str:
        """Genera una cita básica si citeproc falla."""
        parts = []
        
        if metadata.get('author'):
            parts.append(metadata['author'])
        
        if metadata.get('title'):
            parts.append(f"\"{metadata['title']}\"")
        
        if metadata.get('doi'):
            parts.append(f"DOI: {metadata['doi']}")
        
        return ". ".join(parts) + "." if parts else "Referencia no disponible"
    
    def generate_vancouver(self, metadata: Dict) -> str:
        """Atajo para generar cita en formato Vancouver."""
        return self.generate_citation(metadata, style="vancouver")
    
    def generate_apa(self, metadata: Dict) -> str:
        """Atajo para generar cita en formato APA."""
        return self.generate_citation(metadata, style="apa")
