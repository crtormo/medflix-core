
from typing import Dict, Any
from datetime import datetime

class ScanStatusManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScanStatusManager, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance
    
    def reset(self):
        self.status = {
            "active": False,
            "channel": None,
            "message": "Esperando inicio...",
            "stats": {
                "total_canales": 0,
                "canal_actual": 0,
                "nuevos_descargados": 0,
                "duplicados": 0,
                "errores": 0
            },
            "last_log": [],
            "start_time": None
        }

    def start_scan(self, total_channels=0):
        self.reset()
        self.status["active"] = True
        self.status["stats"]["total_canales"] = total_channels
        self.status["start_time"] = datetime.now().isoformat()
        self.log("🚀 Iniciando escaneo de canales...")

    def end_scan(self, stats_final):
        self.status["active"] = False
        self.status["message"] = "Escaneo finalizado"
        self.log(f"🏁 Finalizado. Nuevos: {stats_final.get('processed',0)}. Duplicados: {stats_final.get('existing',0)}")

    def update_channel(self, channel_name, progress_idx):
        self.status["channel"] = channel_name
        self.status["stats"]["canal_actual"] = progress_idx
        self.log(f"📥 Escaneando canal: {channel_name}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        self.status["last_log"].append(entry)
        # Mantener solo ultimos 50 logs
        if len(self.status["last_log"]) > 50:
            self.status["last_log"].pop(0)
        self.status["message"] = msg

# Global instance
scan_status = ScanStatusManager()
