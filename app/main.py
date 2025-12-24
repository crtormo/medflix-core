from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Importar Routers
from app.routers import papers, channels, processing

# Cargar variables de entorno
load_dotenv()

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
    scheduler.add_job(scheduled_scan, 'interval', hours=6) # Cada 6 horas
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

# Incluir Routers
app.include_router(papers.router)
app.include_router(channels.router)
app.include_router(processing.router)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MedFlix Core con Arquitectura Modular 🧩"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
