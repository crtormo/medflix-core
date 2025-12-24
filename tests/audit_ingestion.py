
import os
import sys
import logging
from pathlib import Path
from services.database import get_db_service
from core.analysis import AnalysisCore
from pprint import pprint

# Configurar logging a stdout
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("audit_ingestion")

def audit_single_file(filename: str):
    base_path = Path("/app/data/uploads_channels")
    file_path = base_path / filename
    
    if not file_path.exists():
        logger.error(f"Archivo no encontrado: {file_path}")
        return

    logger.info(f"=== AUDITORÍA DE INGESTA: {filename} ===")
    
    # 1. Auditoría OCR / Extracción
    logger.info("--- PASO 1: Extracción de Texto ---")
    core = AnalysisCore()
    
    try:
        # Usamos métodos internos de ingestion para ver el raw data
        doc_data = core.ingestion.process_pdf(file_path)
        
        raw_text = doc_data.get('content', '')
        logger.info(f"Longitud del texto extraído: {len(raw_text)} caracteres")
        logger.info(f"Muestra del texto (primeros 500 chars):\n{raw_text[:500]}...")
        
        if len(raw_text) < 100:
            logger.warning("ALERTA: Texto extraído muy corto. Posible PDF escaneado sin OCR o protegido.")
            
        logger.info(f"Metadatos extraídos: Hash={doc_data.get('hash')}, Páginas={doc_data.get('page_count')}")
        
    except Exception as e:
        logger.error(f"FALLO EXTRACTOR: {e}")
        return

    # 2. Auditoría de Duplicados DB
    logger.info("\n--- PASO 2: Verificación de Duplicados ---")
    db = get_db_service()
    existing = db.get_paper_by_hash(doc_data['hash'])
    if existing:
        logger.warning(f"Paper ya existe en DB (ID: {existing.id}, Title: {existing.titulo}, Procesado: {existing.procesado})")
    else:
        logger.info("Paper no existe en DB. Procediendo a crear.")

    # 3. Auditoría de Análisis IA
    logger.info("\n--- PASO 3: Ejecución de AnalysisCore (Procesamiento) ---")
    try:
        # Forzar análisis aunque exista (bypass duplicate check del script, pero AnalysisCore lo chequeará internamente)
        # Nota: AnalysisCore.process_and_analyze retorna {status: duplicate} si ya existe.
        result = core.process_and_analyze(str(file_path))
        logger.info(f"Resultado AnalysisCore: {result.get('status')}")
        
        if result.get('status') == 'success':
            job_id = result.get('job_id')
            logger.info(f"Paper procesado exitosamente. Job ID: {job_id}")
            
            # 4. Verificación de Persistencia Final
            logger.info("\n--- PASO 4: Verificación Post-Procesamiento en DB ---")
            paper_final = db.get_paper_by_id(job_id)
            if paper_final:
                logger.info("PERSISTENCIA CONFIRMADA.")
                logger.info(f"Título Final: {paper_final.titulo}")
                logger.info(f"Score Calidad: {paper_final.score_calidad}")
                logger.info(f"Especialidad: {paper_final.especialidad}")
                logger.info(f"Resumen Slide: {paper_final.resumen_slide}")
            else:
                logger.error("CRÍTICO: El paper se reportó como success pero NO aparece en la DB.")
        
        elif result.get('status') == 'duplicate':
            logger.info("Core detectó duplicado correctamente.")
            
    except Exception as e:
        logger.error(f"FALLO EN ANALYSIS CORE: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tests/audit_ingestion.py <nombre_archivo_en_uploads_channels>")
        print("Ejemplo: python tests/audit_ingestion.py paper1.pdf")
    else:
        audit_single_file(sys.argv[1])
