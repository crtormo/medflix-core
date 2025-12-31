import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_ADMIN_ID") or os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(self, text: str, parse_mode: str = "Markdown"):
        if not self.bot_token or not self.chat_id:
            logger.warning("NotificationService: TOKEN o CHAT_ID no configurados.")
            return False

        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")
            return False

    def send_practice_changing_alert(self, paper_data: Any):
        """
        Versión sincrónica para ser llamada desde el core de análisis.
        """
        import asyncio
        
        titulo = paper_data.titulo if hasattr(paper_data, 'titulo') else paper_data.get('titulo', 'Sin título')
        score = paper_data.score_calidad if hasattr(paper_data, 'score_calidad') else paper_data.get('score_calidad', 0)
        insights = paper_data.clinical_insights if hasattr(paper_data, 'clinical_insights') else paper_data.get('clinical_insights', {})
        
        bottom_line = insights.get('bottom_line', 'N/A')
        grade = insights.get('grade', 'N/A')

        message = (
            "🚨 *NUEVA EVIDENCIA CRÍTICA (Score > 9.0)* 🚨\n\n"
            f"📄 *Título*: {titulo}\n"
            f"⭐ *Calidad*: {score}/10\n"
            f"🎓 *Grado*: {grade}\n\n"
            f"💡 *Bottom Line*: {bottom_line}\n\n"
            "🔍 _Revisa el análisis completo en MedFlix Web._"
        )
        
        try:
            # Dado que el Core es síncrono por ahora, forzamos un loop o usamos una llamada síncrona de httpx
            with httpx.Client() as client:
                url = f"{self.api_url}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                client.post(url, json=payload)
                logger.info(f"🚀 Alerta proactiva enviada para: {titulo}")
        except Exception as e:
            logger.error(f"Error en alerta proactiva: {e}")
