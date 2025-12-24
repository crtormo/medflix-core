"""
Servicio de Análisis Visual para MedFlix Core
Extrae imágenes de PDFs y las analiza con modelos de visión (VLM)
"""
import fitz  # PyMuPDF
import base64
import io
import os
from pathlib import Path
from typing import List, Dict, Optional
from services.groq_service import GroqService


class VisualAnalysisService:
    """Servicio para extraer y analizar gráficos de papers médicos."""
    
    def __init__(self, groq_service: Optional[GroqService] = None):
        self.groq = groq_service
        self.output_dir = Path("data/extracted_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_images(self, pdf_path: str, min_width: int = 100, min_height: int = 100) -> List[Dict]:
        """
        Extrae imágenes de un PDF usando PyMuPDF.
        
        Args:
            pdf_path: Ruta al archivo PDF
            min_width: Ancho mínimo para filtrar imágenes pequeñas (iconos, etc.)
            min_height: Alto mínimo
            
        Returns:
            Lista de diccionarios con información de cada imagen
        """
        images_data = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc):
                image_list = page.get_images(full=True)
                
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        width = base_image["width"]
                        height = base_image["height"]
                        
                        # Filtrar imágenes muy pequeñas (probablemente iconos)
                        if width < min_width or height < min_height:
                            continue
                        
                        # Procesar con Pillow para optimizar tamaño
                        from PIL import Image
                        
                        img_pil = Image.open(io.BytesIO(image_bytes))
                        
                        # Convertir a RGB si es necesario
                        if img_pil.mode in ("RGBA", "P"):
                            img_pil = img_pil.convert("RGB")
                            
                        # Redimensionar si es muy grande (max 800px lado mayor)
                        max_dimension = 800
                        if width > max_dimension or height > max_dimension:
                            img_pil.thumbnail((max_dimension, max_dimension))
                            
                        # Guardar a buffer optimizado (JPEG quality 70)
                        buffer = io.BytesIO()
                        img_pil.save(buffer, format="JPEG", quality=70)
                        optimized_bytes = buffer.getvalue()
                        
                        # Convertir a base64
                        image_base64 = base64.b64encode(optimized_bytes).decode('utf-8')
                        data_uri = f"data:image/jpeg;base64,{image_base64}"
                        
                        # Guardar imagen localmente (versión optimizada)
                        pdf_name = Path(pdf_path).stem
                        image_filename = f"{pdf_name}_page{page_num + 1}_img{img_index + 1}.jpg"
                        image_path = self.output_dir / image_filename
                        
                        with open(image_path, "wb") as f:
                            f.write(optimized_bytes)
                        
                        images_data.append({
                            "page": page_num + 1,
                            "index": img_index + 1,
                            "width": img_pil.width,
                            "height": img_pil.height,
                            "extension": "jpg",
                            "data_uri": data_uri,
                            "local_path": str(image_path)
                        })
                        
                    except Exception as e:
                        print(f"Error extrayendo imagen {img_index} de página {page_num}: {e}")
                        continue
            
            doc.close()
            
        except Exception as e:
            print(f"Error abriendo PDF para extracción de imágenes: {e}")
        
        return images_data
    
    def analyze_graph(self, image_data_uri: str, paper_conclusion: str = "") -> str:
        """
        Analiza un gráfico usando el modelo de visión (VLM).
        
        Args:
            image_data_uri: Imagen en formato data URI (base64)
            paper_conclusion: Conclusión del autor para comparar (antisesgo)
            
        Returns:
            Análisis del gráfico en texto
        """
        if not self.groq:
            return "Servicio de visión no disponible (falta API key de Groq)"
        
        return self.groq.analyze_image_url(image_data_uri, context=paper_conclusion)
    
    def analyze_all_graphs(self, pdf_path: str, paper_conclusion: str = "") -> List[Dict]:
        """
        Extrae y analiza todos los gráficos de un PDF.
        
        Args:
            pdf_path: Ruta al PDF
            paper_conclusion: Conclusión del paper para comparación antisesgo
            
        Returns:
            Lista de diccionarios con info de imagen + análisis
        """
        images = self.extract_images(pdf_path)
        results = []
        
        for img in images:
            analysis = self.analyze_graph(img["data_uri"], paper_conclusion)
            results.append({
                "pagina": img["page"],
                "dimensiones": f"{img['width']}x{img['height']}",
                "ruta_local": img["local_path"],
                "analisis_visual": analysis
            })
        
        return results
