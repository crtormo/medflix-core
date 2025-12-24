from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from typing import Dict, List, Optional
from pathlib import Path
from core.analysis import AnalysisCore
from services.reference_generator import ReferenceGenerator
from dotenv import load_dotenv
from .schemas import UploadResponse, JobStatusResponse

# Cargar variables de entorno al inicio
load_dotenv()

app = FastAPI(title="MedFlix Core API")

# Mount static files (thumbnails)
# Asegurar que el directorio existe
counts_dir = Path("data/thumbnails")
counts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/thumbnails", StaticFiles(directory="data/thumbnails"), name="thumbnails")

# CORS setup (permitir todo por ahora para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Core y servicios
analysis_core = AnalysisCore()
reference_generator = ReferenceGenerator()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Memoria simple de Jobs (en prod usar Redis/DB)
# Estructura: job_id -> {status, result, message}
jobs_db: Dict[str, Dict] = {}

def process_file_task(job_id: str, file_path: str):
    """Tarea en segundo plano para procesar el paper"""
    try:
        jobs_db[job_id]["status"] = "procesando"
        
        # Procesar
        result = analysis_core.process_and_analyze(file_path)
        
        if result["status"] == "duplicate":
            jobs_db[job_id]["status"] = "completado"
            jobs_db[job_id]["result"] = {
                "status": "duplicate",
                "message": f"Documento duplicado. Razón: {result['reason']}",
                "doc_id": result['data']['hash'],
                "analysis": result.get("analysis", ""), # A veces se quiere re-ver
                "snippets": result.get("snippets", {})
            }
        else:
            jobs_db[job_id]["status"] = "completado"
            jobs_db[job_id]["result"] = {
                "status": "success", 
                "message": "Análisis completado exitosamente",
                "doc_id": result["doc_id"],
                "analysis": result["analysis"],
                "snippets": result["snippets"],
                "graficos_analizados": result.get("graficos_analizados", []),
                "metadata": result.get("metadata", {})
            }
            
    except Exception as e:
        jobs_db[job_id]["status"] = "fallido"
        jobs_db[job_id]["message"] = str(e)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MedFlix Core"}

@app.post("/upload", response_model=UploadResponse)
async def upload_paper(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Sube un paper e inicia su procesamiento asíncrono.
    Retorna un ID de trabajo (job_id) para consultar el estado.
    """
    try:
        job_id = str(uuid.uuid4())
        file_location = UPLOAD_DIR / f"{job_id}_{file.filename}"
        
        # Guardar archivo
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Inicializar job
        jobs_db[job_id] = {
            "status": "pendiente",
            "message": "Iniciando procesamiento...",
            "result": None
        }
        
        # Lanzar tarea background
        background_tasks.add_task(process_file_task, job_id, str(file_location))
        
        return {
            "status": "pendiente",
            "job_id": job_id,
            "message": "Archivo recibido. Procesamiento iniciado."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir archivo: {str(e)}")

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """Consulta el estado del trabajo de análisis."""
    job = jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "message": job.get("message")
    }
    
    if job["status"] == "completado" and job["result"]:
        res = job["result"]
        response.update({
             "doc_id": res.get("doc_id"),
             "analysis": res.get("analysis"),
             "snippets": res.get("snippets"),
             "message": res.get("message")
        })
    
    return response

@app.get("/query")
def query_papers(q: str):
    """Busca papers usando RAG simple"""
    results = analysis_core.vector_store.query_similar(q)
    return results

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/papers", response_model=List[Dict])
async def list_papers(
    limit: int = 20, 
    offset: int = 0,
    specialty: Optional[str] = None,
    sort: Optional[str] = "recent"
):
    """Lista papers para el catálogo."""
    # Instanciar servicio DB directamente si no lo tiene el Core expuesto
    from services.database import get_db_service
    db = get_db_service()
    
    if specialty and specialty != "Todas":
        papers = db.get_papers_by_especialidad(specialty, limit)
    elif sort == "quality":
        papers = db.get_top_papers(limit)
    else:
        papers = db.get_recent_papers(limit)
        
    return [p.to_card_dict() for p in papers]

@app.get("/papers/{paper_id}", response_model=Dict)
def get_paper_details(paper_id: str):
    """Obtiene los detalles completos de un paper."""
    from services.database import get_db_service
    db = get_db_service()
    paper = db.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    return paper.to_dict()

@app.get("/stats")
async def get_stats():
    from services.database import get_db_service
    return get_db_service().get_stats()

@app.get("/channels", response_model=List[Dict])
def list_channels():
    """Lista todos los canales monitoreados."""
    from services.database import get_db_service
    return [ch.to_dict() for ch in get_db_service().get_all_channels()]

@app.post("/channels")
def add_channel(username: str, nombre: Optional[str] = None):
    """Añade un nuevo canal."""
    from services.database import get_db_service
    if not username.startswith("@"):
        raise HTTPException(status_code=400, detail="El username debe empezar con @")
    
    ch = get_db_service().add_channel(username, nombre)
    return ch.to_dict()

@app.delete("/channels/{username}")
def delete_channel(username: str):
    """Elimina (desactiva) un canal."""
    from services.database import get_db_service
    get_db_service().delete_channel(username)
    return {"status": "ok", "message": f"Canal {username} desactivado"}

@app.post("/scan-channels")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Inicia el escaneo de canales en segundo plano."""
    from services.telegram_ingestor import ChannelIngestor
    
    async def run_scan():
        try:
            ingestor = ChannelIngestor()
            await ingestor.run_all()
        except Exception as e:
            print(f"Error en escaneo manual: {e}")
            
    background_tasks.add_task(run_scan)
    background_tasks.add_task(run_scan)
    return {"status": "started", "message": "Escaneo de canales iniciado en segundo plano"}

@app.get("/scan-status")
def get_scan_status():
    """Retorna el estado actual del escaneo de canales."""
    from services.scan_status import scan_status
    return scan_status.status

@app.get("/citar/{doc_id}")
def generate_citation(doc_id: str, style: str = "vancouver"):


    """
    Genera una cita formateada para un documento.
    Estilos disponibles: vancouver, apa
    """
    # Buscar documento en vector store
    results = analysis_core.vector_store.collection.get(ids=[doc_id])
    
    if not results['ids']:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    metadata = results['metadatas'][0] if results['metadatas'] else {}
    
    citation = reference_generator.generate_citation(metadata, style=style)
    
    return {
        "doc_id": doc_id,
        "estilo": style,
        "cita": citation
    }

# --- Nuevos Endpoints Fase 2 (UI Revamp) ---

# Mount static files (PDFs)
# Nota: Esto expone todos los PDFs públicamente sin auth (según plan aceptado)
app.mount("/static/pdfs", StaticFiles(directory="data/uploads"), name="pdfs")
app.mount("/static/uploads_channels", StaticFiles(directory="data/uploads_channels"), name="pdfs_channels")


@app.post("/chat/{paper_id}")
async def chat_paper(paper_id: str, payload: Dict[str, str]):
    """
    Endpoint para chatear con un paper específico.
    Payload: {"question": "¿Cuál es la conclusión?"}
    """
    question = payload.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Falta la pregunta")
        
    answer = analysis_core.chat_with_paper(paper_id, question)
    return {"answer": answer}

@app.put("/papers/{paper_id}")
async def update_paper_metadata(paper_id: str, updates: Dict):
    """
    Actualiza metadatos de un paper manualmente.
    """
    from services.database import get_db_service
    db = get_db_service()
    
    try:
        # Extraer campos permitidos
        valid_fields = ["titulo", "autores", "año", "especialidad", "tipo_estudio"]
        clean_updates = {k: v for k, v in updates.items() if k in valid_fields}
        
        paper = db.update_paper(paper_id, **clean_updates)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper no encontrado")
            
        return paper.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
