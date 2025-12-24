
from habanero import Crossref
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self):
        self.cr = Crossref()

    def get_metadata_by_doi(self, doi: str) -> Dict:
        """
        Consulta CrossRef API para obtener metadatos enriquecidos.
        Retorna un diccionario con campos normalizados.
        """
        try:
            # Consultar CrossRef
            res = self.cr.works(ids=doi)
            message = res.get('message', {})
            
            # Extraer campos de interés
            titles = message.get('title', [])
            title = titles[0] if titles else None
            
            container_titles = message.get('container-title', [])
            journal = container_titles[0] if container_titles else None
            
            # Fecha (issued -> date-parts -> [[2023, 1, 15]])
            issued = message.get('issued', {}).get('date-parts', [])
            year = issued[0][0] if issued and issued[0] else None
            
            # Construir fecha exacta si disponible
            publish_date = None
            if issued and len(issued[0]) >= 3:
                publish_date = f"{issued[0][0]}-{issued[0][1]:02d}-{issued[0][2]:02d}"
            elif issued and len(issued[0]) == 2:
                publish_date = f"{issued[0][0]}-{issued[0][1]:02d}-01"
            
            # Autores
            authors = []
            for auth in message.get('author', []):
                name = f"{auth.get('given', '')} {auth.get('family', '')}".strip()
                if name:
                    authors.append(name)
            
            return {
                "doi": doi,
                "titulo": title,
                "revista": journal,
                "año": year,
                "fecha_publicacion": publish_date,
                "autores": authors,
                # "publisher": message.get('publisher'),
                # "type": message.get('type')
            }
            
        except Exception as e:
            logger.error(f"Error consultando CrossRef para DOI {doi}: {e}")
            return {}
