
from services.database import get_db_service

def seed_ecg():
    db = get_db_service()
    
    # Canales específicos de ECG / Cardio
    ecg_channels = [
        ("@dailycardiology", "Daily Cardiology (ECG & Cases)"),
        ("@ecgcases", "ECG Cases (Challenges)"),
        ("@ECG_Quiz", "ECG Quiz Bot Channel"), # Intentar
        ("@Cardiology", "Cardiology Updates"),
        ("@DrNajeebNotes", "Medical Notes & ECG") # General pero util
    ]
    
    print(f"🫀 Iniciando carga de {len(ecg_channels)} canales de ECG...")
    
    for username, name in ecg_channels:
        try:
            ch = db.add_channel(username, name)
            print(f"   [+] Procesado: {username} (ID: {ch.id})")
        except Exception as e:
            print(f"   [!] Error añadiendo {username}: {e}")
            
    print("\n✅ Carga de ECG finalizada.")

if __name__ == "__main__":
    seed_ecg()
