from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from typing import Dict, List
import shutil
import uuid
from pathlib import Path
from app.dependencies import jobs_db, analysis_core
from app.schemas import UploadResponse, JobStatusResponse

router = APIRouter(
    tags=["processing"]
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
                "analysis": result.get("analysis", ""), 
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

@router.post("/upload", response_model=UploadResponse)
async def upload_paper(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Sube un paper e inicia su procesamiento asíncrono.
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

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
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
