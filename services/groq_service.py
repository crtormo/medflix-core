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

    def book_analysis(self, text: str) -> str:
        """
        Realiza un resumen y análisis de libro médico.
        """
        truncated_text = text[:15000]
        prompt = f"""
        Actúa como un bibliotecario médico senior y experto en educación médica. 
        Analiza el siguiente texto que pertenece a un LIBRO MÉDICO.
        Tu salida debe ser estrictamente en formato MARKDOWN y en ESPAÑOL.
        
        Texto del libro:
        {truncated_text}
        
        Proporciona:
        1. **Resumen General**: ¿De qué trata el libro y a quién va dirigido?
        2. **Estructura y Contenido**: Breve descripción de los temas cubiertos.
        3. **Utilidad Clínica/Educativa**: ¿Cómo ayuda este libro a un profesional o estudiante?
        4. **Nivel de Dificultad**: Básico, Intermedio, Avanzado.
        
        Al final, proporciona un veredicto de una frase: "Referencia esencial", "Manual práctico", "Texto introductorio", etc.
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
    def analyze_ekg_challenge(self, image_url: str) -> Dict:
        """
        Analiza una imagen de EKG y genera un desafío diagnóstico.
        Retorna JSON con pregunta, opciones y respuesta.
        """
        prompt = """
        Eres un experto cardiólogo docente. Analiza este ECG cuidadosamente.
        Genera un desafío de diagnóstico para médicos residentes en formato JSON.
        
        Tu salida debe ser ESTRICTAMENTE este JSON:
        {
            "question": "¿Cuál es el diagnóstico principal basado en este trazado?",
            "options": [
                "A: Fibrilación Auricular", 
                "B: Flutter Auricular",
                "C: Taquicardia Sinusal",
                "D: Bloqueo AV 2do Grado"
            ],
            "correct_answer": "B",
            "explanation": "Se observan ondas F en dientes de sierra en DII, DIII y aVF..."
        }
        
        Asegúrate de que las opciones sean plausibles (distractores realistas) y la explicación sea educativa.
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                model=self.vision_model,
                response_format={"type": "json_object"}
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            # Fallback simple si falla
            return {
                "question": "Analiza este ECG (Error generacion automatica)",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": f"Error: {str(e)}"
            }
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
            "clinical_implication": "Implicación clínica directa (max 140 chars)",
            "study_type": "Tipo de estudio (RCT, Cohorte, Caso-Control, Meta-análisis, Revisión, Guía, etc.)",
            "specialty": "Especialidad médica principal",
            "quality_score": 8.5,
            "tags": ["tag1", "tag2"],
            "population": "Breve descripción",
            "journal": "Nombre revista",
            "year": 2024,
            "suggested_filename": "Titulo_Del_Estudio_Ano (usar guiones bajos, sin espacios, sin caracteres especiales, max 50 chars)"
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

    def generate_book_metadata(self, text: str) -> Dict:
        """Extrae metadatos específicos de libros médicos."""
        truncated_text = text[:12000]
        prompt = f"""
        Extrae metadatos de este LIBRO MÉDICO en formato JSON válido.
        Asegúrate de que los valores de texto estén en ESPAÑOL.
        
        {{
            "titulo": "Título oficial del libro",
            "autores": ["Autor 1", "Autor 2"],
            "editorial": "Nombre de la editorial",
            "especialidad": "Especialidad médica principal",
            "isbn": "ISBN-13 o ISBN-10 si se encuentra",
            "año": 2024,
            "edicion": "Ej: 5ta Edición",
            "summary_short": "Resumen de una frase para catálogo (max 20 palabras)",
            "tags": ["tag1", "tag2"],
            "idioma": "es",
            "suggested_filename": "Libro_Titulo_Ano (usar guiones bajos, sin espacios, sin caracteres especiales, max 50 chars)"
        }}
        
        Texto del libro:
        {truncated_text}
        """
        try:
            response = self._make_completion_request(
                model=self.fast_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}

    def generate_clinical_insights(self, text: str) -> Dict:
        """
        Extrae información crítica para decisiones clínicas rápidas (Modo Guardia).
        Enfocado en UCI y Emergencias.
        """
        truncated_text = text[:15000]
        prompt = f"""
        Eres un intensivista senior con 20 años de experiencia en UCI. 
        Analiza el siguiente texto médico para extraer información CRÍTICA de soporte vital.
        Tu salida debe ser ESTRICTAMENTE un JSON válido en ESPAÑOL.
        
        {{
            "bottom_line": "La conclusión central para la práctica en una frase contundente",
            "key_dosages": ["Dosis A (ej: 0.1 mcg/kg/min)", "Dosis B"],
            "safety_warnings": ["Advertencia de seguridad 1", "Contraindicación 2"],
            "grade": "Nivel de evidencia (A, B, C, o D)",
            "safety_disclaimer": "Verificar con protocolo institucional. Sugerencia por IA."
        }}
        
        Texto:
        {truncated_text}
        """
        try:
            response = self._make_completion_request(
                model=self.fast_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e), "bottom_line": "No se pudieron extraer insights clínicos."}

    def extract_gpc_recommendations(self, text: str) -> Dict:
        """
        Extrae recomendaciones específicas de una Guía de Práctica Clínica.
        """
        truncated_text = text[:15000]
        prompt = f"""
        Analiza esta Guía de Práctica Clínica (GPC) y extrae las recomendaciones más fuertes ( Clase I y IIa).
        Tu salida debe ser ESTRICTAMENTE un JSON válido en ESPAÑOL.
        
        {{
            "clase_i": ["Recomendación 1", "Recomendación 2"],
            "clase_iia": ["Recomendación A"],
            "contraindicaciones_iii": ["Lo que NO se debe hacer"],
            "puntos_clave": ["Mensaje central 1"]
        }}
        
        Texto:
        {truncated_text}
        """
        try:
            response = self._make_completion_request(
                model=self.fast_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"clase_i": [], "clase_iia": [], "contraindicaciones_iii": [], "puntos_clave": []}

    def suggest_calculators(self, text: str) -> List[str]:
        """
        Sugiere calculadoras médicas relevantes basadas en el texto.
        """
        prompt = f"""
        Identifica qué scores o calculadoras clínicas son relevantes para este texto médico.
        Responde SÓLO con una lista de nombres de calculadoras separadas por comas.
        Ej: SOFA, Wells, Apache II, CURB-65, HAS-BLED.
        
        Texto: {text[:5000]}
        """
        try:
            completion = self._make_completion_request(
                model=self.fast_model,
                messages=[{"role": "user", "content": prompt}]
            )
            res = completion.choices[0].message.content
            return [c.strip() for c in res.split(",") if c.strip()]
        except:
            return []
