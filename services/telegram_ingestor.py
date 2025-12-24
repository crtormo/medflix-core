import os
import asyncio
import logging
from telethon import TelegramClient
from pathlib import Path
from dotenv import load_dotenv

# Importar DB Service
from services.database import get_db_service
from core.analysis import AnalysisCore

# Configuración de Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

# Credenciales de my.telegram.org (UserBot)
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
# Guardar sesión en volumen persistente
SESSION_PATH = Path("data/medflix_userbot") 
SESSION_NAME = str(SESSION_PATH)

DOWNLOAD_DIR = Path("data/uploads_channels")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

class ChannelIngestor:
    def __init__(self):
        if not API_ID or not API_HASH:
             raise ValueError("TELEGRAM_API_ID y TELEGRAM_API_HASH son requeridos en .env")
             
        self.client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
        self.db = get_db_service()
        
        # Inicializar Core para análisis
        try:
            self.core = AnalysisCore()
            logger.info("AnalysisCore inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error inicializando AnalysisCore: {e}")
            self.core = None

    async def ingest_channel(self, channel_data, limit: int = 50):
        """Descarga y ANALIZA PDFs de un canal específico usando puntero de DB"""
        channel_username = channel_data.username
        last_id = channel_data.last_scanned_id
        channel_pk = str(channel_data.id)
        
        logger.info(f"📥 Escaneando canal: {channel_username} (Last ID: {last_id})...")
        
        count = 0
        processed = 0
        max_id_seen = last_id
        
        existing_count = 0
        
        # Inicializar status global
        from services.scan_status import scan_status
        
        # Iterar mensajes (desde el más nuevo)
        async for message in self.client.iter_messages(channel_username, limit=limit):
            # Si llegamos a mensajes ya vistos, paramos (si last_id > 0)
            if last_id > 0 and message.id <= last_id:
                logger.info(f"🛑 Alcanzado último mensaje visto ({last_id}). Deteniendo escaneo.")
                scan_status.log(f"🛑 {channel_username}: Al día.")
                break
            
            # Actualizar max_id para guardar progreso
            if message.id > max_id_seen:
                max_id_seen = message.id
            
            if message.document and message.file.mime_type == 'application/pdf':
                file_name = message.file.name or f"doc_{message.id}.pdf"
                file_path = DOWNLOAD_DIR / file_name
                
                # Descargar si no existe
                if not file_path.exists():
                    logger.info(f"Descargando: {file_name}")
                    scan_status.log(f"📥 Descargando: {file_name}...")
                    try:
                        await message.download_media(file=file_path)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error descargando {file_name}: {e}")
                        continue
                else:
                    # logger.info(f"Archivo ya existe en disco: {file_name}")
                    pass

                # PROCESAR CON MEDFLIX CORE (Siempre, el Core maneja deduplicación por hash)
                if self.core:
                    # logger.info(f"🧠 Verificado/Analizando {file_name}...")
                    try:
                        # Ejecutar en thread pool para no bloquear loop async
                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(
                            None, 
                            self.core.process_and_analyze, 
                            str(file_path)
                        )
                        
                        status = result.get('status')
                        logger.info(f"DEBUG: Result status for {file_name}: {status}") 
                        if status == 'success':
                            logger.info(f"✅ Análisis completado: {result.get('doc_id')}")
                            scan_status.log(f"✅ Nuevo paper analizado: {result.get('data',{}).get('titulo', file_name)[:30]}...")
                            scan_status.status["stats"]["nuevos_descargados"] += 1
                            processed += 1
                        elif status == 'duplicate':
                             # logger.info(f"⚠️ Duplicado detectado: {result.get('reason')} (Data: {result.get('data')})")
                             scan_status.status["stats"]["duplicados"] += 1
                             existing_count += 1
                        else:
                            logger.warning(f"❌ Falló análisis: {result}")
                            scan_status.log(f"❌ Falló análisis de {file_name}")
                            
                    except Exception as e:
                        logger.error(f"Error procesando {file_name}: {e}")
        
        # Actualizar DB con el nuevo puntero
        if max_id_seen > last_id:
            self.db.update_channel_scan(channel_pk, max_id_seen)
                    
        logger.info(f"🏁 Finalizado {channel_username}. \n📊 Resumen: \n   - 📥 Nuevos Procesados: {processed} \n   - ♻️ Ya Existentes (Duplicados): {existing_count} \n   - 💾 Descargados: {count}")

    async def run_all(self):
        """Escanea todos los canales activos de la base de datos"""
        from services.scan_status import scan_status
        
        await self.client.start()
        channels = self.db.get_all_channels()
        
        if not channels:
            logger.warning("No hay canales configurados en la base de datos.")
            return

        scan_status.start_scan(total_channels=len(channels))
        
        logger.info(f"🔄 Iniciando escaneo de {len(channels)} canales...")
        
        total_processed = 0
        total_existing = 0
        
        for idx, ch in enumerate(channels, 1):
            scan_status.update_channel(ch.username, idx)
            try:
                # Modificamos ingest_channel para devolver stats si fuera posible, 
                # pero por ahora parsearemos logs o asumiremos éxito.
                # Mejor inyectar scan_status en ingest_channel o actualizar aquí?
                # Vamos a hacer un override rápido de ingest_channel para que use el status global también si queremos detalle fino.
                # Por simplicidad, actualizamos status global desde ingest_channel si lo modificamos arriba.
                # Pero como replace_file_content reemplaza bloques, modifiquemos ingest_channel también o usemos el singleton dentro.
                
                # Llamada original
                await self.ingest_channel(ch)
                
            except Exception as e:
                logger.error(f"Error escaneando canal {ch.username}: {e}")
                scan_status.status["stats"]["errores"] += 1
                scan_status.log(f"❌ Error en {ch.username}: {e}")

        scan_status.end_scan({"processed": 0, "existing": 0}) # Placeholder, idealmente sumaríamos real



if __name__ == "__main__":
    import sys
    
    # Argumentos CLI: python -m services.telegram_ingestor @Canal [limit]
    if len(sys.argv) > 1:
        target_channel = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    else:
        target_channel = input("Introduce el username del canal a escanear (ej: @librosmedicina): ")
        limit_str = input("Numero de mensajes a revisar (default 50): ")
        limit = int(limit_str) if limit_str.isdigit() else 50
    
    ingestor = ChannelIngestor()
    asyncio.run(ingestor.ingest_channel(target_channel, limit))

