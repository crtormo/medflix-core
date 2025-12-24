import os
import groq
from typing import Dict, List, Optional
import json
import time
import threading

import groq

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

# Rate Limiter basado en límites del Free Tier de Groq
# Fuente: https://console.groq.com/docs/rate-limits
# Free Tier aproximado: 30 RPM, 6000 TPM (varía por modelo)
class RateLimiter:
    """Controla la tasa de requests para evitar 429 errors."""
    
    # Límites conservadores para Free Tier (por modelo)
    LIMITS = {
        "llama-3.1-8b-instant": {"rpm": 30, "tpm": 6000},
        "llama-3.3-70b-versatile": {"rpm": 30, "tpm": 6000},
        "llama-3.2-90b-vision-preview": {"rpm": 15, "tpm": 7000},
        "meta-llama/llama-4-maverick-17b-128e-instruct": {"rpm": 30, "tpm": 6000},
        "default": {"rpm": 20, "tpm": 5000}  # Fallback conservador
    }
    
    def __init__(self):
        self._lock = threading.Lock()
        self._last_request_time = {}
        self._request_count = {}
        self._window_start = {}
    
    def wait_if_needed(self, model: str):
        """Espera si es necesario para respetar el rate limit."""
        limits = self.LIMITS.get(model, self.LIMITS["default"])
        rpm = limits["rpm"]
        min_interval = 60.0 / rpm  # Segundos mínimos entre requests
        
        with self._lock:
            now = time.time()
            last = self._last_request_time.get(model, 0)
            elapsed = now - last
            
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                time.sleep(sleep_time)
            
            self._last_request_time[model] = time.time()

# Instancia global del rate limiter
_rate_limiter = RateLimiter()

class GroqService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        # ... (resto del init igual) ...
        if not self.api_key:
             # logging warning instead of error for test compatibility if needed
             pass
        self.client = groq.Groq(api_key=self.api_key)
        
        # Modelos optimizados
        # Llama 4 Maverick para análisis profundo (Auditoría Epistemológica)
        self.deep_model = os.getenv("GROQ_DEEP_MODEL", "meta-llama/llama-4-maverick-17b-128e-instruct")
        # 8B para extracción rápida (Snippets, Metadatos) - Más rápido y barato (mejor Rate Limit)
        self.fast_model = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")
        # Vision: llama-3.2-11b deprecado, usando 90b (o desactivar)
        self.vision_model = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")

    @retry(
        stop=stop_after_attempt(7), # Aumentar intentos
        wait=wait_exponential(multiplier=2, min=10, max=120), # Espera mínima 10s, max 2 min
        retry=retry_if_exception_type((
            httpx.HTTPStatusError, 
            httpx.ReadTimeout, 
            httpx.ConnectError,
            groq.RateLimitError,
            groq.InternalServerError,
            groq.APIConnectionError
        ))
    )
    def _make_completion_request(self, model, messages, response_format=None, temperature=0.3):
        """Wrapper con retry para llamadas a la API"""
        # Esperar si es necesario para respetar rate limits
        _rate_limiter.wait_if_needed(model)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        return self.client.chat.completions.create(**kwargs)

    def analyze_text(self, text: str, prompt_template: str, use_deep_model: bool = True) -> str:
        """Envía texto al modelo. Por defecto usa modelo profundo (70B) para auditoría."""
        model = self.deep_model if use_deep_model else self.fast_model
        try:
            completion = self._make_completion_request(
                model=model,
                messages=[{"role": "user", "content": prompt_template.format(text=text)}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error en análisis de texto (tras reintentos): {str(e)}"

    def epistemological_audit(self, text: str) -> str:
        """
        Realiza la 'Auditoría Epistemológica' de los 10 puntos.
        Trunca el texto si excede límites (simple truncation por ahora).
        """
        # Limite de seguridad básico
        truncated_text = text[:15000] 
        
        prompt = f"""
        Actúa como un revisor senior de The Lancet que habla español nativo. Realiza un análisis crítico exhaustivo del siguiente paper médico.
        Tu salida debe ser estrictamente en formato MARKDOWN y en ESPAÑOL.
        
        Texto del paper:
        {truncated_text}
        
        Realiza el análisis basado en estos 10 puntos clave:
        1. **Desafío de premisas**: ¿El estudio asume verdades no probadas?
        2. **Conflictos de interés**: ¿Hay sesgos financieros o institucionales no declarados o implícitos?
        3. **Validez Interna/Metodológica**: ¿El diseño (RCT, observacional, etc.) justifica las conclusiones?
        4. **Validez Externa**: ¿Son los resultados generalizables a una población real?
        5. **Sesgos Estadísticos**: ¿P-hacking? ¿Intervalos de confianza amplios? ¿NNT reportado?
        6. **Relevancia Clínica**: ¿El resultado es estadísticamente significativo pero clínicamente irrelevante?
        7. **Comparación con Standard of Care**: ¿El grupo control recibió el mejor tratamiento actual?
        8. **Endpoints**: ¿Se usaron endpoints duros (mortalidad) o subrogados (biomarcadores)?
        9. **Reproducibilidad y Transparencia**: ¿Están los datos disponibles?
        10. **Conclusión vs Datos**: ¿La conclusión exagera los hallazgos (spin)?

        Al final, proporciona un veredicto de una frase: "Recomendado para cambio de práctica", "Evidencia débil", etc.
        """
        
        return self.analyze_text(text="", prompt_template=prompt)

    def analyze_image_url(self, image_url: str, context: str = "") -> str:
        """
        Analiza una imagen (pasada como URL o base64 data URI).
        NOTA: Groq Vision requiere URLs accesibles o base64. 
        Asumiremos que pasaremos data URI base64.
        """
        prompt = f"""
        Describe los ejes, los intervalos de confianza y la tendencia real de este gráfico médico. Responde en ESPAÑOL.
        Contexto (si existe): {context}
        
        Responde:
        1. Descripción objetiva del gráfico.
        2. ¿La representación visual exagera o minimiza algún efecto?
        3. ¿Concuerda con la conclusión típica de un paper positivo?
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                },
                            },
                        ],
                    }
                ],
                model=self.vision_model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error analizando imagen: {str(e)}"

    def generate_snippets(self, text: str) -> Dict:
        """Genera N, NNT, resumen y metadatos estructurados."""
        truncated_text = text[:12000]
        prompt = f"""
        Eres un experto analista de literatura médica. Extrae la siguiente información del paper en formato JSON válido.
        Asegúrate de que los valores de texto estén en ESPAÑOL.
        
        {{
            "n_study": "Tamaño de la muestra (ej: 1540 pacientes)",
            "nnt": "Número Necesario a Tratar (si aplica, o 'N/A')",
            "summary_slide": "Una frase contundente para una diapositiva (max 20 palabras)",
            "study_type": "Tipo de estudio (RCT, Cohorte, Caso-Control, Meta-análisis, Revisión, Guía, etc.)",
            "specialty": "Especialidad médica principal (Cardiología, UCI, Neurología, Infectología, etc.)",
            "quality_score": 8.5,
            "tags": ["tag1", "tag2"],
            "population": "Breve descripción",
            "journal": "Nombre revista",
            "year": 2024
        }}
        
        Texto del paper:
        {truncated_text}
        """
        
        try:
            response = self._make_completion_request(
                model=self.fast_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"error": "Falló al procesar respuesta JSON"}
        except Exception as e:
             return {"error": f"Error generando snippets (tras retries): {str(e)}"}

