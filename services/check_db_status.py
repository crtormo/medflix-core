
from services.database import get_db_service
from models.paper import Paper
from models.channel import Channel

def check_status():
    db = get_db_service()
    stats = db.get_stats()
    print("=== ESTADO DE BASE DE DATOS ===")
    print(f"Total Papers: {stats['total_papers']}")
    print(f"Procesados: {stats['procesados']}")
    print(f"Pendientes: {stats['pendientes']}")
    print(f"Con Gráficos: {stats['con_graficos']}")
    
    with db.get_session() as session:
        channels = session.query(Channel).all()
        print(f"\n=== CANALES ({len(channels)}) ===")
        for ch in channels:
            print(f"- {ch.username} (Activo: {ch.active}, Last Scan ID: {ch.last_scanned_id})")

        recientes = session.query(Paper).order_by(Paper.fecha_subida.desc()).limit(5).all()
        print("\n=== ÚLTIMOS 5 PAPERS ===")
        for p in recientes:
            print(f"- [{p.id}] {p.titulo[:50]}... (Procesado: {p.procesado})")

if __name__ == "__main__":
    check_status()
