import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from pathlib import Path
from core.analysis import AnalysisCore
from services.groq_service import GroqService
from services.reference_generator import ReferenceGenerator

# Configuración de Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Instancia global del Core
# En producción, gestionar esto con cuidado para threads/async
try:
    analysis_core = AnalysisCore()
except Exception as e:
    logging.error(f"Error inicializando AnalysisCore: {e}")
    analysis_core = None

UPLOAD_DIR = Path("data/uploads_telegram")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Generador de referencias
reference_generator = ReferenceGenerator()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 ¡Hola! Soy MedFlix Bot.\n\nEnvíame un archivo PDF para analizarlo con 'Auditoría Epistemológica' o hazme una pregunta para buscar en tu biblioteca."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not analysis_core:
        await update.message.reply_text("❌ El sistema de análisis no está disponible en este momento.")
        return

    document = update.message.document
    
    # Verificar que sea PDF
    if not document.mime_type == 'application/pdf':
        await update.message.reply_text("❌ Por favor, envía solo archivos PDF.")
        return

    # Mensaje de confirmación inicial
    status_msg = await update.message.reply_text("📥 Recibido. Descargando y analizando...")

    try:
        # Descargar archivo
        file = await context.bot.get_file(document.file_id)
        file_path = UPLOAD_DIR / document.file_name
        await file.download_to_drive(file_path)

        await context.bot.edit_message_text(f"🧠 Leyendo '{document.file_name}' y realizando Auditoría Epistemológica...", chat_id=update.effective_chat.id, message_id=status_msg.message_id)

        # Ejecutar análisis (esto en realidad bloqueará el loop principal si tarda mucho, 
        # idealmente usar run_in_executor para cpu-bound tasks)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, analysis_core.process_and_analyze, str(file_path))

        if result["status"] == "duplicate":
            await context.bot.edit_message_text(
                f"⚠️ *Duplicado detectado*\n\nEste paper ya está en tu biblioteca.\nRazón: {result['reason']}",
                chat_id=update.effective_chat.id, 
                message_id=status_msg.message_id,
                parse_mode='Markdown'
            )
        else:
            # Preparar un resumen bonito para telegram
            snippets = result.get("snippets", {})
            summary_text = (
                f"✅ *Análisis Completado*\n\n"
                f"📄 *Paper*: {document.file_name}\n"
                f"👥 *N*: {snippets.get('n_study', 'N/A')}\n"
                f"💊 *NNT*: {snippets.get('nnt', 'N/A')}\n\n"
                f"💡 *Resumen*: {snippets.get('summary_slide', 'N/A')}\n\n"
                f"🔎 *Veredicto Auditoría*:\nVer app web para detalle completo."
            )
            
            # Enviar resumen
            await context.bot.edit_message_text(
                summary_text,
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                parse_mode='Markdown'
            )
            
            # Enviar archivo de texto con la auditoría completa si es muy largo
            if result.get("analysis"):
                full_analysis = result["analysis"]
                # Telegram tiene limite de 4096 chars. Si es más largo, enviamos chunks o archivo.
                # Para simplificar, enviamos los primeros 3000 chars como mensaje extra o creamos un txt virtual
                if len(full_analysis) > 3000:
                   await update.message.reply_text(f"📝 *Auditoría Detallada (Extracto)*:\n\n{full_analysis[:3000]}...", parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"📝 *Auditoría Detallada*:\n\n{full_analysis}", parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error processing file: {e}")
        await context.bot.edit_message_text(f"❌ Ocurrió un error al procesar el archivo: {str(e)}", chat_id=update.effective_chat.id, message_id=status_msg.message_id)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja consultas de texto (RAG simple)"""
    if not analysis_core:
        await update.message.reply_text("❌ El sistema no está disponible.")
        return

    query = update.message.text
    
    await update.message.reply_chat_action("typing")
    
    # Consulta a ChromaDB
    results = analysis_core.vector_store.query_similar(query, n_results=3)
    
    if not results['ids'][0]:
        await update.message.reply_text("No encontré papers relacionados en tu biblioteca.")
        return

    response_text = "📚 *Papers encontrados:*\n\n"
    for i, doc_id in enumerate(results['ids'][0]):
        meta = results['metadatas'][0][i]
        title = meta.get('title', 'Sin título')
        author = meta.get('author', 'Autor desconocido')
        response_text += f"🔹 *{title}* ({author})\n"
    
    await update.message.reply_text(response_text, parse_mode='Markdown')

async def citar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /citar {doc_id} - Genera cita Vancouver para un paper
    Uso: /citar abc123 o /citar abc123 apa
    """
    if not analysis_core:
        await update.message.reply_text("❌ El sistema no está disponible.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "📝 *Uso:* `/citar {doc_id} [estilo]`\n\n"
            "Ejemplo: `/citar abc123` o `/citar abc123 apa`\n"
            "Estilos disponibles: vancouver (default), apa",
            parse_mode='Markdown'
        )
        return
    
    doc_id = args[0]
    style = args[1] if len(args) > 1 else "vancouver"
    
    # Buscar documento
    results = analysis_core.vector_store.collection.get(ids=[doc_id])
    
    if not results['ids']:
        await update.message.reply_text(f"❌ No encontré un documento con ID: {doc_id}")
        return
    
    metadata = results['metadatas'][0] if results['metadatas'] else {}
    citation = reference_generator.generate_citation(metadata, style=style)
    
    await update.message.reply_text(
        f"📋 *Cita ({style.upper()}):*\n\n`{citation}`",
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN no encontrada en variables de entorno.")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        
        start_handler = CommandHandler('start', start)
        citar_handler = CommandHandler('citar', citar_command)
        doc_handler = MessageHandler(filters.Document.PDF, handle_document)
        text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
        
        application.add_handler(start_handler)
        application.add_handler(citar_handler)
        application.add_handler(doc_handler)
        application.add_handler(text_handler)
        
        print("Bot iniciado. Escuchando...")
        application.run_polling()
