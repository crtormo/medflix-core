from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from pathlib import Path
from core.analysis import AnalysisCore
from dotenv import load_dotenv

# Cargar variables de entorno al inicio
load_dotenv()

app = FastAPI(title="MedFlix Core API")

# CORS setup (permitir todo por ahora para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Core
# Lo hacemos global para reutilización, aunque pattern 'Depends' sería mejor pro
analysis_core = AnalysisCore()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Welcome to MedFlix Core API"}

@app.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """
    Sube y procesa un paper.
    Retorna el resultado del análisis inmediatamente (sync para MVP, async mejor para prod)
    """
    try:
        file_location = UPLOAD_DIR / file.filename
        
        # Guardar archivo temporalmente
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Procesar
        result = analysis_core.process_and_analyze(str(file_location))
        
        if result["status"] == "duplicate":
            return {
                "status": "duplicate", 
                "message": f"Document already exists. Reason: {result['reason']}",
                "doc_id": result['data']['hash']
            }
            
        return {
            "status": "success",
            "message": "Paper analyzed successfully",
            "doc_id": result["doc_id"],
            "analysis": result["analysis"],
            "snippets": result["snippets"]
        }

    except Exception as e:
        # En producción borrar archivo si falla
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/query")
def query_papers(q: str):
    """Busca papers usando RAG simple"""
    results = analysis_core.vector_store.query_similar(q)
    return results

@app.get("/health")
def health_check():
    return {"status": "ok"}
