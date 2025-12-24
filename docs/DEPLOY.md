# Proceso de Deploy Seguro

Este documento describe el proceso de deployment para MedFlix en producción.

## Pre-requisitos

- Docker y Docker Compose instalados
- Acceso a servidor de producción
- Variables de entorno configuradas

## Verificación Pre-Deploy

Antes de cualquier deploy, ejecutar:

```bash
python scripts/pre_deploy_check.py
```

Este script verifica:
- ✅ Configuración de `.env`
- ✅ Sintaxis de código Python
- ✅ Dependencias en `requirements.txt`
- ✅ Migraciones de Alembic
- ✅ Modo DEBUG deshabilitado
- ✅ Tests pasando

## Pasos de Deploy

### 1. Preparar ambiente
```bash
# Clonar o actualizar código
git pull origin master

# Verificar pre-deploy
python scripts/pre_deploy_check.py
```

### 2. Backup de base de datos
```bash
docker exec medflix-db pg_dump -U medflix medflix_db > backup_$(date +%Y%m%d).sql
```

### 3. Aplicar migraciones
```bash
docker exec medflix-api alembic upgrade head
```

### 4. Construir y desplegar
```bash
docker-compose build
docker-compose up -d
```

### 5. Verificar deployment
```bash
# Health check
curl http://localhost:8005/health

# Verificar logs
docker-compose logs -f --tail=100
```

## Rollback

En caso de problemas:

```bash
# Detener servicios
docker-compose down

# Restaurar backup
cat backup_YYYYMMDD.sql | docker exec -i medflix-db psql -U medflix medflix_db

# Revertir migración
docker exec medflix-api alembic downgrade -1

# Volver a versión anterior
git checkout <commit-anterior>
docker-compose up -d
```

## Checklist de Deploy

- [ ] Pre-deploy check pasó
- [ ] Backup de BD realizado
- [ ] Migraciones aplicadas
- [ ] Servicios reiniciados
- [ ] Health check OK
- [ ] Prueba manual de funcionalidad crítica
