
import os
import sys
import asyncio
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reprocess_papers")

from services.database import get_db_service
from services.metadata_enricher import MetadataService
from services.groq_service import GroqService
from core.analysis import AnalysisCore
import fitz  # PyMuPDF

async def reprocess_all():
    db = get_db_service()
    md_service = MetadataService()
    groq = GroqService()
    
    # Obtener todos los papers (sin limite de paginacion idealmente, pero aqui 1000)
    papers = db.get_all_papers(limit=2000)
    logger.info(f"🔍 Encontrados {len(papers)} papers para revisar.")
    
    processed_count = 0
    renamed_count = 0
    enriched_count = 0
    thumbs_fixed = 0
    
    for paper in papers:
        try:
            logger.info(f"👉 Revisando: {paper.titulo[:50]}... (ID: {paper.id})")
            changes_made = False
            updates = {}
            
            # Contexto del archivo
            current_path = Path(paper.archivo_path)
            
            # 1. FIX THUMBNAILS
            # Verificar si existe el thumbnail físico
            thumb_ok = False
            if paper.thumbnail_path and os.path.exists(paper.thumbnail_path):
                thumb_ok = True
            
            if not thumb_ok and process_thumbnail(paper, current_path):
                 thumbs_fixed += 1
                 # Nota: process_thumbnail ya actualiza la DB o devuelve path? 
                 # Lo haremos manual aqui para ser explícitos
                 pass 

            # 2. ENRIQUECIMIENTO (Abstract, Veredicto)
            # Si falta abstract o veredicto, intentar enriquecer
            if not paper.abstract and paper.doi:
                meta = md_service.get_metadata_by_doi(paper.doi)
                if meta.get('abstract'):
                    updates['abstract'] = meta['abstract']
                    logger.info("   ✅ Abstract encontrado via DOI")
                    enriched_count += 1
            
            # Si no hay veredicto IA y tenemos texto (u acceso al archivo)
            if not paper.veredicto_ia and os.path.exists(current_path):
                # Leer contenido breve
                try:
                    doc = fitz.open(current_path)
                    text = ""
                    for page in doc:
                        text += page.get_text()
                        if len(text) > 15000: break
                    
                    if text:
                        audit = groq.epistemological_audit(text)
                        if audit and isinstance(audit, dict):
                             updates['veredicto_ia'] = audit.get('veredicto_breve')
                             # Si ya que estamos, el score es null, actualizarlo
                             if not paper.score_calidad:
                                 updates['score_calidad'] = audit.get('score_calidad')
                             logger.info(f"   🤖 Veredicto IA generado: {updates.get('veredicto_ia')}")
                except Exception as e:
                    logger.error(f"   Error leyendo PDF para IA: {e}")

            # 3. RENOMBRADO FÍSICO (Si sigue con nombre UUID o raro)
            # Criterio: Si el nombre del archivo contiene números largos o 'doc_' y tenemos un título bueno
            if ("doc_" in paper.archivo_nombre or "-" in paper.archivo_nombre) and paper.titulo:
                 # Generar nombre limpio
                 import re
                 clean_title = re.sub(r'[^a-zA-Z0-9]', '_', paper.titulo)[:60]
                 new_name = f"{clean_title}.pdf"
                 
                 # Solo renombrar si es diferente y no existe ya
                 if new_name != paper.archivo_nombre:
                     dir_path = current_path.parent
                     new_path = dir_path / new_name
                     
                     if current_path.exists() and not new_path.exists():
                         try:
                             os.rename(current_path, new_path)
                             updates['archivo_path'] = str(new_path)
                             updates['archivo_nombre'] = new_name
                             logger.info(f"   ♻️ Renombrado a: {new_name}")
                             renamed_count += 1
                             
                             # Actualizar current_path por si acaso se usa después
                             current_path = new_path 
                         except Exception as e:
                             logger.error(f"   Error renombrando: {e}")

            # Aplicar actualizaciones
            if updates:
                db.update_paper(str(paper.id), **updates)
                processed_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error procesando paper {paper.id}: {e}")

    logger.info("🏁 REPROCESAMIENTO FINALIZADO")
    logger.info(f"   - Papers actualizados en DB: {processed_count}")
    logger.info(f"   - Thumbnails generados: {thumbs_fixed}")
    logger.info(f"   - Archivos renombrados: {renamed_count}")
    logger.info(f"   - Enriquecidos (DOI/IA): {enriched_count}")


def process_thumbnail(paper, pdf_path):
    """Genera thumbnail si el PDF existe."""
    if not pdf_path or not os.path.exists(pdf_path):
        return False
        
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        
        # Nombre hash o basado en ID
        thumb_name = f"thumb_{paper.id}.png"
        thumb_dir = Path("data/thumbnails")
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / thumb_name
        
        pix.save(str(thumb_path))
        
        # Guardar en DB
        from services.database import get_db_service
        db = get_db_service()
        db.update_paper(str(paper.id), thumbnail_path=str(thumb_path))
        logger.info(f"   🖼️ Thumbnail generado: {thumb_name}")
        return True
    except Exception as e:
        logger.error(f"   Error generando thumb: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(reprocess_all())
