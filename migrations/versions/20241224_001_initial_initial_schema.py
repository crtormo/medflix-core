"""Migración inicial con esquema completo de MedFlix

Esta migración crea las tablas papers y channels con todas las columnas
definidas en los modelos actuales. Debe ejecutarse una sola vez en 
bases de datos nuevas o después de respaldar datos existentes.

Revision ID: 001_initial
Revises: 
Create Date: 2024-12-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Tabla: papers ###
    op.create_table(
        'papers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('hash', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('doi', sa.String(100), index=True),
        
        # Metadatos del Paper
        sa.Column('titulo', sa.Text(), nullable=False),
        sa.Column('autores', postgresql.JSONB(), server_default='[]'),
        sa.Column('revista', sa.String(300)),
        sa.Column('año', sa.Integer(), index=True),
        sa.Column('abstract', sa.Text()),
        
        # Clasificación
        sa.Column('tipo_estudio', sa.String(50), index=True),
        sa.Column('especialidad', sa.String(100), index=True),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        
        # Datos del Estudio
        sa.Column('n_muestra', sa.String(50)),
        sa.Column('nnt', sa.String(50)),
        sa.Column('poblacion', sa.String(200)),
        
        # Metadatos Enriquecidos
        sa.Column('impact_factor', sa.String(50)),
        sa.Column('fecha_publicacion_exacta', sa.String(20)),
        
        # Metadatos Multi-Fuente (Fase 8)
        sa.Column('pmid', sa.String(20), index=True),
        sa.Column('mesh_terms', postgresql.JSONB(), server_default='[]'),
        sa.Column('abstract_estructurado', postgresql.JSONB(), server_default='{}'),
        sa.Column('affiliaciones', postgresql.JSONB(), server_default='[]'),
        sa.Column('funders', postgresql.JSONB(), server_default='[]'),
        sa.Column('license', sa.String(500)),
        sa.Column('referencias', postgresql.JSONB(), server_default='[]'),
        sa.Column('crossmark_status', sa.String(50)),
        sa.Column('metadata_source', sa.String(50)),
        sa.Column('doi_validado', sa.Boolean(), server_default='false'),
        
        # Análisis IA
        sa.Column('veredicto_ia', sa.String(100)),
        sa.Column('resumen_slide', sa.Text()),
        sa.Column('analisis_completo', sa.Text()),
        sa.Column('score_calidad', sa.Float()),
        
        # EKG Dojo / Quiz Mode
        sa.Column('is_quiz', sa.Boolean(), server_default='false', index=True),
        sa.Column('quiz_data', postgresql.JSONB(), server_default='{}'),
        
        # Imágenes y Gráficos
        sa.Column('thumbnail_path', sa.String(500)),
        sa.Column('imagenes', postgresql.JSONB(), server_default='[]'),
        sa.Column('num_graficos', sa.Integer(), server_default='0'),
        sa.Column('analisis_graficos', postgresql.JSONB(), server_default='[]'),
        
        # Archivo Original
        sa.Column('archivo_path', sa.String(500)),
        sa.Column('archivo_nombre', sa.String(300)),
        sa.Column('num_paginas', sa.Integer()),
        
        # Timestamps
        sa.Column('fecha_subida', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('fecha_analisis', sa.DateTime()),
        
        # Estado
        sa.Column('procesado', sa.Boolean(), server_default='false'),
    )
    
    # ### Tabla: channels ###
    op.create_table(
        'channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('nombre', sa.String(200)),
        sa.Column('last_scanned_id', sa.Integer(), server_default='0'),
        sa.Column('last_scan_date', sa.DateTime()),
        sa.Column('active', sa.Boolean(), server_default='true'),
        sa.Column('added_date', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('channels')
    op.drop_table('papers')
