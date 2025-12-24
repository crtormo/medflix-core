
from services.database import get_db_service

def seed_specialties():
    db = get_db_service()
    
    # Canales específicos solicitados Fase 10
    specialties_channels = [
        # Cardiología & EKG
        ("@dailycardiology", "Daily Cardiology (Cases & Tips)"),
        ("@ecgcases", "ECG Cases (Challenges)"),
        ("@Cardiology_Books", "Cardiology Books Library"),
        
        # UCI / Crítico / Sepsis
        ("@CriticalCareMedicine", "Critical Care Medicine Updates"), # Asumido, validaremos en logs
        ("@icu_channel", "The ICU Channel"), # Generico, probaremos
        ("@esbicm", "ESBICM Critical Care"),
        
        # Neumología / Ventilación
        ("@Pneumology", "Pneumology & Respiratory"),
        ("@MechanicalVentilation", "Mechanical Ventilation Masters"),
        
        # Sepsis & Alergias
        ("@SepsisUpdates", "Sepsis & Infection Control"),
        ("@AllergyImmunology", "Allergy & Immunology"),
        
        # Cirugía Cardíaca
        ("@CardiacSurgery", "Cardiac Surgery International")
    ]
    
    print(f"🫀 Iniciando carga de {len(specialties_channels)} canales de especialidad...")
    
    added_count = 0
    
    for username, name in specialties_channels:
        try:
            # add_channel ya gestiona existencia/reactivación internamente
            ch = db.add_channel(username, name)
            print(f"   [+] Procesado: {username} (ID: {ch.id})")
            added_count += 1
                
        except Exception as e:
            print(f"   [!] Error añadiendo {username}: {e} (Posiblemente no existe o privado)")
            
    print("\n✅ Carga de especialidades finalizada.")

if __name__ == "__main__":
    seed_specialties()
