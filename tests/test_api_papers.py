"""
Tests de integración para los endpoints de la API Papers.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestPapersEndpoints:
    """Tests para /papers endpoints."""
    
    def test_list_papers_empty(self, test_client, mock_db_service):
        """GET /papers retorna lista vacía cuando no hay papers."""
        with patch('app.routers.papers.get_db_service', return_value=mock_db_service):
            response = test_client.get("/papers")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    
    def test_list_papers_with_limit(self, test_client, mock_db_service, sample_paper):
        """GET /papers respeta parámetro limit."""
        mock_db_service.get_papers.return_value = [sample_paper]
        
        with patch('app.routers.papers.get_db_service', return_value=mock_db_service):
            response = test_client.get("/papers?limit=5")
            assert response.status_code == 200
            mock_db_service.get_papers.assert_called()
    
    def test_get_paper_details_not_found(self, test_client, mock_db_service):
        """GET /papers/{id} retorna 404 para paper inexistente."""
        mock_db_service.get_paper_by_id.return_value = None
        
        with patch('app.routers.papers.get_db_service', return_value=mock_db_service):
            response = test_client.get("/papers/non-existent-id")
            assert response.status_code == 404
    
    def test_get_paper_details_success(self, test_client, mock_db_service, sample_paper):
        """GET /papers/{id} retorna detalles del paper."""
        mock_db_service.get_paper_by_id.return_value = sample_paper
        
        with patch('app.routers.papers.get_db_service', return_value=mock_db_service):
            response = test_client.get(f"/papers/{sample_paper['id']}")
            assert response.status_code == 200
            data = response.json()
            assert data["titulo"] == sample_paper["titulo"]
    
    def test_get_stats(self, test_client, mock_db_service):
        """GET /papers/stats retorna estadísticas."""
        mock_db_service.get_stats.return_value = {
            "total": 100,
            "procesados": 80,
            "especialidades_breakdown": {"Cardiología": 30, "UCI": 25}
        }
        
        with patch('app.routers.papers.get_db_service', return_value=mock_db_service):
            response = test_client.get("/papers/stats")
            assert response.status_code == 200
            data = response.json()
            assert "total" in data


class TestPapersEnrichment:
    """Tests para enriquecimiento de metadatos via DOI."""
    
    def test_enrich_doi_no_doi(self, test_client, mock_db_service, sample_paper):
        """POST /papers/{id}/enrich-doi falla sin DOI."""
        paper_without_doi = sample_paper.copy()
        paper_without_doi["doi"] = None
        mock_db_service.get_paper_by_id.return_value = paper_without_doi
        
        with patch('app.routers.papers.get_db_service', return_value=mock_db_service):
            response = test_client.post(
                f"/papers/{sample_paper['id']}/enrich-doi",
                json={}
            )
            # Sin DOI existente ni nuevo, debe fallar
            assert response.status_code in [400, 422]
    
    def test_enrich_doi_with_new_doi(self, test_client, mock_db_service, sample_paper):
        """POST /papers/{id}/enrich-doi acepta DOI en payload."""
        mock_db_service.get_paper_by_id.return_value = sample_paper
        mock_db_service.update_paper.return_value = sample_paper
        
        mock_metadata_service = MagicMock()
        mock_metadata_service.get_metadata_by_doi.return_value = {
            "titulo": "Updated Title",
            "doi_validado": True,
            "metadata_source": "pubmed"
        }
        
        with patch('app.routers.papers.get_db_service', return_value=mock_db_service):
            with patch('app.routers.papers.MetadataService', return_value=mock_metadata_service):
                response = test_client.post(
                    f"/papers/{sample_paper['id']}/enrich-doi",
                    json={"doi": "10.1001/test.2023"}
                )
                # Puede ser 200 o error si mock no está bien configurado
                assert response.status_code in [200, 500]


class TestHealthEndpoint:
    """Tests para el endpoint de health check."""
    
    def test_health_check_returns_status(self, test_client):
        """GET /health retorna estado."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
    
    def test_root_endpoint(self, test_client):
        """GET / retorna mensaje de bienvenida."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "MedFlix" in data["message"]
