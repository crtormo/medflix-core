from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Optional
from services.database import get_db_service
from services.telegram_ingestor import ChannelIngestor
import services.scan_status as scan_status_module

router = APIRouter(
    tags=["channels"]
)

# Rutas originales en main.py: /channels, /channels/{username}, /scan-channels, /scan-status
# No hay prefix común claro excepto /channels. Pero scan-channels es distinto.
# Usaremos router sin prefix para mayor flexibilidad y compatibilidad.

@router.get("/channels", response_model=List[Dict])
def list_channels():
    """Lista todos los canales monitoreados."""
    return [ch.to_dict() for ch in get_db_service().get_all_channels()]

@router.post("/channels")
def add_channel(username: str, nombre: Optional[str] = None):
    """Añade un nuevo canal."""
    if not username.startswith("@"):
        raise HTTPException(status_code=400, detail="El username debe empezar con @")
    
    ch = get_db_service().add_channel(username, nombre)
    return ch.to_dict()

@router.delete("/channels/{username}")
def delete_channel(username: str):
    """Elimina (desactiva) un canal."""
    get_db_service().delete_channel(username)
    return {"status": "ok", "message": f"Canal {username} desactivado"}

@router.post("/scan-channels")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Inicia el escaneo de canales en segundo plano."""
    
    async def run_scan():
        try:
            ingestor = ChannelIngestor()
            await ingestor.run_all()
        except Exception as e:
            print(f"Error en escaneo manual: {e}")
            
    background_tasks.add_task(run_scan)
    return {"status": "started", "message": "Escaneo de canales iniciado en segundo plano"}

@router.get("/scan-status")
def get_scan_status():
    """Retorna el estado actual del escaneo de canales."""
    return scan_status_module.scan_status.status
