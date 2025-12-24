
import os
import asyncio
from pathlib import Path
from services.database import get_db_service
from core.analysis import AnalysisCore
import logging

# Configuración de Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def scan_local_files():
    """Escanea y procesa archivos existentes en data/uploads_channels"""
    db = get_db_service()
    core = AnalysisCore()
    
    target_dir = Path("data/uploads_channels")
    if not target_dir.exists():
        logger.error(f"El directorio {target_dir} no existe.")
        return

    logger.info(f"📂 Escaneando directorio: {target_dir}")
    
    pdf_files = list(target_dir.glob("*.pdf"))
    logger.info(f"Encontrados {len(pdf_files)} archivos PDF.")
    
    processed_count = 0
    duplicate_count = 0
    error_count = 0

    for file_path in pdf_files:
        try:
            logger.info(f"🧠 Procesando: {file_path.name}...")
            
            # Ejecutar análisis (usando thread pool porque AnalysisCore puede ser bloqueante)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                core.process_and_analyze, 
                str(file_path)
            )
            
            status = result.get('status')
            if status == 'success':
                logger.info(f"✅ Éxito: {result.get('doc_id')}")
                processed_count += 1
            elif status == 'duplicate':
                logger.info(f"⚠️ Duplicado: {result.get('reason')}")
                duplicate_count += 1
            else:
                logger.warning(f"❌ Fallo: {result}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Error crítico con {file_path.name}: {e}")
            error_count += 1
            
    logger.info(f"🏁 Resumen: Procesados {processed_count} | Duplicados {duplicate_count} | Errores {error_count}")

if __name__ == "__main__":
    asyncio.run(scan_local_files())
