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


    def chat_with_paper(self, paper_id: str, question: str) -> str:
        """
        Permite chatear con un paper específico usando RAG.
        1. Recuperar contexto de vector store filtrando por paper_id
        2. Consultar LLM con el contexto
        """
        if not self.groq:
            return "El servicio de IA no está disponible."
            
        # Buscar contexto relevante solo de ESTE paper
        context_results = self.vector_store.collection.query(
            query_texts=[question],
            n_results=3,
            where={"id": paper_id} # Asumiendo que guardamos ID en metadata o podemos filtrar
            # NOTA: En vector_store.add_document usamos doc_id como ID del chunk? 
            # Si usamos doc_id como ID de documento, esto funciona.
            # Veamos vector_store.py: ids=[doc_id] -> Un paper = Un chunk gigante?
            # En la implementación actual linea 118: doc_id=str(paper.id). 
            # Sí, es un chunk por paper.
        )
        
        # Si no usamos metadata filtering, usamos IDs directos si es un solo doc
        # Pero query busca en toda la colección. Mejor filtrar.
        # En ingestion linea 121: metadata ID no se incluye explicitamente como campo 'id'
        # pero se pasa como 'ids' argument.
        
        # Recuperar texto
        context = ""
        if context_results['documents'] and context_results['documents'][0]:
            context = "\n\n".join(context_results['documents'][0])
            
        if not context:
            # Fallback a buscar por ID directo si chroma query falla
            try: 
                 doc = self.vector_store.collection.get(ids=[paper_id])
                 if doc['documents']:
                     context = doc['documents'][0]
            except:
                pass
        
        if not context:
            return "No pude encontrar el contenido de este documento para responder."

        prompt = f"""
        Utilizando SÓLO la siguiente información del paper médico (y tus conocimientos generales para dar coherencia pero sin inventar datos):
        
        CONTEXTO:
        {context[:15000]}
        
        PREGUNTA DEL USUARIO:
        {question}
        
        Responde de manera concisa, profesional y en ESPAÑOL.
        """
        
        return self.groq.analyze_text(text="", prompt_template=prompt)
