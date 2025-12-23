# Configuración Inicial de MedFlix Core

## 1. Obtener Token de Telegram
1. Abre Telegram y busca al usuario **@BotFather**.
2. Envía el comando `/newbot`.
3. Sigue las instrucciones:
   - Elige un nombre visible para tu bot (ej: `MedFlix Bot`).
   - Elige un username único que termine en `bot` (ej: `MiMedFlixBot`).
4. BotFather te responderá con un mensaje que contiene tu **HTTP API Token**.
5. Copia este token.

## 2. Configurar Variables de Entorno
1. Copia el archivo `.env.example` a `.env`:
   ```bash
   cp .env.example .env
   ```
2. Pega tu Token de Telegram en `TELEGRAM_BOT_TOKEN`.
3. Pega tu API Key de Groq en `GROQ_API_KEY`.
