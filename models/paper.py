"""
Modelos de Base de Datos para MedFlix Core
Usando SQLAlchemy para PostgreSQL
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, Boolean, create_engine
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import os

Base = declarative_base()


class Paper(Base):
    """Modelo completo de paper médico."""
    __tablename__ = 'papers'
    
    # Identificadores
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hash = Column(String(64), unique=True, nullable=False, index=True)
    doi = Column(String(100), index=True)
    
    # Metadatos del Paper
    titulo = Column(Text, nullable=False)
    autores = Column(JSONB, default=list)  # ["Dr. Juan Pérez", "Dra. María López"]
    revista = Column(String(300))
    año = Column(Integer, index=True)
    abstract = Column(Text)
    
    # Clasificación
    tipo_estudio = Column(String(50), index=True)  # RCT, Cohorte, Meta-análisis, etc.
    especialidad = Column(String(100), index=True)  # Cardiología, UCI, Neurología, etc.
    tags = Column(JSONB, default=list)  # ["ventilación", "prono", "SDRA"]
    
    # Datos del Estudio
    n_muestra = Column(String(50))  # "1540 pacientes"
    nnt = Column(String(50))  # Número Necesario a Tratar
    poblacion = Column(String(200))  # Descripción de la población
    
    # Metadatos Enriquecidos (Fase 7)
    impact_factor = Column(String(50)) # Estimado o Manual
    fecha_publicacion_exacta = Column(String(20)) # "2023-05-12"
    
    # Metadatos Multi-Fuente (Fase 8)
    pmid = Column(String(20), index=True)  # PubMed ID
    mesh_terms = Column(JSONB, default=list)  # ["Cardiovascular Diseases", "Biomarkers/blood"]
    abstract_estructurado = Column(JSONB, default=dict)  # {antecedentes, metodos, resultados, conclusiones}
    affiliaciones = Column(JSONB, default=list)  # [{author, institution, country}]
    funders = Column(JSONB, default=list)  # [{name, doi, award}]
    license = Column(String(500))  # URL licencia CC-BY, etc.
    referencias = Column(JSONB, default=list)  # [{doi, key}]
    crossmark_status = Column(String(50))  # current, updated, retracted
    metadata_source = Column(String(50))  # pubmed, crossref, merged
    doi_validado = Column(Boolean, default=False)  # DOI verificado via doi.org
    
    # Análisis IA
    veredicto_ia = Column(String(100)) # "Aprobado", "Evidencia Baja", etc.
    resumen_slide = Column(Text)  # Frase para diapositiva
    analisis_completo = Column(Text)  # Auditoría epistemológica completa
    score_calidad = Column(Float)  # 0-10, calculado de la auditoría
    
    # EKG Dojo / Quiz Mode
    is_quiz = Column(Boolean, default=False, index=True)
    quiz_data = Column(JSONB, default=dict) # {question, options, correct, explanation}
    
    # Imágenes y Gráficos
    thumbnail_path = Column(String(500))  # Ruta a imagen de portada
    imagenes = Column(JSONB, default=list)  # Lista de rutas a imágenes extraídas
    num_graficos = Column(Integer, default=0)
    analisis_graficos = Column(JSONB, default=list)  # Análisis VLM de cada gráfico
    
    # Archivo Original
    archivo_path = Column(String(500))
    archivo_nombre = Column(String(300))
    num_paginas = Column(Integer)
    
    # Timestamps
    fecha_subida = Column(DateTime, default=datetime.utcnow)
    fecha_analisis = Column(DateTime)
    
    # Estado
    procesado = Column(Boolean, default=False)
    
    def to_dict(self):
        """Convierte el modelo a diccionario para APIs."""
        return {
            "id": str(self.id),
            "hash": self.hash,
            "doi": self.doi,
            "titulo": self.titulo,
            "autores": self.autores or [],
            "revista": self.revista,
            "año": self.año,
            "abstract": self.abstract,
            "tipo_estudio": self.tipo_estudio,
            "especialidad": self.especialidad,
            "tags": self.tags or [],
            "n_muestra": self.n_muestra,
            "nnt": self.nnt,
            "poblacion": self.poblacion,
            "impact_factor": self.impact_factor,
            "fecha_publicacion_exacta": self.fecha_publicacion_exacta,
            # Metadatos Multi-Fuente
            "pmid": self.pmid,
            "mesh_terms": self.mesh_terms or [],
            "abstract_estructurado": self.abstract_estructurado or {},
            "affiliaciones": self.affiliaciones or [],
            "funders": self.funders or [],
            "license": self.license,
            "referencias": self.referencias or [],
            "crossmark_status": self.crossmark_status,
            "metadata_source": self.metadata_source,
            "doi_validado": self.doi_validado,
            # Análisis IA
            "veredicto_ia": self.veredicto_ia,
            "resumen_slide": self.resumen_slide,
            "analisis_completo": self.analisis_completo,
            "score_calidad": self.score_calidad,
            "thumbnail_path": self.thumbnail_path,
            "imagenes": self.imagenes or [],
            "num_graficos": self.num_graficos,
            "archivo_path": self.archivo_path,
            "archivo_nombre": self.archivo_nombre,
            "num_paginas": self.num_paginas,
            "fecha_subida": self.fecha_subida.isoformat() if self.fecha_subida else None,
            "fecha_analisis": self.fecha_analisis.isoformat() if self.fecha_analisis else None,
            "procesado": self.procesado,
            "is_quiz": self.is_quiz,
            "quiz_data": self.quiz_data or {}
        }
    
    def to_card_dict(self):
        """Versión reducida para tarjetas del catálogo Netflix."""
        return {
            "id": str(self.id),
            "titulo": self.titulo,
            "autores": self.autores[:2] if self.autores else [],  # Solo primeros 2
            "año": self.año,
            "tipo_estudio": self.tipo_estudio,
            "especialidad": self.especialidad,
            "n_muestra": self.n_muestra,
            "score_calidad": self.score_calidad,
            "thumbnail_path": self.thumbnail_path,
            "resumen_slide": self.resumen_slide
        }


def get_database_url():
    """Obtiene URL de conexión a PostgreSQL desde variables de entorno."""
    user = os.getenv("POSTGRES_USER", "medflix")
    password = os.getenv("POSTGRES_PASSWORD", "medflix_secret")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "medflix_db")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def init_db():
    """Inicializa la base de datos y crea las tablas."""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Crea una sesión de base de datos."""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()
