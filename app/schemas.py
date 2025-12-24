from pydantic import BaseModel
from typing import Dict, Optional, Any, List

class UploadResponse(BaseModel):
    status: str
    job_id: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # 'procesando', 'completado', 'fallido'
    message: Optional[str] = None
    doc_id: Optional[str] = None
    analysis: Optional[str] = None
    snippets: Optional[Dict[str, Any]] = None
    graficos_analizados: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5

class AnalysisResponse(BaseModel):
    id: str
    content: str
    metadata: Dict
