"""
Servicio de Enriquecimiento de Metadatos para Libros
Usa OpenLibrary (principal) y Google Books (fallback) para obtener:
- Portadas
- ISBN, editorial, edición
- Descripción, idioma
"""

import requests
import re
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class BookMetadataEnricher:
    """Enriquece metadatos de libros usando APIs públicas."""
    
    OPENLIBRARY_SEARCH = "https://openlibrary.org/search.json"
    OPENLIBRARY_ISBN = "https://openlibrary.org/isbn/{isbn}.json"
    OPENLIBRARY_COVERS = "https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"
    GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"
    
    def __init__(self, covers_dir: str = "data/covers"):
        self.covers_dir = Path(covers_dir)
        self.covers_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_isbn_from_text(self, text: str) -> Optional[str]:
        """Extrae ISBN del texto de un PDF."""
        # ISBN-13: 978-X-XXX-XXXXX-X o 9780000000000
        # ISBN-10: X-XXX-XXXXX-X
        patterns = [
            r'ISBN[-:\s]*(?:13)?[-:\s]*(97[89][-\s]?\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,6}[-\s]?\d)',
            r'ISBN[-:\s]*(?:10)?[-:\s]*(\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,6}[-\s]?[\dX])',
            r'(97[89]\d{10})',  # ISBN-13 sin guiones
            r'(\d{9}[\dX])',    # ISBN-10 sin guiones
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                isbn = re.sub(r'[-\s]', '', match.group(1))
                return isbn
        return None
    
    def enrich_by_isbn(self, isbn: str) -> Dict[str, Any]:
        """Busca metadatos por ISBN en OpenLibrary y Google Books."""
        isbn = re.sub(r'[-\s]', '', isbn)  # Limpiar ISBN
        
        result = self._search_openlibrary_isbn(isbn)
        if not result or not result.get('titulo'):
            result = self._search_google_books(f"isbn:{isbn}")
        
        if result:
            # Descargar portada
            cover_path = self._download_cover(isbn, result.get('cover_url'))
            if cover_path:
                result['cover_path'] = str(cover_path)
        
        return result or {}
    
    def enrich_by_title(self, title: str, author: str = None) -> Dict[str, Any]:
        """Busca metadatos por título y autor."""
        result = self._search_openlibrary_title(title, author)
        
        if not result or not result.get('titulo'):
            query = f"{title} {author}" if author else title
            result = self._search_google_books(query)
        
        if result and result.get('isbn'):
            cover_path = self._download_cover(result['isbn'], result.get('cover_url'))
            if cover_path:
                result['cover_path'] = str(cover_path)
        
        return result or {}
    
    def _search_openlibrary_isbn(self, isbn: str) -> Optional[Dict]:
        """Busca en OpenLibrary por ISBN."""
        try:
            url = self.OPENLIBRARY_ISBN.format(isbn=isbn)
            res = requests.get(url, timeout=10)
            
            if res.status_code != 200:
                return None
            
            data = res.json()
            
            # Obtener más detalles del work
            work_key = data.get('works', [{}])[0].get('key', '')
            
            return {
                'isbn': isbn,
                'titulo': data.get('title'),
                'editorial': ', '.join(data.get('publishers', [])),
                'edicion': data.get('edition_name'),
                'idioma': ', '.join(data.get('languages', [{}])[0].get('key', '').split('/')[-1:]),
                'num_paginas': data.get('number_of_pages'),
                'cover_url': self.OPENLIBRARY_COVERS.format(isbn=isbn, size='L'),
                'open_library_id': data.get('key', '').split('/')[-1],
                'metadata_source': 'openlibrary'
            }
        except Exception as e:
            logger.error(f"Error OpenLibrary ISBN: {e}")
            return None
    
    def _search_openlibrary_title(self, title: str, author: str = None) -> Optional[Dict]:
        """Busca en OpenLibrary por título."""
        try:
            params = {'title': title, 'limit': 1}
            if author:
                params['author'] = author
            
            res = requests.get(self.OPENLIBRARY_SEARCH, params=params, timeout=10)
            
            if res.status_code != 200:
                return None
            
            data = res.json()
            docs = data.get('docs', [])
            
            if not docs:
                return None
            
            book = docs[0]
            isbn = book.get('isbn', [''])[0] if book.get('isbn') else None
            
            return {
                'isbn': isbn,
                'titulo': book.get('title'),
                'autores': book.get('author_name', []),
                'editorial': ', '.join(book.get('publisher', [])[:2]),
                'año': book.get('first_publish_year'),
                'idioma': ', '.join(book.get('language', [])[:2]),
                'cover_url': f"https://covers.openlibrary.org/b/olid/{book.get('cover_edition_key')}-L.jpg" if book.get('cover_edition_key') else None,
                'open_library_id': book.get('key', '').split('/')[-1],
                'metadata_source': 'openlibrary'
            }
        except Exception as e:
            logger.error(f"Error OpenLibrary Title: {e}")
            return None
    
    def _search_google_books(self, query: str) -> Optional[Dict]:
        """Busca en Google Books API."""
        try:
            params = {'q': query, 'maxResults': 1}
            res = requests.get(self.GOOGLE_BOOKS_API, params=params, timeout=10)
            
            if res.status_code != 200:
                return None
            
            data = res.json()
            items = data.get('items', [])
            
            if not items:
                return None
            
            vol = items[0].get('volumeInfo', {})
            
            # Extraer ISBN
            identifiers = vol.get('industryIdentifiers', [])
            isbn = None
            for ident in identifiers:
                if ident.get('type') in ['ISBN_13', 'ISBN_10']:
                    isbn = ident.get('identifier')
                    break
            
            # Obtener mejor imagen disponible
            images = vol.get('imageLinks', {})
            cover_url = images.get('extraLarge') or images.get('large') or images.get('medium') or images.get('thumbnail')
            
            return {
                'isbn': isbn,
                'titulo': vol.get('title'),
                'autores': vol.get('authors', []),
                'editorial': vol.get('publisher'),
                'año': int(vol.get('publishedDate', '0')[:4]) if vol.get('publishedDate') else None,
                'descripcion_libro': vol.get('description'),
                'num_paginas': vol.get('pageCount'),
                'idioma': vol.get('language'),
                'cover_url': cover_url,
                'metadata_source': 'google_books'
            }
        except Exception as e:
            logger.error(f"Error Google Books: {e}")
            return None
    
    def _download_cover(self, isbn: str, cover_url: str) -> Optional[Path]:
        """Descarga y guarda la portada localmente."""
        if not cover_url:
            return None
        
        try:
            res = requests.get(cover_url, timeout=15)
            if res.status_code != 200 or len(res.content) < 1000:  # Imagen vacía
                return None
            
            # Guardar imagen
            ext = 'jpg'
            if 'png' in cover_url.lower():
                ext = 'png'
            
            cover_path = self.covers_dir / f"cover_{isbn}.{ext}"
            with open(cover_path, 'wb') as f:
                f.write(res.content)
            
            logger.info(f"✅ Portada descargada: {cover_path}")
            return cover_path
        except Exception as e:
            logger.error(f"Error descargando portada: {e}")
            return None
    
    def get_cover_url(self, isbn: str, size: str = 'M') -> str:
        """Genera URL de portada de OpenLibrary."""
        return self.OPENLIBRARY_COVERS.format(isbn=isbn, size=size.upper())


def get_book_enricher() -> BookMetadataEnricher:
    """Factory function para obtener el enriquecedor."""
    return BookMetadataEnricher()
