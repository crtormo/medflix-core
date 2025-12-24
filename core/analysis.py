import os
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
            # Auditoría Epistemológica (Ahora retorna JSON)
            audit_data = self.groq.epistemological_audit(doc_data['content'])
            analysis_result = audit_data.get("analisis_critico", "Error en análisis")
            veredicto = audit_data.get("veredicto_breve", "")
            
            # Snippets enriquecidos (JSON estructurado)
            snippets = self.groq.generate_snippets(doc_data['content'])
            
            # ENRIQUECIMIENTO CON DOI (Nuevo Fase 7)
            doi = doc_data.get('doi')
            enriched_meta = {}
            if doi:
                try:
                    from services.metadata_enricher import MetadataService
                    md_service = MetadataService()
                    enriched_meta = md_service.get_metadata_by_doi(doi)
                    logger.info(f"✅ Metadatos enriquecidos para DOI {doi}")
                except Exception as e:
                    logger.warning(f"Error enriqueciendo metadatos DOI: {e}")

            # Merge de datos (priorizar enriquecidos > snippets > doc_data)
            final_ano = enriched_meta.get('año') or snippets.get('year')
            final_titulo = enriched_meta.get('titulo') or doc_data['title']
            
            # --- RENOMBRADO DE ARCHIVO FÍSICO ---
            # Intentar renombrar el archivo a algo legible
            new_filename = snippets.get("suggested_filename")
            if not new_filename and final_titulo:
                 # Sanitizar titulo si no hay sugerencia
                 import re
                 clean = re.sub(r'[^a-zA-Z0-9]', '_', final_titulo)[:50]
                 new_filename = f"{clean}"
            
            final_path = str(path)
            final_name = path.name
            
            if new_filename:
                try:
                    # Asegurar extensión .pdf
                    if not new_filename.lower().endswith('.pdf'):
                        new_filename += ".pdf"
                    
                    # Directorio original
                    directory = path.parent
                    new_path = directory / new_filename
                    
                    # Renombrar físico
                    if not new_path.exists():
                        os.rename(path, new_path)
                        final_path = str(new_path)
                        final_name = new_filename
                        logger.info(f"♻️ Archivo renombrado: {path.name} -> {new_filename}")
                    else:
                        logger.warning(f"No se pudo renombrar a {new_filename}, el archivo ya existe.")
                except Exception as e:
                    logger.error(f"Error renombrando archivo: {e}")

            # 5. Análisis Visual de Gráficos
            if analyze_graphs:
                try:
                    conclusion_hint = snippets.get('summary_slide', '')
                    graphs_analysis = self.visual.analyze_all_graphs(
                        final_path, # Usar el nuevo path
                        paper_conclusion=conclusion_hint
                    )
                    
                    # --- EKG DOJO LOGIC ---
                    # Si el título o tags sugieren ECG, y hay imágenes, generar un reto
                    is_ecg = "ecg" in final_titulo.lower() or "ekg" in final_titulo.lower() or "electrocardiogram" in final_titulo.lower()
                    quiz_data = {}
                    is_quiz = False
                    
                    if is_ecg and len(doc_data.get('images', [])) > 0:
                         # Tomar la primera imagen (idealmente buscaríamos la más relevante)
                         # Aquí asumimos que doc_data tiene la ruta de imágenes extraidas.
                         # Ojo: Ingesta actual no extrae imagenes a disco separado salvo thumbnail.
                         # Usaremos el thumbnail como proxy si es un "caso en una imagen" (típico de telegram)
                         # O si 'analisis_graficos' tiene algo, usamos esa imagen.
                         
                         target_img = None
                         if paper.thumbnail_path:
                             target_img = paper.thumbnail_path
                         
                         if target_img:
                             # Convertir a data URI para enviar a Groq Vision
                             import base64
                             with open(target_img, "rb") as img_file:
                                 b64_img = base64.b64encode(img_file.read()).decode('utf-8')
                                 data_uri = f"data:image/jpeg;base64,{b64_img}"
                                 
                                 logger.info("🥋 Generando EKG Dojo Challenge...")
                                 quiz_data = self.groq.analyze_ekg_challenge(data_uri)
                                 is_quiz = True
                    
                except Exception as e:
                    logger.error(f"Error en análisis visual / EKG: {e}")
        
        # 6. Actualizar DB con resultados completos
        # Preparar datos de update incluyendo enriquecidos
        paper_updated = self.db_service.mark_as_processed(
            str(paper.id),
            analysis_data={
                "analisis_completo": analysis_result,
                "resumen_slide": snippets.get('summary_slide'),
                "score_calidad": audit_data.get("score_calidad") or snippets.get('quality_score'), # Priorizar deep model
                "tipo_estudio": snippets.get('study_type'),
                "especialidad": snippets.get('specialty') or snippets.get('study_type'),
                "n_muestra": snippets.get('n_study'),
                "nnt": snippets.get('nnt'),
                "num_graficos": len(graphs_analysis),
                "analisis_graficos": graphs_analysis,
                # Campos adicionales
                "tags": snippets.get('tags'),
                "poblacion": snippets.get('population'),
                "año": final_ano,
                # Campos Nuevos
                "revista": enriched_meta.get('revista'),
                "fecha_publicacion_exacta": enriched_meta.get('fecha_publicacion'),
                "veredicto_ia": veredicto,
                "abstract": enriched_meta.get('abstract')
            }
        )
        
        # Update Quiz Data
        if is_quiz:
             self.db_service.update_paper(str(paper.id), is_quiz=True, quiz_data=quiz_data)
        
        # Actualizar paths y título si cambiaron
        updates = {}
        if final_path != str(path):
            updates["archivo_path"] = final_path
            updates["archivo_nombre"] = final_name
            # Thumbnails también suelen basarse en nombre, pero aquí es path separado. OK.
            
        if enriched_meta.get('titulo'):
            updates["titulo"] = enriched_meta.get('titulo')
        
        if enriched_meta.get('autores'):
            updates["autores"] = enriched_meta.get('autores')
            
        if updates:
            self.db_service.update_paper(str(paper.id), **updates)
        
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
