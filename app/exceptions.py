"""
Excepciones personalizadas para MedFlix Core.
Proporciona una jerarquía de errores para manejo consistente.
"""


class MedFlixError(Exception):
    """Excepción base para todos los errores de MedFlix."""
    
    def __init__(self, message: str, code: str = "MEDFLIX_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class PaperNotFoundError(MedFlixError):
    """El paper solicitado no existe en la base de datos."""
    
    def __init__(self, paper_id: str):
        super().__init__(
            message=f"Paper con ID '{paper_id}' no encontrado",
            code="PAPER_NOT_FOUND"
        )
        self.paper_id = paper_id


class DOIEnrichmentError(MedFlixError):
    """Error durante el proceso de enriquecimiento de metadatos via DOI."""
    
    def __init__(self, doi: str, reason: str):
        super().__init__(
            message=f"Error enriqueciendo DOI '{doi}': {reason}",
            code="DOI_ENRICHMENT_FAILED"
        )
        self.doi = doi
        self.reason = reason


class DOIValidationError(MedFlixError):
    """El DOI proporcionado no es válido o no se puede resolver."""
    
    def __init__(self, doi: str, reason: str = "DOI inválido o no resoluble"):
        super().__init__(
            message=f"DOI '{doi}' no válido: {reason}",
            code="DOI_VALIDATION_FAILED"
        )
        self.doi = doi


class DatabaseError(MedFlixError):
    """Error de conexión o operación con la base de datos."""
    
    def __init__(self, operation: str, detail: str = ""):
        super().__init__(
            message=f"Error de base de datos en '{operation}': {detail}",
            code="DATABASE_ERROR"
        )
        self.operation = operation


class ChannelNotFoundError(MedFlixError):
    """El canal de Telegram no existe."""
    
    def __init__(self, username: str):
        super().__init__(
            message=f"Canal '{username}' no encontrado",
            code="CHANNEL_NOT_FOUND"
        )
        self.username = username


class FileProcessingError(MedFlixError):
    """Error al procesar un archivo (PDF, imagen, etc.)."""
    
    def __init__(self, filename: str, reason: str):
        super().__init__(
            message=f"Error procesando archivo '{filename}': {reason}",
            code="FILE_PROCESSING_ERROR"
        )
        self.filename = filename
        self.reason = reason


class ExternalServiceError(MedFlixError):
    """Error al comunicarse con un servicio externo (PubMed, CrossRef, Groq)."""
    
    def __init__(self, service: str, reason: str):
        super().__init__(
            message=f"Error en servicio externo '{service}': {reason}",
            code="EXTERNAL_SERVICE_ERROR"
        )
        self.service = service
        self.reason = reason
