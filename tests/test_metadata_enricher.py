"""
Tests unitarios para el servicio de metadatos multi-fuente.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

from services.metadata_enricher import MetadataService


@pytest.fixture
def metadata_service():
    """Fixture que retorna una instancia del servicio."""
    return MetadataService()


# ==================== TESTS VALIDACIÓN DOI ====================

class TestValidacionDOI:
    """Tests para la validación de DOIs."""
    
    def test_doi_formato_valido(self, metadata_service):
        """DOI con formato correcto pasa validación de formato."""
        # Mock de requests.head para evitar llamadas reales
        with patch('requests.head') as mock_head:
            mock_head.return_value = MagicMock(status_code=200, url="https://example.com/paper")
            
            resultado = metadata_service.validar_doi("10.1056/NEJMoa2007764")
            
            assert resultado["valido"] == True
            assert resultado["url_resuelta"] is not None
    
    def test_doi_formato_invalido(self, metadata_service):
        """DOI con formato incorrecto falla."""
        resultado = metadata_service.validar_doi("esto-no-es-un-doi")
        
        assert resultado["valido"] == False
        assert "Formato DOI inválido" in resultado["error"]
    
    def test_doi_vacio(self, metadata_service):
        """DOI vacío retorna error."""
        resultado = metadata_service.validar_doi("")
        
        assert resultado["valido"] == False
        assert "DOI vacío" in resultado["error"]
    
    def test_doi_cache(self, metadata_service):
        """DOIs validados se cachean."""
        with patch('requests.head') as mock_head:
            mock_head.return_value = MagicMock(status_code=200, url="https://test.com")
            
            # Primera llamada
            metadata_service.validar_doi("10.1234/test")
            # Segunda llamada (debería usar cache)
            metadata_service.validar_doi("10.1234/test")
            
            # Solo debería haberse hecho UNA llamada HTTP
            assert mock_head.call_count == 1


# ==================== TESTS PUBMED ====================

class TestPubMed:
    """Tests para extracción de metadatos PubMed."""
    
    @patch('requests.get')
    def test_pubmed_extrae_mesh_terms(self, mock_get, metadata_service):
        """PubMed extrae términos MeSH correctamente."""
        # Mock de búsqueda PMID
        mock_search = MagicMock()
        mock_search.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}
        
        # Mock de fetch con MeSH
        mock_fetch = MagicMock()
        mock_fetch.text = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                        <Journal><Title>Test Journal</Title></Journal>
                    </Article>
                    <MeshHeadingList>
                        <MeshHeading>
                            <DescriptorName>Cardiovascular Diseases</DescriptorName>
                        </MeshHeading>
                        <MeshHeading>
                            <DescriptorName>Biomarkers</DescriptorName>
                            <QualifierName>blood</QualifierName>
                        </MeshHeading>
                    </MeshHeadingList>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        mock_get.side_effect = [mock_search, mock_fetch]
        
        resultado = metadata_service._try_pubmed("10.1234/test")
        
        assert "Cardiovascular Diseases" in resultado.get("mesh_terms", [])
        assert "Biomarkers/blood" in resultado.get("mesh_terms", [])
    
    @patch('requests.get')
    def test_pubmed_abstract_estructurado(self, mock_get, metadata_service):
        """PubMed extrae abstract con secciones."""
        mock_search = MagicMock()
        mock_search.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}
        
        mock_fetch = MagicMock()
        mock_fetch.text = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                        <Journal><Title>Test Journal</Title></Journal>
                        <Abstract>
                            <AbstractText Label="BACKGROUND">Contexto del estudio.</AbstractText>
                            <AbstractText Label="METHODS">Se realizó un RCT.</AbstractText>
                            <AbstractText Label="RESULTS">Resultados significativos.</AbstractText>
                            <AbstractText Label="CONCLUSIONS">El tratamiento es efectivo.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        mock_get.side_effect = [mock_search, mock_fetch]
        
        resultado = metadata_service._try_pubmed("10.1234/test")
        abstract_est = resultado.get("abstract_estructurado", {})
        
        assert "antecedentes" in abstract_est
        assert "metodos" in abstract_est
        assert "resultados" in abstract_est
        assert "conclusiones" in abstract_est
    
    @patch('requests.get')
    def test_pubmed_afiliaciones(self, mock_get, metadata_service):
        """PubMed extrae afiliaciones de autores."""
        mock_search = MagicMock()
        mock_search.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}
        
        mock_fetch = MagicMock()
        mock_fetch.text = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                        <Journal><Title>Test Journal</Title></Journal>
                        <AuthorList>
                            <Author>
                                <LastName>Smith</LastName>
                                <ForeName>John</ForeName>
                                <AffiliationInfo>
                                    <Affiliation>Harvard Medical School, Boston, USA</Affiliation>
                                </AffiliationInfo>
                            </Author>
                        </AuthorList>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        mock_get.side_effect = [mock_search, mock_fetch]
        
        resultado = metadata_service._try_pubmed("10.1234/test")
        affiliaciones = resultado.get("affiliaciones", [])
        
        assert len(affiliaciones) > 0
        assert "Harvard" in affiliaciones[0]["institucion"]


# ==================== TESTS CROSSREF ====================

class TestCrossRef:
    """Tests para extracción de metadatos CrossRef."""
    
    def test_crossref_extrae_funders(self, metadata_service):
        """CrossRef extrae información de financiadores."""
        mock_response = {
            "message": {
                "title": ["Test Paper"],
                "funder": [
                    {"name": "NIH", "DOI": "10.13039/100000002", "award": ["R01-123"]},
                    {"name": "Wellcome Trust", "DOI": None, "award": []}
                ]
            }
        }
        
        with patch.object(metadata_service.cr, 'works', return_value=mock_response):
            resultado = metadata_service._try_crossref("10.1234/test")
            funders = resultado.get("funders", [])
            
            assert len(funders) == 2
            assert funders[0]["nombre"] == "NIH"
            assert "R01-123" in funders[0]["award"]
    
    def test_crossref_extrae_license(self, metadata_service):
        """CrossRef extrae URL de licencia."""
        mock_response = {
            "message": {
                "title": ["Test Paper"],
                "license": [
                    {"URL": "https://creativecommons.org/licenses/by/4.0/"}
                ]
            }
        }
        
        with patch.object(metadata_service.cr, 'works', return_value=mock_response):
            resultado = metadata_service._try_crossref("10.1234/test")
            
            assert "creativecommons" in resultado.get("license", "")
    
    def test_crossref_extrae_referencias(self, metadata_service):
        """CrossRef extrae DOIs de referencias."""
        mock_response = {
            "message": {
                "title": ["Test Paper"],
                "reference": [
                    {"DOI": "10.1234/ref1", "key": "ref-1"},
                    {"DOI": "10.1234/ref2", "key": "ref-2"},
                    {"key": "ref-3"}  # Sin DOI
                ]
            }
        }
        
        with patch.object(metadata_service.cr, 'works', return_value=mock_response):
            resultado = metadata_service._try_crossref("10.1234/test")
            referencias = resultado.get("referencias", [])
            
            # Solo referencias con DOI
            assert len(referencias) == 2
            assert referencias[0]["doi"] == "10.1234/ref1"


# ==================== TESTS MERGE ====================

class TestMergeInteligente:
    """Tests para la fusión inteligente de metadatos."""
    
    def test_merge_prioriza_pubmed_para_mesh(self, metadata_service):
        """Merge prioriza PubMed para MeSH terms."""
        pubmed = {"mesh_terms": ["Term1", "Term2"]}
        crossref = {}
        
        resultado = metadata_service._fusionar_metadatos(pubmed, crossref)
        
        assert resultado["mesh_terms"] == ["Term1", "Term2"]
    
    def test_merge_prioriza_crossref_para_funders(self, metadata_service):
        """Merge prioriza CrossRef para funders."""
        pubmed = {}
        crossref = {"funders": [{"nombre": "NIH"}]}
        
        resultado = metadata_service._fusionar_metadatos(pubmed, crossref)
        
        assert resultado["funders"][0]["nombre"] == "NIH"
    
    def test_merge_titulo_pubmed_primero(self, metadata_service):
        """Merge usa título de PubMed si está disponible."""
        pubmed = {"titulo": "Título PubMed"}
        crossref = {"titulo": "Título CrossRef"}
        
        resultado = metadata_service._fusionar_metadatos(pubmed, crossref)
        
        assert resultado["titulo"] == "Título PubMed"
    
    def test_merge_titulo_fallback_crossref(self, metadata_service):
        """Merge usa título de CrossRef si PubMed no tiene."""
        pubmed = {"titulo": None}
        crossref = {"titulo": "Título CrossRef"}
        
        resultado = metadata_service._fusionar_metadatos(pubmed, crossref)
        
        assert resultado["titulo"] == "Título CrossRef"
    
    def test_merge_año_mas_temprano(self, metadata_service):
        """Merge usa el año más temprano."""
        pubmed = {"año": 2024}
        crossref = {"año": 2023}
        
        resultado = metadata_service._fusionar_metadatos(pubmed, crossref)
        
        assert resultado["año"] == 2023


# ==================== TESTS API PRINCIPAL ====================

class TestGetMetadataByDOI:
    """Tests para el método principal get_metadata_by_doi."""
    
    def test_normaliza_doi_con_prefijo_https(self, metadata_service):
        """Normaliza DOI quitando prefijo https://doi.org/."""
        with patch.object(metadata_service, '_try_pubmed', return_value={"titulo": "Test"}):
            with patch.object(metadata_service, '_try_crossref', return_value={}):
                with patch.object(metadata_service, 'validar_doi', return_value={"valido": True}):
                    resultado = metadata_service.get_metadata_by_doi("https://doi.org/10.1234/test")
                    
                    assert resultado.get("titulo") == "Test"
    
    def test_retorna_metadata_source_merged(self, metadata_service):
        """Retorna metadata_source='merged' cuando ambas fuentes tienen datos."""
        pubmed_data = {"titulo": "Test", "pmid": "123", "mesh_terms": ["Term"]}
        crossref_data = {"titulo": "Test", "funders": [{"nombre": "NIH"}]}
        
        with patch.object(metadata_service, '_try_pubmed', return_value=pubmed_data):
            with patch.object(metadata_service, '_try_crossref', return_value=crossref_data):
                with patch.object(metadata_service, 'validar_doi', return_value={"valido": True}):
                    resultado = metadata_service.get_metadata_by_doi("10.1234/test")
                    
                    assert resultado["metadata_source"] == "merged"
    
    def test_retorna_vacio_si_no_hay_datos(self, metadata_service):
        """Retorna diccionario vacío si ninguna fuente tiene datos."""
        with patch.object(metadata_service, '_try_pubmed', return_value={}):
            with patch.object(metadata_service, '_try_crossref', return_value={}):
                with patch.object(metadata_service, 'validar_doi', return_value={"valido": False}):
                    resultado = metadata_service.get_metadata_by_doi("10.9999/noexiste")
                    
                    assert resultado == {}
