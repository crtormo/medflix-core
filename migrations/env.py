"""
Alembic Environment Configuration for MedFlix Core

Este archivo configura cómo Alembic se conecta a la base de datos
y detecta cambios en los modelos SQLAlchemy.
"""

from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Agregar el directorio raíz al path para importar modelos
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Importar Base y todos los modelos para que Alembic los detecte
from models.paper import Base, Paper, get_database_url
from models.channel import Channel

# Configuración de Alembic desde alembic.ini
config = context.config

# Configurar logging si existe el archivo ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos para autogenerate
target_metadata = Base.metadata


def get_url():
    """
    Obtiene la URL de conexión desde variables de entorno.
    Prioriza la URL dinámica sobre la hardcodeada en alembic.ini
    """
    return get_database_url()


def run_migrations_offline() -> None:
    """
    Ejecuta migraciones en modo 'offline'.
    
    Genera SQL sin conectarse a la base de datos.
    Útil para generar scripts de migración para DBA.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detectar cambios de tipo de columna
        compare_server_default=True,  # Detectar cambios en defaults
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecuta migraciones en modo 'online'.
    
    Se conecta a la base de datos y aplica las migraciones.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
