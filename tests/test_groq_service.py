
import pytest
from unittest.mock import MagicMock, patch
from services.groq_service import GroqService
import httpx
import json
import groq

@pytest.fixture
def groq_service():
    with patch.dict('os.environ', {'GROQ_API_KEY': 'fake_key'}):
        return GroqService()

def test_analyze_text_success(groq_service):
    # Mock de la respuesta de Groq
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Análisis completado"
    
    with patch.object(groq_service.client.chat.completions, 'create', return_value=mock_response):
        # Default uses deep_model
        result = groq_service.analyze_text("texto prueba", "Prompt {text}")
        assert result == "Análisis completado"

def test_generate_snippets_success(groq_service):
    expected_json = {
        "n_study": "100", 
        "summary_slide": "Test summary",
        "quality_score": 9.0
    }
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(expected_json)
    
    with patch.object(groq_service.client.chat.completions, 'create', return_value=mock_response):
        result = groq_service.generate_snippets("texto prueba")
        assert result["n_study"] == "100"
        # Verify it uses fast model (implicitly covered if no error, but ideally we'd check args)
        
def test_retry_logic_eventual_success(groq_service):
    # Simular fallo RateLimit dos veces y luego éxito
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Éxito tras retry"
    
    # Usamos la excepción real de Groq
    error_429 = groq.RateLimitError(message="Rate limit exceeded", response=MagicMock(), body=None)
    
    # Patching sleep to speed up test
    with patch('tenacity.nap.time.sleep', return_value=None):
        with patch.object(groq_service.client.chat.completions, 'create', side_effect=[error_429, error_429, mock_response]) as mock_create:
            result = groq_service.analyze_text("texto", "prompt {text}")
            assert result == "Éxito tras retry"
            assert mock_create.call_count == 3

def test_retry_logic_failure(groq_service):
    # Simular fallo persistente
    error_429 = groq.RateLimitError(message="Rate limit exceeded", response=MagicMock(), body=None)
    
    with patch('tenacity.nap.time.sleep', return_value=None):
        with patch.object(groq_service.client.chat.completions, 'create', side_effect=error_429):
            result = groq_service.analyze_text("texto", "prompt {text}")
            assert "Error en análisis de texto" in result
