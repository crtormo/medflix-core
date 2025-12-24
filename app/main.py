from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
import json
import traceback
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Importar Routers
from app.routers import papers, channels, processing

# Importar Excepciones
from app.exceptions import (
    MedFlixError, 
    PaperNotFoundError, 
    DOIEnrichmentError,
    DatabaseError,
    ExternalServiceError
)

# Cargar variables de entorno
load_dotenv()

# Configurar Logging Estructurado
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = traceback.format_exception(*record.exc_info)
        return json.dumps(log_obj)

# Configurar logger principal
logger = logging.getLogger("medflix")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# Scheduler Global
scheduler = AsyncIOScheduler()

async def scheduled_scan():
    """Tarea programada para escanear canales periódicamente"""
    print("⏰ Ejecutando escaneo programado de Telegram...")
    from services.telegram_ingestor import ChannelIngestor
    ingestor = ChannelIngestor()
    # Usamos un límite razonable para el automático
    await ingestor.run_all() 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando Scheduler...")
    
    # Ejecutar escaneo inmediatamente al iniciar
    import asyncio
    asyncio.create_task(scheduled_scan())
    
    # Programar escaneo cada 12 horas
    scheduler.add_job(scheduled_scan, 'interval', hours=12)
    scheduler.start()
    yield
    # Shutdown
    print("🛑 Deteniendo Scheduler...")
    scheduler.shutdown()

app = FastAPI(title="MedFlix Core API", lifespan=lifespan)

# Configuración Global
# Mount static files (thumbnails)
counts_dir = Path("data/thumbnails")
counts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/thumbnails", StaticFiles(directory="data/thumbnails"), name="thumbnails")

# Mount static files (PDFs)
app.mount("/static/pdfs", StaticFiles(directory="data/uploads"), name="pdfs")
app.mount("/static/uploads_channels", StaticFiles(directory="data/uploads_channels"), name="pdfs_channels")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Exception Handlers ---
@app.exception_handler(PaperNotFoundError)
async def paper_not_found_handler(request: Request, exc: PaperNotFoundError):
    logger.warning(f"Paper no encontrado: {exc.paper_id}")
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(DOIEnrichmentError)
async def doi_enrichment_handler(request: Request, exc: DOIEnrichmentError):
    logger.error(f"Error DOI enrichment: {exc.doi} - {exc.reason}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    logger.error(f"Error de base de datos: {exc.operation}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Error de base de datos. Intente nuevamente.", "code": exc.code}
    )


@app.exception_handler(MedFlixError)
async def medflix_error_handler(request: Request, exc: MedFlixError):
    logger.error(f"MedFlixError: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Error no manejado")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "code": "INTERNAL_ERROR"}
    )


# Incluir Routers
app.include_router(papers.router)
app.include_router(channels.router)
app.include_router(processing.router)


@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MedFlix Core con Arquitectura Modular 🧩"}


@app.get("/health")
def health_check():
    """Health check mejorado que verifica servicios críticos."""
    import os
    from sqlalchemy import create_engine, text
    
    status = {
        "status": "ok",
        "version": "1.0.0",
        "services": {}
    }
    
    # Verificar PostgreSQL
    try:
        user = os.getenv("POSTGRES_USER", "medflix")
        password = os.getenv("POSTGRES_PASSWORD", "medflix_secret")
        host = os.getenv("POSTGRES_HOST", "db")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "medflix_db")
        
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["services"]["postgresql"] = "ok"
    except Exception as e:
        status["services"]["postgresql"] = f"error: {str(e)[:50]}"
        status["status"] = "degraded"
    
    return status

