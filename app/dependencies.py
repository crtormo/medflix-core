from typing import Dict
from core.analysis import AnalysisCore
from services.reference_generator import ReferenceGenerator

# Inicializar Core y servicios (Singleton instances)
# Se instancian aquí para ser importados por los routers y main.py
analysis_core = AnalysisCore()
reference_generator = ReferenceGenerator()

# Memoria simple de Jobs (en prod usar Redis/DB)
# Estructura: job_id -> {status, result, message}
jobs_db: Dict[str, Dict] = {}
