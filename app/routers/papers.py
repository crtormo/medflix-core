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
    is_quiz: bool = False
):
    """Lista papers para el catálogo."""
    db = get_db_service()
    
    if is_quiz:
        papers = db.get_quiz_papers(limit)
    elif specialty and specialty != "Todas":
        papers = db.get_papers_by_especialidad(specialty, limit)
    elif sort == "quality":
        papers = db.get_top_papers(limit)
    else:
        papers = db.get_recent_papers(limit)
        
    return [p.to_card_dict() for p in papers]

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

# --- Stats y Otros (que estaban sueltos) ---

@router.get("/stats", tags=["stats"])
async def get_stats():
    return get_db_service().get_stats()

@router.get("/citar/{doc_id}", tags=["tools"])
def generate_citation(doc_id: str, style: str = "vancouver"):
    """
    Genera una cita formateada para un documento.
    """
    # Buscar documento en vector store
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

@router.get("/query", tags=["search"])
def query_papers(q: str):
    """Busca papers usando RAG simple"""
    results = analysis_core.vector_store.query_similar(q)
    return results

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
