from pydantic import BaseModel
from typing import Dict, Optional, Any

class UploadResponse(BaseModel):
    status: str
    doc_id: Optional[str] = None
    message: str
    analysis: Optional[str] = None
    snippets: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5

class AnalysisResponse(BaseModel):
    id: str
    content: str
    metadata: Dict
