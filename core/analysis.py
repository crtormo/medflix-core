from .ingestion import IngestionService
from .visual_analysis import VisualAnalysisService
from services.groq_service import GroqService
from services.vector_store import VectorStoreService
from services.database import get_db_service
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class AnalysisCore:
    def __init__(self, 
                 ingestion_service: Optional[IngestionService] = None,
                 vector_store_service: Optional[VectorStoreService] = None,
                 groq_service: Optional[GroqService] = None,
                 visual_service: Optional[VisualAnalysisService] = None):
        
        self.ingestion = ingestion_service or IngestionService()
        self.vector_store = vector_store_service or VectorStoreService()
        self.db_service = get_db_service()  # Servicio PostgreSQL
        
        if groq_service:
            self.groq = groq_service
        else:
            try:
                self.groq = GroqService()
            except ValueError:
                print("Advertencia: GROQ_API_KEY no encontrada. Funciones de IA deshabilitadas.")
                self.groq = None
        
        self.visual = visual_service or VisualAnalysisService(groq_service=self.groq)

    def process_and_analyze(self, file_path: str, analyze_graphs: bool = True) -> Dict[str, Any]:
        path = Path(file_path)
        
        # 1. Ingesta enriquecida (incluye thumbnail)
        doc_data = self.ingestion.process_pdf(path)
        
        # 2. Verificar duplicados (Hash en DB)
        logger.info(f"DEBUG: Buscando hash en DB: {doc_data['hash']}")
        existing_paper = self.db_service.get_paper_by_hash(doc_data['hash'])
        logger.info(f"DEBUG: Resultado DB: {existing_paper}")
        if existing_paper:
             # Si ya existe y está procesado, retornar datos
             if existing_paper.procesado:
                return {
                    "status": "duplicate", 
                    "reason": "Ya existe en la biblioteca", 
                    "data": existing_paper.to_dict()
                }

        # 3. Crear registro inicial en DB (estado pendiente)
        paper = self.db_service.create_paper(
            hash=doc_data['hash'],
            doi=doc_data['doi'],
            titulo=doc_data['title'] or doc_data['file_name'],
            autores=[doc_data['author']] if doc_data['author'] else [],
            año=None, # Se completará con IA
            thumbnail_path=doc_data.get('thumbnail_path'),
            archivo_path=str(path),
            archivo_nombre=path.name,
            num_paginas=doc_data['page_count']
        )
        
        # 4. Análisis IA
        analysis_result = ""
        snippets = {}
        graphs_analysis: List[Dict] = []
        
        if self.groq:
            # Auditoría Epistemológica
            analysis_result = self.groq.epistemological_audit(doc_data['content'])
            
            # Snippets enriquecidos (JSON estructurado)
            snippets = self.groq.generate_snippets(doc_data['content'])
            
            # 5. Análisis Visual de Gráficos
            if analyze_graphs:
                try:
                    conclusion_hint = snippets.get('summary_slide', '')
                    graphs_analysis = self.visual.analyze_all_graphs(
                        str(path), 
                        paper_conclusion=conclusion_hint
                    )
                except Exception as e:
                    logger.error(f"Error en análisis visual: {e}")
        
        # 6. Actualizar DB con resultados completos
        paper_updated = self.db_service.mark_as_processed(
            str(paper.id),
            analysis_data={
                "analisis_completo": analysis_result,
                "resumen_slide": snippets.get('summary_slide'),
                "score_calidad": snippets.get('quality_score'),
                "tipo_estudio": snippets.get('study_type'),
                "especialidad": snippets.get('specialty') or snippets.get('study_type'), # Fallback
                "n_muestra": snippets.get('n_study'),
                "nnt": snippets.get('nnt'),
                "num_graficos": len(graphs_analysis),
                "analisis_graficos": graphs_analysis,
                # Campos adicionales que podríamos mapear del JSON
                "tags": snippets.get('tags'),
                "poblacion": snippets.get('population'),
                "año": snippets.get('year')
            }
        )
        
        # 7. Guardar en ChromaDB (para búsqueda semántica)
        # Usamos el análisis y metadatos clave para el embedding
        combined_text_for_embedding = (
            f"Título: {paper.titulo}\n"
            f"Resumen: {snippets.get('summary_slide')}\n"
            f"Contenido: {doc_data['content'][:8000]}\n" # Truncar para no exceder tokens
            f"Análisis: {analysis_result}"
        )
        
        self.vector_store.add_document(
            doc_id=str(paper.id), # Usar UUID como ID en vector store
            text=combined_text_for_embedding,
            metadata={
                "hash": paper.hash,
                "title": paper.titulo,
                "year": paper.año or 0,
                "score": paper.score_calidad or 0.0,
                "specialty": paper.especialidad or ""
            }
        )

        return {
            "status": "success",
            "job_id": str(paper.id),
            "data": paper_updated.to_dict() if paper_updated else {}
        }

