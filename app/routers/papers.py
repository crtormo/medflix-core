from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from app.dependencies import analysis_core, reference_generator
from services.database import get_db_service

router = APIRouter(
    prefix="/papers",
    tags=["papers"]
)

# --- Endpoints de Papers ---

@router.get("", response_model=List[Dict])
async def list_papers(
    limit: int = 20, 
    offset: int = 0,
    specialty: Optional[str] = None,
    sort: Optional[str] = "recent",
    is_quiz: bool = False,
    categoria: Optional[str] = None,
    include_deleted: bool = False
):
    """Lista papers para el catálogo. Filtra por categoría si se especifica."""
    db = get_db_service()
    
    if categoria:
        papers = db.get_papers_by_categoria(categoria, limit, include_deleted)
    elif is_quiz:
        papers = db.get_quiz_papers(limit)
    elif specialty and specialty != "Todas":
        papers = db.get_papers_by_especialidad(specialty, limit)
    elif sort == "quality":
        papers = db.get_top_papers(limit)
    else:
        papers = db.get_recent_papers(limit)
        
    return [p.to_card_dict() for p in papers]

# --- Endpoints Estáticos (ANTES de rutas dinámicas) ---

@router.get("/stats", tags=["stats"])
async def get_stats():
    return get_db_service().get_stats()

@router.get("/especialidades", tags=["stats"])
async def get_especialidades():
    """Retorna lista única de especialidades en la DB."""
    return get_db_service().get_all_especialidades()

@router.get("/search", tags=["search"])
async def search_papers(q: str, limit: int = 20):
    """Busca papers por título, autores o tags (SQL ILIKE)."""
    db = get_db_service()
    papers = db.search_papers(q, limit)
    return [p.to_card_dict() for p in papers]

@router.get("/query", tags=["search"])
def query_papers(q: str):
    """Busca papers usando RAG simple"""
    results = analysis_core.vector_store.query_similar(q)
    return results

@router.get("/citar/{doc_id}", tags=["tools"])
def generate_citation(doc_id: str, style: str = "vancouver"):
    """
    Genera una cita formateada para un documento.
    """
    results = analysis_core.vector_store.collection.get(ids=[doc_id])
    
    if not results['ids']:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    metadata = results['metadatas'][0] if results['metadatas'] else {}
    citation = reference_generator.generate_citation(metadata, style=style)
    
    return {
        "doc_id": doc_id,
        "estilo": style,
        "cita": citation
    }

# --- Endpoints de Gestión ---

@router.get("/deleted", response_model=List[Dict], tags=["management"])
async def list_deleted_papers(limit: int = 50):
    """Lista papers eliminados (soft delete)."""
    db = get_db_service()
    papers = db.get_deleted_papers(limit)
    return [p.to_card_dict() for p in papers]

@router.delete("/{paper_id}", tags=["management"])
async def soft_delete_paper(paper_id: str):
    """Marca un paper como eliminado (soft delete). No se volverá a descargar."""
    db = get_db_service()
    success = db.soft_delete_paper(paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    return {"success": True, "message": "Paper marcado como eliminado"}

@router.put("/{paper_id}/restore", tags=["management"])
async def restore_paper(paper_id: str):
    """Restaura un paper eliminado."""
    db = get_db_service()
    success = db.restore_paper(paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    return {"success": True, "message": "Paper restaurado"}

@router.put("/{paper_id}/categoria", tags=["management"])
async def change_paper_categoria(paper_id: str, payload: Dict):
    """Cambia la categoría de un paper. Payload: {"categoria": "papers|libros|ekg_dojo|sin_categorizar"}"""
    nueva_categoria = payload.get("categoria")
    if not nueva_categoria:
        raise HTTPException(status_code=400, detail="Falta el campo 'categoria'")
    
    db = get_db_service()
    paper = db.change_categoria(paper_id, nueva_categoria)
    if not paper:
        raise HTTPException(status_code=400, detail="Categoría inválida o paper no encontrado")
    return {"success": True, "message": f"Categoría cambiada a {nueva_categoria}", "paper": paper.to_dict()}

@router.delete("/{paper_id}/permanent", tags=["management"])
async def permanent_delete_paper(paper_id: str):
    """Elimina permanentemente un paper de la base de datos."""
    db = get_db_service()
    success = db.delete_paper(paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    return {"success": True, "message": "Paper eliminado permanentemente"}


# --- Endpoints de Metadatos (Específicos) ---

# (Rutas de enriquecimiento movidas arriba)


# --- Endpoints Dinámicos (DESPUÉS de rutas estáticas/específicas) ---

@router.get("/{paper_id}", response_model=Dict)
def get_paper_details(paper_id: str):
    """Obtiene los detalles completos de un paper."""
    db = get_db_service()
    paper = db.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    return paper.to_dict()


@router.put("/{paper_id}")
async def update_paper_metadata(paper_id: str, updates: Dict):
    """
    Actualiza metadatos de un paper manualmente.
    """
    db = get_db_service()
    
    try:
        # Extraer campos permitidos
        valid_fields = ["titulo", "autores", "año", "especialidad", "tipo_estudio"]
        clean_updates = {k: v for k, v in updates.items() if k in valid_fields}
        
        paper = db.update_paper(paper_id, **clean_updates)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper no encontrado")
            
        return paper.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{paper_id}/enrich-doi", tags=["metadata"])
async def enrich_paper_doi(paper_id: str, payload: Optional[Dict] = None):
    """
    Enriquece los metadatos de un paper usando su DOI.
    Consulta PubMed y CrossRef para obtener metadatos completos.
    
    Payload opcional: {"doi": "10.xxxx/yyyy"} para especificar un DOI diferente.
    Si no se provee, usa el DOI existente del paper.
    """
    from services.metadata_enricher import MetadataService
    
    db = get_db_service()
    paper = db.get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    
    # Usar DOI del payload o el existente
    doi = None
    if payload and payload.get("doi"):
        doi = payload["doi"]
    elif paper.doi:
        doi = paper.doi
    else:
        raise HTTPException(
            status_code=400, 
            detail="No hay DOI disponible. Proporcione uno en el payload: {\"doi\": \"10.xxxx/yyyy\"}"
        )
    
    # Consultar servicios de metadatos
    metadata_service = MetadataService()
    enriched_data = metadata_service.get_metadata_by_doi(doi)
    
    if not enriched_data:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontraron metadatos para el DOI: {doi}"
        )
    
    # Mapear campos del servicio a campos de la base de datos
    update_fields = {}
    
    # DOI (actualizar si era diferente)
    if doi != paper.doi:
        update_fields["doi"] = doi
    
    # Campos básicos
    if enriched_data.get("titulo") and not paper.titulo:
        update_fields["titulo"] = enriched_data["titulo"]
    if enriched_data.get("autores"):
        update_fields["autores"] = enriched_data["autores"]
    if enriched_data.get("revista"):
        update_fields["revista"] = enriched_data["revista"]
    if enriched_data.get("año"):
        update_fields["año"] = enriched_data["año"]
    if enriched_data.get("abstract") and not paper.abstract:
        update_fields["abstract"] = enriched_data["abstract"]
    
    # Campos multi-fuente
    if enriched_data.get("pmid"):
        update_fields["pmid"] = enriched_data["pmid"]
    if enriched_data.get("mesh_terms"):
        update_fields["mesh_terms"] = enriched_data["mesh_terms"]
    if enriched_data.get("abstract_estructurado"):
        update_fields["abstract_estructurado"] = enriched_data["abstract_estructurado"]
    if enriched_data.get("affiliaciones"):
        update_fields["affiliaciones"] = enriched_data["affiliaciones"]
    if enriched_data.get("funders"):
        update_fields["funders"] = enriched_data["funders"]
    if enriched_data.get("license"):
        update_fields["license"] = enriched_data["license"]
    if enriched_data.get("referencias"):
        update_fields["referencias"] = enriched_data["referencias"]
    if enriched_data.get("crossmark_status"):
        update_fields["crossmark_status"] = enriched_data["crossmark_status"]
    if enriched_data.get("fecha_publicacion"):
        update_fields["fecha_publicacion_exacta"] = enriched_data["fecha_publicacion"]
    if enriched_data.get("metadata_source"):
        update_fields["metadata_source"] = enriched_data["metadata_source"]
    if enriched_data.get("doi_validado") is not None:
        update_fields["doi_validado"] = enriched_data["doi_validado"]
    
    # Actualizar en base de datos
    if update_fields:
        updated_paper = db.update_paper(paper_id, **update_fields)
        if not updated_paper:
            raise HTTPException(status_code=500, detail="Error actualizando paper")
        return {
            "success": True,
            "mensaje": f"Metadatos actualizados desde {enriched_data.get('metadata_source', 'fuente externa')}",
            "campos_actualizados": list(update_fields.keys()),
            "paper": updated_paper.to_dict()
        }
        return {
            "success": True,
            "mensaje": "No se encontraron campos nuevos para actualizar",
            "campos_actualizados": [],
            "paper": paper.to_dict()
        }


@router.put("/{paper_id}/enrich-book", tags=["metadata"])
async def enrich_book_metadata(paper_id: str, payload: Optional[Dict] = None):
    """
    Enriquece metadatos de un libro usando ISBN o título.
    Payload: {"isbn": "9780323341905"} o vacío para auto-detectar.
    """
    from app.dependencies import book_enricher
    db = get_db_service()
    paper = db.get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    
    # Intentar obtener ISBN: payload -> DB -> auto-detectar
    isbn = None
    if payload and payload.get("isbn"):
        isbn = payload["isbn"]
    elif paper.isbn:
        isbn = paper.isbn
    else:
        # Auto-detectar de titulo o contenido
        isbn = book_enricher.extract_isbn_from_text(paper.titulo)
        if not isbn and paper.abstract:
            isbn = book_enricher.extract_isbn_from_text(paper.abstract)
            
    enriched_data = None
    if not isbn:
        # Fallback: buscar por título
        title = paper.titulo.replace('.pdf', '').replace('_', ' ')
        enriched_data = book_enricher.enrich_by_title(title)
        if not enriched_data or not enriched_data.get('titulo'):
             raise HTTPException(status_code=400, detail="No se pudo encontrar ISBN ni metadatos por título")
    else:
        enriched_data = book_enricher.enrich_by_isbn(isbn)
        
    if not enriched_data or not enriched_data.get('titulo'):
        raise HTTPException(status_code=404, detail="No se encontraron metadatos satisfactorios")
    
    # Mapear y actualizar
    update_fields = {
        "isbn": enriched_data.get("isbn") or isbn,
        "editorial": enriched_data.get("editorial"),
        "edicion": enriched_data.get("edicion"),
        "cover_url": enriched_data.get("cover_url"),
        "descripcion_libro": enriched_data.get("descripcion_libro") or enriched_data.get("descripcion"),
        "idioma": enriched_data.get("idioma"),
        "open_library_id": enriched_data.get("open_library_id"),
        "año": enriched_data.get("año") or paper.año,
        "num_paginas": enriched_data.get("num_paginas") or paper.num_paginas
    }
    
    # Autores si no tiene o son pocos
    if enriched_data.get("autores") and (not paper.autores or len(paper.autores) == 0):
        update_fields["autores"] = enriched_data["autores"]
    
    # Descargar portada localmente si hay URL
    if enriched_data.get("isbn") and enriched_data.get("cover_url"):
        cover_path = book_enricher._download_cover(enriched_data['isbn'], enriched_data['cover_url'])
        if cover_path:
            update_fields["cover_path"] = str(cover_path)
    
    # Título más limpio si el actual parece nombre de archivo
    if paper.titulo and ('.pdf' in paper.titulo.lower() or '_' in paper.titulo or len(paper.titulo) < 5):
        update_fields["titulo"] = enriched_data["titulo"]

    updated_paper = db.update_paper(paper_id, **update_fields)
    if not updated_paper:
        raise HTTPException(status_code=500, detail="Error actualizando libro en DB")
        
    return {
        "success": True,
        "message": f"Metadatos de libro actualizados desde {enriched_data.get('metadata_source', 'fuente externa')}",
        "paper": updated_paper.to_dict()
    }
@router.post("/{paper_id}/clinical-insights", tags=["analysis"])
async def generate_clinical_insights(paper_id: str):
    """
    Genera Insights Clínicos (Modo Guardia) para un paper existente.
    """
    from app.dependencies import analysis_core
    db = get_db_service()
    paper = db.get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper no encontrado")
    
    # Obtener contenido del vector store o archivo
    content = ""
    try:
        # Intentar obtener de ChromaDB primero
        v_doc = analysis_core.vector_store.collection.get(ids=[paper_id])
        if v_doc['documents']:
            content = v_doc['documents'][0]
    except:
        pass
        
    if not content and paper.archivo_path:
        # Fallback: Extraer de PDF de nuevo
        doc_data = analysis_core.ingestion.process_pdf(Path(paper.archivo_path))
        content = doc_data['content']
        
    if not content:
        raise HTTPException(status_code=400, detail="No se pudo recuperar el contenido del documento")
    
    # Generar insights
    insights = analysis_core.groq.generate_clinical_insights(content)
    
    # Actualizar DB
    updated_paper = db.update_paper(paper_id, clinical_insights=insights)
    
    return {
        "success": True,
        "clinical_insights": insights
    }

# --- Endpoints de Chat & RAG ---
# (Nota: main.py original los tenía en raiz /chat/{paper_id}, ahora los movemos a child de router o mantenemos)
# Para consistencia con prefix="/papers", esto quedaría como /papers/chat/{id} ?
# El main original tenía: POST /chat/{paper_id}
# Para no romper frontend, podemos hacer un router separado o ajustarlo aquí.
# El plan decía /post /chat/{id} en papers router.
# Si prefix es /papers, quedaria /papers/chat/{id}.
# CAMBIO IMPORTANTE: Frontend llama a /chat/{id}.
# Opción: Crear este endpoint SIN el prefix del router, o ajustar frontend.
# Ajustaremos el router para que incluya estos paths pero cuidado con el prefix global.
# Mejor estrategia: Router de papers maneja todo lo relacionado a papers.
# Pero si el frontend espera /chat/{id}, entonces aqui quedaria /papers/chat/{id} si uso router.
# Solución: Definir prefix solo para lo comun, y rutas absolutas para excepciones? No se puede facilemente.
# Solución B: Router papers con prefix="/papers".
# Router raiz para cosas sueltas?
# Voy a asumir que puedo cambiar el frontend o que la refactorización implica cambio de URL.
# PERO el usuario no pidió cambiar frontend.
# El frontend catalog.py linea 383: requests.post(f"{API_URL}/chat/{paper['id']}"...
# Entonces DEBO mantener las rutas originales o actualizar frontend.
# Voy a actualizar frontend también en esta pasada para ser consistente, o declarar rutas especificas.
# FastAPI router permite rutas que no empiezan con prefix si no se pone prefix al instanciar.
# PERO es mejor agrupar.
# Voy a hacer: router = APIRouter() sin prefix global, y definir endpoints explicitos.


@router.post("/chat/{paper_id}", tags=["chat"])
async def chat_paper(paper_id: str, payload: Dict[str, str]):
    """
    Endpoint para chatear con un paper específico.
    Payload: {"question": "¿Cuál es la conclusión?"}
    """
    question = payload.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Falta la pregunta")
        
    answer = analysis_core.chat_with_paper(paper_id, question)
    return {"answer": answer}
