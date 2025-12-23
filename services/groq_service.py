import os
from groq import Groq
from typing import Dict, List, Optional
import json

class GroqService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=self.api_key)
        
        # Modelos
        self.text_model = "llama-3.3-70b-versatile" 
        self.vision_model = "llama-3.2-11b-vision-preview" # Ajustar según disponibilidad

    def analyze_text(self, text: str, prompt_template: str) -> str:
        """Envía texto al modelo para análisis genérico."""
        completion = self.client.chat.completions.create(
            model=self.text_model,
            messages=[
                {"role": "user", "content": prompt_template.format(text=text)}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content

    def epistemological_audit(self, text: str) -> str:
        """
        Realiza la 'Auditoría Epistemológica' de los 10 puntos.
        Trunca el texto si excede límites (simple truncation por ahora).
        """
        # Limite de seguridad básico
        truncated_text = text[:25000] 
        
        prompt = f"""
        Actúa como un revisor senior de The Lancet. Realiza un análisis crítico exhaustivo del siguiente paper médico.
        Tu salida debe ser estrictamente en formato MARKDOWN.
        
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
        Describe los ejes, los intervalos de confianza y la tendencia real de este gráfico médico.
        Contexto (si existe): {context}
        
        Responde:
        1. Descripción objetiva del gráfico.
        2. ¿La representación visual exagera o minimiza algún efecto?
        3. ¿Concuerda con la conclusión típica de un paper positivo?
        """
        
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

    def generate_snippets(self, text: str) -> Dict:
        """Genera N, NNT y frase resumen."""
        truncated_text = text[:15000]
        prompt = f"""
        Extrae la siguiente información del texto médico en formato JSON válido:
        {{
            "n_study": "Tamaño de la muestra (ej: 1540 pacientes)",
            "nnt": "Número Necesario a Tratar (si aplica, o 'N/A')",
            "summary_slide": "Una frase contundente para una diapositiva de presentación (max 20 palabras)",
            "study_type": "Tipo de estudio (RCT, Cohorte, etc.)"
        }}
        
        Texto:
        {truncated_text}
        """
        
        response = self.client.chat.completions.create(
            model=self.text_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON response"}
