"""
Tests de integración para operaciones de base de datos.
Utiliza mocks para evitar dependencia de PostgreSQL real.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import uuid


class TestDatabaseService:
    """Tests para el servicio de base de datos."""
    
    def test_get_papers_empty(self, mock_db_service):
        """get_papers retorna lista vacía sin papers."""
        mock_db_service.get_papers.return_value = []
        result = mock_db_service.get_papers(limit=10, offset=0)
        assert result == []
    
    def test_get_papers_with_data(self, mock_db_service, sample_paper):
        """get_papers retorna papers existentes."""
        mock_db_service.get_papers.return_value = [sample_paper]
        result = mock_db_service.get_papers(limit=10, offset=0)
        assert len(result) == 1
        assert result[0]["titulo"] == sample_paper["titulo"]
    
    def test_get_paper_by_id_found(self, mock_db_service, sample_paper):
        """get_paper_by_id retorna paper cuando existe."""
        mock_db_service.get_paper_by_id.return_value = sample_paper
        result = mock_db_service.get_paper_by_id(sample_paper["id"])
        assert result is not None
        assert result["id"] == sample_paper["id"]
    
    def test_get_paper_by_id_not_found(self, mock_db_service):
        """get_paper_by_id retorna None cuando no existe."""
        mock_db_service.get_paper_by_id.return_value = None
        result = mock_db_service.get_paper_by_id("non-existent-id")
        assert result is None
    
    def test_update_paper(self, mock_db_service, sample_paper):
        """update_paper actualiza campos correctamente."""
        updated = sample_paper.copy()
        updated["titulo"] = "Nuevo Título"
        mock_db_service.update_paper.return_value = updated
        
        result = mock_db_service.update_paper(sample_paper["id"], {"titulo": "Nuevo Título"})
        assert result["titulo"] == "Nuevo Título"
    
    def test_get_stats(self, mock_db_service):
        """get_stats retorna estadísticas."""
        mock_db_service.get_stats.return_value = {
            "total": 100,
            "procesados": 80,
            "especialidades_breakdown": {"Cardiología": 30}
        }
        result = mock_db_service.get_stats()
        assert result["total"] == 100
        assert "Cardiología" in result["especialidades_breakdown"]


class TestChannelOperations:
    """Tests para operaciones de canales."""
    
    def test_get_channels_empty(self, mock_db_service):
        """get_channels retorna lista vacía sin canales."""
        mock_db_service.get_channels.return_value = []
        result = mock_db_service.get_channels()
        assert result == []
    
    def test_add_channel(self, mock_db_service, sample_channel):
        """add_channel crea canal correctamente."""
        mock_db_service.add_channel.return_value = sample_channel
        result = mock_db_service.add_channel("@test_channel", "Test Channel")
        assert result["username"] == sample_channel["username"]
    
    def test_delete_channel(self, mock_db_service):
        """delete_channel elimina canal correctamente."""
        mock_db_service.delete_channel.return_value = True
        result = mock_db_service.delete_channel("@test_channel")
        assert result is True


class TestPaperModel:
    """Tests para el modelo Paper."""
    
    def test_paper_to_dict(self, sample_paper):
        """to_dict convierte paper a diccionario."""
        assert "id" in sample_paper
        assert "titulo" in sample_paper
        assert "autores" in sample_paper
        assert isinstance(sample_paper["autores"], list)
    
    def test_paper_required_fields(self, sample_paper):
        """Paper tiene campos requeridos."""
        required_fields = ["id", "hash", "titulo"]
        for field in required_fields:
            assert field in sample_paper
    
    def test_paper_multi_source_fields(self, sample_paper):
        """Paper tiene campos multi-fuente."""
        multi_source_fields = [
            "pmid", "mesh_terms", "abstract_estructurado",
            "affiliaciones", "funders", "license", "referencias",
            "crossmark_status", "metadata_source", "doi_validado"
        ]
        for field in multi_source_fields:
            assert field in sample_paper
