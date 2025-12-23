import os
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Credenciales de my.telegram.org (UserBot)
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = 'medflix_userbot_session'

if not API_ID or not API_HASH:
    print("Error: TELEGRAM_API_ID or TELEGRAM_API_HASH missing in .env")
    # No salimos aqui para permitir importar la clase y ver el error despues si se instancia
    
DOWNLOAD_DIR = Path("data/uploads_channels")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

class ChannelIngestor:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    async def ingest_channel(self, channel_username: str, limit: int = 50):
        """Descarga PDFs de un canal especifico"""
        await self.client.start()
        
        print(f"📥 Scaneando canal: {channel_username}...")
        
        count = 0
        async for message in self.client.iter_messages(channel_username, limit=limit):
            if message.document and message.file.mime_type == 'application/pdf':
                file_name = message.file.name or f"doc_{message.id}.pdf"
                file_path = DOWNLOAD_DIR / file_name
                
                # Check si ya existe (simple check de nombre por ahora, el hash check real lo hace el ingestion service despues)
                if not file_path.exists():
                    print(f"Descargando: {file_name}")
                    await message.download_media(file=file_path)
                    count += 1
                else:
                    print(f"Skipping {file_name}, existe en disco local.")
                    
        print(f"✅ Descarga completada. {count} nuevos archivos en {DOWNLOAD_DIR}")
        print("💡 Nota: Ejecuta el proceso de 'Ingesta masiva' (pendiente) para analizarlos en MedFlix.")

if __name__ == "__main__":
    import sys
    
    if not API_ID:
        print("❌ Configura TELEGRAM_API_ID y TELEGRAM_API_HASH en .env primero.")
        exit(1)
        
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
