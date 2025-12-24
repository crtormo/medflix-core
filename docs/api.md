# Documentación de API - MedFlix Core

## Descripción General
Esta API proporciona los servicios backend para MedFlix Core, incluyendo la gestión de papers médicos, análisis con IA (Groq), ingesta desde Telegram y funcionalidades de chat (RAG).

**Base URL**: `http://localhost:8005` (por defecto en desarrollo)

---

## 📚 Papers

### Subir Paper
Sube un archivo PDF para su procesamiento asíncrono.
- **Endpoint**: `POST /upload`
- **Body**: `Multipart/Form-Data` (`file`: PDF)
- **Respuesta**:
  ```json
  {
    "status": "pendiente",
    "job_id": "uuid-string",
    "message": "Archivo recibido..."
  }
  ```

### Listar Papers
Obtiene el catálogo de papers con opciones de filtrado y paginación.
- **Endpoint**: `GET /papers`
- **Query Params**:
  - `limit` (int, default: 20)
  - `offset` (int, default: 0)
  - `specialty` (str, opcional)
  - `sort` (str: "recent" | "quality")
- **Respuesta**: Lista de objetos `Paper` simplificados (Card format).

### Detalle de Paper
Obtiene la información completa de un paper.
- **Endpoint**: `GET /papers/{paper_id}`
- **Respuesta**: Objeto completo del Paper.

### Actualizar Metadatos
Actualiza manualmente campos específicos de un paper.
- **Endpoint**: `PUT /papers/{paper_id}`
- **Body**:
  ```json
  {
    "titulo": "Nuevo Título",
    "especialidad": "Cardiología"
  }
  ```

### Chatear con Paper (RAG)
Realiza preguntas específicas sobre el contenido de un paper.
- **Endpoint**: `POST /chat/{paper_id}`
- **Body**:
  ```json
  {
    "question": "¿Cuál es la dosis recomendada?"
  }
  ```
- **Respuesta**:
  ```json
  {
    "answer": "Según el estudio, la dosis es..."
  }
  ```

---

## 📢 Canales de Telegram

### Listar Canales
- **Endpoint**: `GET /channels`

### Añadir Canal
- **Endpoint**: `POST /channels`
- **Query Params**: `username` (ej: `@canal`), `nombre` (opcional)

### Eliminar Canal
- **Endpoint**: `DELETE /channels/{username}`

### Iniciar Escaneo Manual
Fuerza el escaneo de nuevos mensajes en los canales configurados.
- **Endpoint**: `POST /scan-channels`
- **Respuesta**: `{"status": "started"}`

### Estado de Escaneo
Consulta el progreso del escaneo en tiempo real.
- **Endpoint**: `GET /scan-status`
- **Respuesta**:
  ```json
  {
    "is_scanning": true,
    "current_channel": "@canal",
    "logs": ["..."],
    "stats": {...}
  }
  ```

---

## 📊 Sistema & Estadísticas

### Health Check
- **Endpoint**: `GET /health`

### Estadísticas Globales
Resumen de la base de datos.
- **Endpoint**: `GET /stats`
- **Respuesta**:
  ```json
  {
    "total_papers": 150,
    "procesados": 145,
    "especialidades_breakdown": {"UCI": 20, "Cardio": 10},
    "score_promedio": 8.5
  }
  ```

### Generar Cita
Genera una referencia bibliográfica.
- **Endpoint**: `GET /citar/{doc_id}`
- **Query Params**: `style` ("vancouver" | "apa")
