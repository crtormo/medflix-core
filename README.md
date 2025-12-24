# 🧬 MedFlix Core

> **Plataforma de Auditoría Epistemológica de Papers Médicos impulsada por IA.**
> *Desencadena la verdad científica con el estilo de Netflix.*

![MedFlix Banner](https://via.placeholder.com/1200x400/141414/46d369?text=MEDFLIX+CORE+|+Auditoria+Epistemologica)

**MedFlix Core** es un sistema integral para la ingestión, análisis y visualización crítica de literatura médica. Utiliza Modelos de Lenguaje Grande (LLMs) a través de Groq para realizar "Auditorías Epistemológicas", detectando sesgos, conflictos de interés y fallas metodológicas en papers científicos, presentándolos en una interfaz moderna y accesible.

---

## 🚀 Características Principales

- **🧠 Auditoría Epistemológica con IA**: Análisis profundo utilizando Llama-3 (vía Groq) para evaluar validez interna/externa, sesgos y relevancia clínica.
- **🎬 Interfaz "Netflix-Style"**: Catálogo visual oscuro y moderno para explorar tu biblioteca médica.
- **🤖 Bot de Telegram & UserBot**: Auto-ingestión de papers desde canales de Telegram y subida directa vía chat personal.
- **🔍 Búsqueda Semántica (RAG)**: Encuentra respuestas exactas dentro de miles de papers usando ChromaDB.
- **📊 Dashboard de Métricas**: Visualización de scores de calidad, rigor metodológico e impacto innovador.
- **📚 Generador de Citas**: Exportación automática a formatos Vancouver y APA.

## 🛠️ Stack Tecnológico

- **Backend**: FastAPI (Python 3.10+)
- **Base de Datos**: PostgreSQL 16 (SQLAlchemy ORM)
- **Vector Store**: ChromaDB (AI Embeddings)
- **LLM Engine**: Groq API (Llama-3.3-70b-versatile / 8b-instant)
- **Frontend**: Streamlit
- **PDF Processing**: PyMuPDF (Fitz)
- **Integraciones**: Telethon (Telegram Client API)
- **Infraestructura**: Docker & Docker Compose

---

## ⚡ Guía de Inicio Rápido

### Prerrequisitos
- Docker & Docker Compose
- Groq API Key
- Telegram API ID/Hash (para el bot)

### 1. Instalación con Docker (Recomendado)

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/crtormo/medflix-core.git
   cd medflix-core
   ```

2. **Configurar Variables de Entorno:**
   ```bash
   cp .env.example .env
   # Edita .env con tus credenciales (ver sección Configuración)
   ```

3. **Desplegar Servicios:**
   ```bash
   docker-compose up -d --build
   ```

4. **Acceder:**
   - 🖥️ **Web UI:** [http://localhost:8502](http://localhost:8502)
   - 🔌 **API Docs:** [http://localhost:8005/docs](http://localhost:8005/docs)
   - 🗄️ **Base de Datos:** Puerto 5433

### 2. Instalación Local (Desarrollo)

1. **Crear entorno virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Levantar Base de Datos (requiere Postgres corriendo):**
   Asegúrate de que las credenciales en `.env` apunten a tu instancia local de Postgres.

3. **Iniciar Servicios:**
   ```bash
   # Terminal 1: API
   uvicorn app.main:app --reload --port 8005

   # Terminal 2: UI
   streamlit run ui/catalog.py --server.port 8502

   # Terminal 3: Bot (Opcional)
   python -m services.telegram_bot
   ```

---

## ⚙️ Configuración (.env)

| Variable | Descripción | Valor Ejemplo |
|----------|-------------|---------------|
| `GROQ_API_KEY` | Key para acceso a LLMs | `gsk_...` |
| `TELEGRAM_BOT_TOKEN` | Token del Bot (BotFather) | `123456:ABC...` |
| `TELEGRAM_API_ID` | App ID para UserBot | `12345` |
| `TELEGRAM_API_HASH` | App Hash para UserBot | `abcde12345...` |
| `POSTGRES_USER` | Usuario DB | `medflix` |
| `POSTGRES_PASSWORD` | Password DB | `secret` |
| `POSTGRES_DB` | Nombre DB | `medflix_db` |
| `POSTGRES_HOST` | Host DB (docker service name) | `db` |

---

## 📂 Estructura del Proyecto

```
medflix-core/
├── app/                # FastAPI Application
│   ├── main.py         # Entry point API
│   └── schemas.py      # Pydantic models
├── core/               # Lógica Cognitiva
│   ├── analysis.py     # Orquestador de análisis
│   ├── ingestion.py    # Procesamiento PDF
│   └── visual_analysis.py # Análisis de gráficos VLM
├── models/             # Modelos DB (SQLAlchemy)
├── services/           # Servicios Externos
│   ├── database.py     # CRUD PostgreSQL
│   ├── groq_service.py # Cliente LLM & Rate Limiter
│   ├── telegram_bot.py # Bot Interactivo
│   └── vector_store.py # RAG / ChromaDB
├── ui/                 # Frontend Streamlit
│   └── catalog.py      # Interfaz Principal
└── docker-compose.yml  # Orquestación Contenedores
```

## 🤝 Contribución

¡Bienvenido! Por favor lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles sobre nuestro código de conducta y el proceso para enviarnos pull requests.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE.md](LICENSE.md) para detalles.

---
*Desarrollado con ❤️ y Cafeína para la Ciencia Médica.*
