# Migraciones de Base de Datos con Alembic

Este documento describe cómo gestionar migraciones de esquema en MedFlix.

## Requisitos

```bash
pip install alembic
```

## Comandos Básicos

### Ver estado actual
```bash
alembic current
```

### Aplicar todas las migraciones pendientes
```bash
alembic upgrade head
```

### Revertir última migración
```bash
alembic downgrade -1
```

### Crear nueva migración
```bash
alembic revision -m "descripcion_del_cambio"
```

## Flujo de Trabajo

### 1. Modificar el modelo
Edita `models/paper.py` con los nuevos campos.

### 2. Crear migración
```bash
alembic revision -m "add_nuevo_campo"
```

### 3. Editar migración generada
Abre `migrations/versions/xxx_add_nuevo_campo.py` y añade:

```python
def upgrade():
    op.add_column('papers', sa.Column('nuevo_campo', sa.String(100)))

def downgrade():
    op.drop_column('papers', 'nuevo_campo')
```

### 4. Aplicar migración
```bash
alembic upgrade head
```

## Migraciones Existentes

| Revisión | Fecha | Descripción |
|----------|-------|-------------|
| 001_initial | 2024-12-24 | Esquema completo inicial (papers, channels) |

## Troubleshooting

### Error: "Target database is not up to date"
Ejecuta `alembic upgrade head` para sincronizar.

### Error: "Can't locate revision"
Verifica que la variable `POSTGRES_*` esté configurada correctamente.
