"""
Servicio de Base de Datos para MedFlix Core
Maneja operaciones CRUD sobre PostgreSQL
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, desc, or_
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from contextlib import contextmanager

from models.paper import Paper, Base, get_database_url
from models.channel import Channel

logger = logging.getLogger(__name__)



class DatabaseService:
    """Servicio para interactuar con PostgreSQL."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or get_database_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def init_db(self):
        """Crea las tablas si no existen."""
        Base.metadata.create_all(self.engine)
        logger.info("Base de datos inicializada correctamente.")
        
    @contextmanager
    def get_session(self) -> Session:
        """Context manager para sesiones de base de datos."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error en sesión de base de datos: {e}")
            raise
        finally:
            session.close()
    
    # ==================== CREATE ====================
    
    def create_paper(self, **kwargs) -> Paper:
        """Crea un nuevo paper en la base de datos."""
        with self.get_session() as session:
            paper = Paper(**kwargs)
            session.add(paper)
            session.flush()
            session.commit()
            session.refresh(paper)
            session.expunge(paper)
            return paper
    
    # ==================== READ ====================
    
    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """Obtiene un paper por su ID."""
        with self.get_session() as session:
            paper = session.query(Paper).filter(Paper.id == paper_id).first()
            if paper:
                session.expunge(paper)  # Desacoplar del session
            return paper
    
    def get_paper_by_hash(self, hash_value: str) -> Optional[Paper]:
        """Obtiene un paper por su hash (para detectar duplicados)."""
        with self.get_session() as session:
            paper = session.query(Paper).filter(Paper.hash == hash_value).first()
            if paper:
                session.expunge(paper)
            return paper
    
    def get_all_papers(self, limit: int = 100, offset: int = 0) -> List[Paper]:
        """Obtiene todos los papers con paginación."""
        with self.get_session() as session:
            papers = session.query(Paper)\
                .order_by(desc(Paper.fecha_subida))\
                .offset(offset)\
                .limit(limit)\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers
    
    def get_recent_papers(self, limit: int = 10) -> List[Paper]:
        """Obtiene los papers más recientes."""
        with self.get_session() as session:
            papers = session.query(Paper)\
                .filter(Paper.procesado == True)\
                .order_by(desc(Paper.fecha_analisis))\
                .limit(limit)\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers
    
    def get_papers_by_especialidad(self, especialidad: str, limit: int = 20) -> List[Paper]:
        """Obtiene papers filtrados por especialidad."""
        with self.get_session() as session:
            papers = session.query(Paper)\
                .filter(Paper.especialidad == especialidad)\
                .filter(Paper.procesado == True)\
                .order_by(desc(Paper.score_calidad))\
                .limit(limit)\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers
    
    def get_all_especialidades(self) -> List[str]:
        """Obtiene lista única de especialidades."""
        with self.get_session() as session:
            result = session.query(Paper.especialidad)\
                .filter(Paper.especialidad.isnot(None))\
                .distinct()\
                .all()
            return [e[0] for e in result if e[0]]
    
    def search_papers(self, query: str, limit: int = 20) -> List[Paper]:
        """Búsqueda por título, autores o tags."""
        with self.get_session() as session:
            search_term = f"%{query}%"
            papers = session.query(Paper)\
                .filter(
                    or_(
                        Paper.titulo.ilike(search_term),
                        Paper.autores.cast(str).ilike(search_term),
                        Paper.tags.cast(str).ilike(search_term)
                    )
                )\
                .order_by(desc(Paper.fecha_subida))\
                .limit(limit)\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers
    
    def get_papers_by_year(self, year: int) -> List[Paper]:
        """Obtiene papers de un año específico."""
        with self.get_session() as session:
            papers = session.query(Paper)\
                .filter(Paper.año == year)\
                .filter(Paper.procesado == True)\
                .order_by(desc(Paper.score_calidad))\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers
    
    def get_papers_by_tipo_estudio(self, tipo: str) -> List[Paper]:
        """Obtiene papers por tipo de estudio (RCT, Cohorte, etc.)."""
        with self.get_session() as session:
            papers = session.query(Paper)\
                .filter(Paper.tipo_estudio == tipo)\
                .filter(Paper.procesado == True)\
                .order_by(desc(Paper.score_calidad))\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers
    
    def get_top_papers(self, limit: int = 10) -> List[Paper]:
        """Obtiene los papers con mayor score de calidad."""
        with self.get_session() as session:
            papers = session.query(Paper)\
                .filter(Paper.procesado == True)\
                .filter(Paper.score_calidad.isnot(None))\
                .order_by(desc(Paper.score_calidad))\
                .limit(limit)\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers

    def get_quiz_papers(self, limit: int = 50) -> List[Paper]:
        """Obtiene papers marcados como Quiz (EKG Dojo)."""
        with self.get_session() as session:
            papers = session.query(Paper)\
                .filter(Paper.is_quiz == True)\
                .order_by(desc(Paper.fecha_subida))\
                .limit(limit)\
                .all()
            for paper in papers:
                session.expunge(paper)
            return papers
    
    def count_papers(self) -> int:
        """Cuenta el total de papers."""
        with self.get_session() as session:
            return session.query(Paper).count()
    
    # ==================== UPDATE ====================
    
    def update_paper(self, paper_id: str, **kwargs) -> Optional[Paper]:
        """Actualiza campos de un paper existente."""
        with self.get_session() as session:
            paper = session.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                return None
            
            for key, value in kwargs.items():
                if hasattr(paper, key):
                    setattr(paper, key, value)
            
            session.commit()
            session.refresh(paper)
            # Access attributes to force load
            _ = paper.id
            _ = paper.titulo
            _ = paper.procesado
            _ = paper.score_calidad
            session.expunge(paper)
            return paper
    
    def mark_as_processed(self, paper_id: str, analysis_data: Dict[str, Any]) -> Optional[Paper]:
        """Marca un paper como procesado y guarda el análisis."""
        return self.update_paper(
            paper_id,
            procesado=True,
            fecha_analisis=datetime.utcnow(),
            analisis_completo=analysis_data.get("analisis_completo"),
            resumen_slide=analysis_data.get("resumen_slide"),
            score_calidad=analysis_data.get("score_calidad"),
            tipo_estudio=analysis_data.get("tipo_estudio"),
            especialidad=analysis_data.get("especialidad"),
            n_muestra=analysis_data.get("n_muestra"),
            nnt=analysis_data.get("nnt"),
            imagenes=analysis_data.get("imagenes"),
            num_graficos=analysis_data.get("num_graficos"),
            analisis_graficos=analysis_data.get("analisis_graficos")
        )
    
    # ==================== DELETE ====================
    
    def delete_paper(self, paper_id: str) -> bool:
        """Elimina un paper de la base de datos."""
        with self.get_session() as session:
            paper = session.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                return False
            session.delete(paper)
            session.commit()
            return True
    
    # ==================== STATS ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales del catálogo."""
        with self.get_session() as session:
            total = session.query(Paper).count()
            procesados = session.query(Paper).filter(Paper.procesado == True).count()
            con_graficos = session.query(Paper).filter(Paper.num_graficos > 0).count()
            
            especialidades = session.query(Paper.especialidad)\
                .filter(Paper.especialidad.isnot(None))\
                .distinct()\
                .count()
            
            avg_score = 0
            scores = session.query(Paper.score_calidad)\
                .filter(Paper.score_calidad.isnot(None))\
                .all()
            if scores:
                avg_score = sum(s[0] for s in scores) / len(scores)
            
            # Breakdown por especialidad
            from sqlalchemy import func
            breakdown = session.query(Paper.especialidad, func.count(Paper.id))\
                .filter(Paper.procesado == True)\
                .group_by(Paper.especialidad)\
                .all()
            spec_stats = {b[0]: b[1] for b in breakdown if b[0]}

            return {
                "total_papers": total,
                "procesados": procesados,
                "pendientes": total - procesados,
                "con_graficos": con_graficos,
                "especialidades": especialidades,
                "especialidades_breakdown": spec_stats,
                "score_promedio": round(avg_score, 2)
            }
    
    # ==================== CHANNELS ====================

    def add_channel(self, username: str, nombre: Optional[str] = None) -> Channel:
        """Añade un nuevo canal de Telegram."""
        with self.get_session() as session:
            # Check si existe
            existing = session.query(Channel).filter(Channel.username == username).first()
            if existing:
                if not existing.active: # Si existía pero estaba inactivo, reactivar
                    existing.active = True
                    session.commit()
                # Refrescar y de-asociar
                session.refresh(existing)
                session.expunge(existing)
                return existing

            channel = Channel(username=username, nombre=nombre or username)
            session.add(channel)
            session.commit()
            session.refresh(channel)
            session.expunge(channel)
            return channel

    def get_all_channels(self) -> List[Channel]:
        """Obtiene todos los canales monitoreados."""
        with self.get_session() as session:
            channels = session.query(Channel).filter(Channel.active == True).all()
            # Force load attributes before expunge
            for ch in channels:
                _ = ch.id
                _ = ch.username
                _ = ch.last_scan_date
                session.expunge(ch)
            return channels

    def update_channel_scan(self, channel_id: str, last_msg_id: int):
        """Actualiza el puntero de escaneo de un canal."""
        with self.get_session() as session:
            channel = session.query(Channel).filter(Channel.id == channel_id).first()
            if channel:
                channel.last_scanned_id = max(channel.last_scanned_id, last_msg_id)
                channel.last_scan_date = datetime.utcnow()
                session.commit()

    def delete_channel(self, username: str):
        """Desactiva (soft delete) un canal."""
        with self.get_session() as session:
            channel = session.query(Channel).filter(Channel.username == username).first()
            if channel:
                channel.active = False
                session.commit()


# Singleton para uso global
_db_service = None

def get_db_service() -> DatabaseService:
    """Obtiene la instancia global del servicio de base de datos."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
        _db_service.init_db()
    return _db_service
