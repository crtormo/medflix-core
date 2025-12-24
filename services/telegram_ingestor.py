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

    async def ingest_channel(self, channel_data, limit: int = None):
        """Descarga y ANALIZA PDFs de un canal específico usando puntero de DB"""
        channel_username = channel_data.username
        last_id = channel_data.last_scanned_id
        channel_pk = str(channel_data.id)
        
        limit_str = "Infinito" if limit is None else str(limit)
        logger.info(f"📥 Escaneando canal: {channel_username} (Last ID: {last_id}). Límite: {limit_str}")
        
        count = 0
        processed = 0
        max_id_seen = last_id
        
        existing_count = 0
        
        # Inicializar status global
        from services.scan_status import scan_status
        from telethon.errors import FloodWaitError, RPCError
        
        try:
            # Iterar mensajes (desde el más nuevo)
            async for message in self.client.iter_messages(channel_username, limit=limit):
                # Si llegamos a mensajes ya vistos, paramos (si last_id > 0)
                if last_id > 0 and message.id <= last_id:
                    logger.info(f"🛑 {channel_username}: Alcanzado último mensaje visto ({last_id}).")
                    break
                
                # Actualizar max_id para guardar progreso
                if message.id > max_id_seen:
                    max_id_seen = message.id
                
                # Determinar si es PDF o Imagen (para canales ECG)
                is_pdf = message.document and message.file.mime_type == 'application/pdf'
                is_image = message.photo or (message.document and message.file.mime_type and message.file.mime_type.startswith('image/'))
                
                target_file = None
                
                if is_pdf:
                    file_name = message.file.name or f"doc_{message.id}.pdf"
                    target_file = DOWNLOAD_DIR / file_name
                elif is_image:
                    # Solo procesar imágenes si parece ser un canal clínico/ECG (para no bajar memes)
                    # O simplemente bajamos todo de los canales monitoreados.
                    # Vamos a bajar todo y convertir.
                    file_name = f"img_{message.id}.jpg"
                    original_img_path = DOWNLOAD_DIR / file_name
                    target_file = DOWNLOAD_DIR / f"ecg_case_{message.id}.pdf"
                
                if target_file:
                    
                    # Descargar (PDF directo o Imagen->PDF)
                    if not target_file.exists():
                        scan_status.log(f"📥 Detectado contenido: {message.id}...")
                        try:
                            if is_pdf:
                                await message.download_media(file=target_file)
                            elif is_image:
                                # Descargar imagen temporalmente
                                if not original_img_path.exists():
                                    await message.download_media(file=original_img_path)
                                
                                # Convertir a PDF
                                if original_img_path.exists() and original_img_path.stat().st_size > 0:
                                    try:
                                        import img2pdf
                                        with open(target_file, "wb") as f:
                                            f.write(img2pdf.convert(str(original_img_path)))
                                        # Eliminar imagen original para ahorrar espacio
                                        original_img_path.unlink()
                                        scan_status.log(f"🖼️ Convertido a PDF: {target_file.name}")
                                    except ImportError:
                                        # Fallback si no hay img2pdf, usar PIL
                                        from PIL import Image
                                        image = Image.open(original_img_path)
                                        pdf_bytes = image.convert('RGB')
                                        pdf_bytes.save(target_file)
                                        original_img_path.unlink()
                                    except Exception as e:
                                        logger.error(f"Error conversión img->pdf: {e}")
                            
                            # Validar descarga
                            if target_file.exists() and target_file.stat().st_size == 0:
                                logger.error(f"⚠️ Archivo vacío creado: {target_file.name}")
                                target_file.unlink()
                                continue
                                
                            count += 1
                        except FloodWaitError as e:
                            logger.warning(f"⏳ FloodWait: {e.seconds}s")
                            await asyncio.sleep(e.seconds)
                            continue 
                        except Exception as e:
                            logger.error(f"Error descargando: {e}")
                            continue
                    else:
                        pass

                    # PROCESAR CON MEDFLIX CORE
                    if self.core:
                        try:
                            # Ejecutar en thread pool 
                            loop = asyncio.get_running_loop()
                            result = await loop.run_in_executor(
                                None, 
                                self.core.process_and_analyze, 
                                str(target_file)
                            )
                            
                            status = result.get('status')
                            if status == 'success':
                                logger.info(f"✅ Análisis completado: {result.get('doc_id')}")
                                processed += 1
                                scan_status.status["stats"]["nuevos_descargados"] += 1
                            elif status == 'duplicate':
                                 # existing_count += 1 # Opcional contar
                                 scan_status.status["stats"]["duplicados"] += 1
                            else:
                                logger.warning(f"❌ Falló análisis: {result}")
                                scan_status.log(f"❌ Falló análisis {file_name}")
                                scan_status.status["stats"]["errores"] += 1
                                
                        except Exception as e:
                            logger.error(f"Error procesando {file_name}: {e}")
                            scan_status.log(f"❌ Error proceso: {str(e)[:30]}")
                            scan_status.status["stats"]["errores"] += 1
            
            # Al finalizar bucle exitosamente
            logger.info(f"🏁 {channel_username} escaneado correctamente.")

        except FloodWaitError as e:
            logger.critical(f"🚨 FloodWait Global en canal {channel_username}: {e.seconds}s")
            scan_status.log(f"🚨 Límite Global. Pausando {e.seconds}s...")
            await asyncio.sleep(e.seconds)
        except RPCError as e:
            logger.error(f"🚨 Error RPC Telegram en {channel_username}: {e}")
            scan_status.log(f"🚨 Error Telegram: {e}")
        except Exception as e:
            logger.error(f"🚨 Error inesperado en {channel_username}: {e}")
            
        # Actualizar DB con el nuevo puntero solo si hubo progreso
        if max_id_seen > last_id:
            logger.info(f"💾 Actualizando puntero {channel_username} a ID {max_id_seen}")
            self.db.update_channel_scan(channel_pk, max_id_seen)
                    
        logger.info(f"📊 Resumen {channel_username}: Nuevos {processed} | Descargas {count} | Errores {scan_status.status['stats']['errores']}")

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

