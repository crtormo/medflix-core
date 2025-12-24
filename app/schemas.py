"""
Pydantic Schemas para request/response de la API MedFlix.
Proporciona validación automática y documentación OpenAPI.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional, Any, List
from datetime import datetime
import re


# --- Schemas Existentes ---

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


# --- Paper Schemas ---

class PaperBase(BaseModel):
    """Campos base compartidos."""
    titulo: str = Field(..., min_length=1, max_length=1000)
    autores: Optional[List[str]] = Field(default_factory=list)
    revista: Optional[str] = Field(None, max_length=300)
    año: Optional[int] = Field(None, ge=1900, le=2100)
    abstract: Optional[str] = None
    doi: Optional[str] = Field(None, max_length=100)
    
    @field_validator('doi')
    @classmethod
    def validate_doi_format(cls, v):
        if v and not re.match(r'^10\.\d{4,}/', v):
            raise ValueError('DOI debe comenzar con 10.xxxx/')
        return v


class PaperUpdate(BaseModel):
    """Schema para actualizar un paper."""
    titulo: Optional[str] = Field(None, min_length=1, max_length=1000)
    autores: Optional[List[str]] = None
    revista: Optional[str] = Field(None, max_length=300)
    año: Optional[int] = Field(None, ge=1900, le=2100)
    abstract: Optional[str] = None
    doi: Optional[str] = Field(None, max_length=100)
    tipo_estudio: Optional[str] = Field(None, max_length=50)
    especialidad: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None


class PaperResponse(PaperBase):
    """Schema de respuesta para un paper."""
    id: str
    hash: str
    tipo_estudio: Optional[str] = None
    especialidad: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    pmid: Optional[str] = None
    mesh_terms: List[str] = Field(default_factory=list)
    doi_validado: bool = False
    metadata_source: Optional[str] = None
    veredicto_ia: Optional[str] = None
    resumen_slide: Optional[str] = None
    score_calidad: Optional[float] = Field(None, ge=0, le=10)
    archivo_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    procesado: bool = False
    
    class Config:
        from_attributes = True


class PaperCard(BaseModel):
    """Schema reducido para tarjetas."""
    id: str
    titulo: str
    autores: List[str] = Field(default_factory=list)
    año: Optional[int] = None
    tipo_estudio: Optional[str] = None
    especialidad: Optional[str] = None
    score_calidad: Optional[float] = None
    thumbnail_path: Optional[str] = None


# --- DOI Enrichment ---

class DOIEnrichRequest(BaseModel):
    """Request para enriquecer via DOI."""
    doi: Optional[str] = None


class DOIEnrichResponse(BaseModel):
    """Response del enriquecimiento."""
    mensaje: str
    doi_validado: bool
    campos_actualizados: List[str] = Field(default_factory=list)


# --- Channel Schemas ---

class ChannelCreate(BaseModel):
    """Schema para crear canal."""
    username: str = Field(..., min_length=1, max_length=100)
    nombre: Optional[str] = Field(None, max_length=200)


class ChannelResponse(BaseModel):
    """Response de canal."""
    id: str
    username: str
    nombre: Optional[str] = None
    last_scanned_id: int = 0
    last_scan_date: Optional[datetime] = None
    active: bool = True


# --- Stats & Health ---

class StatsResponse(BaseModel):
    """Estadísticas del sistema."""
    total: int = 0
    procesados: int = 0
    especialidades_breakdown: Dict[str, int] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    services: Dict[str, str] = Field(default_factory=dict)


# --- Chat ---

class ChatRequest(BaseModel):
    """Request para chat."""
    question: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Response del chat."""
    answer: str
    sources: List[str] = Field(default_factory=list)
