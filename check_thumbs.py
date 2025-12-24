
import sys
import os
from pathlib import Path
from services.database import get_db_service
from core.ingestion import IngestionService
import fitz

def check_thumbnails():
    db = get_db_service()
    papers = db.get_all_papers(limit=100)
    print(f"Total papers en DB: {len(papers)}")
    
    ingestion = IngestionService()
    
    processed_count = 0
    regenerated_count = 0
    
    for p in papers:
        if p.procesado:
            processed_count += 1
            
        print(f"ID: {p.id} | Titulo: {p.titulo[:30]}... | Procesado: {p.procesado}")
        
        should_regenerate = False
        if not p.thumbnail_path:
            print("  [NULL] Sin thumbnail. Intentando generar...")
            should_regenerate = True
        elif not Path(p.thumbnail_path).exists():
            print(f"  [MISSING] Archivo {p.thumbnail_path} no existe. Intentando generar...")
            should_regenerate = True
            
        if should_regenerate:
            # Intentar regenerar si existe el PDF original
            if p.archivo_path and Path(p.archivo_path).exists():
                try:
                    doc = fitz.open(p.archivo_path)
                    # Asegurar directorio de salida
                    output_dir = Path("data/thumbnails")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    new_thumb = ingestion.generate_thumbnail(doc, Path(p.archivo_path).name)
                    if new_thumb:
                         # Actualizar DB
                         db.update_paper(str(p.id), thumbnail_path=new_thumb)
                         print(f"  [OK] Regenerado y actualizado en DB: {new_thumb}")
                         regenerated_count += 1
                except Exception as e:
                    print(f"  [ERROR] Falló regeneración: {e}")
            else:
                print(f"  [FATAL] PDF original no encontrado en {p.archivo_path}")

    print(f"\nResumen:")
    print(f"Total Papers: {len(papers)}")
    print(f"Procesados (visibles en UI): {processed_count}")
    print(f"Thumbnails Regenerados: {regenerated_count}")

if __name__ == "__main__":
    check_thumbnails()
