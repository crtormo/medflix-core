"""
Fixtures compartidos para tests de MedFlix.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock
import uuid
import os

# Configurar para tests
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "medflix_test"
os.environ["POSTGRES_USER"] = "medflix"
os.environ["POSTGRES_PASSWORD"] = "medflix_secret"


@pytest.fixture
def test_client():
    """Cliente de prueba para la API FastAPI."""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_db_service():
    """Mock del servicio de base de datos."""
    mock = MagicMock()
    mock.get_papers.return_value = []
    mock.get_paper_by_id.return_value = None
    mock.get_stats.return_value = {"total": 0, "procesados": 0}
    return mock


@pytest.fixture
def sample_paper():
    """Paper de ejemplo para tests."""
    return {
        "id": str(uuid.uuid4()),
        "hash": "abc123def456",
        "doi": "10.1001/jama.2019.8430",
        "titulo": "Test Paper Title",
        "autores": ["Dr. Test Author", "Dr. Another Author"],
        "revista": "Test Journal",
        "año": 2023,
        "abstract": "This is a test abstract for the paper.",
        "tipo_estudio": "RCT",
        "especialidad": "Cardiología",
        "tags": ["test", "cardiology"],
        "n_muestra": "1000 pacientes",
        "nnt": "10",
        "poblacion": "Adultos con hipertensión",
        "impact_factor": "50.1",
        "fecha_publicacion_exacta": "2023-05-12",
        "pmid": "12345678",
        "mesh_terms": ["Cardiovascular Diseases", "Hypertension"],
        "abstract_estructurado": {
            "antecedentes": "Background text",
            "metodos": "Methods text",
            "resultados": "Results text",
            "conclusiones": "Conclusions text"
        },
        "affiliaciones": [{"author": "Dr. Test", "institution": "Test Hospital"}],
        "funders": [{"nombre": "NIH", "award": "R01-12345"}],
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "referencias": [],
        "crossmark_status": "current",
        "metadata_source": "pubmed",
        "doi_validado": True,
        "veredicto_ia": "Aprobado",
        "resumen_slide": "Key finding from this study",
        "analisis_completo": "Full analysis text here",
        "score_calidad": 8.5,
        "thumbnail_path": None,
        "imagenes": [],
        "num_graficos": 2,
        "archivo_path": "/data/uploads/test.pdf",
        "archivo_nombre": "test.pdf",
        "num_paginas": 12,
        "fecha_subida": "2023-05-12T10:00:00",
        "fecha_analisis": "2023-05-12T12:00:00",
        "procesado": True,
        "is_quiz": False,
        "quiz_data": {}
    }


@pytest.fixture
def sample_channel():
    """Canal de Telegram de ejemplo."""
    return {
        "id": str(uuid.uuid4()),
        "username": "@test_channel",
        "nombre": "Test Channel",
        "last_scanned_id": 0,
        "last_scan_date": None,
        "active": True
    }
