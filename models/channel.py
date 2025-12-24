from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from .paper import Base

class Channel(Base):
    """Modelo para canales de Telegram monitoreados."""
    __tablename__ = 'channels'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    nombre = Column(String(200))  # Nombre display del canal
    
    # Control de escaneo
    last_scanned_id = Column(Integer, default=0)  # ID del último mensaje procesado
    last_scan_date = Column(DateTime)
    
    active = Column(Boolean, default=True)
    added_date = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "username": self.username,
            "nombre": self.nombre,
            "last_scanned_id": self.last_scanned_id,
            "last_scan_date": self.last_scan_date.isoformat() if self.last_scan_date else None,
            "active": self.active
        }
