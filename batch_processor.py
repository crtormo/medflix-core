import asyncio
from pathlib import Path
from core.analysis import AnalysisCore
import os
from dotenv import load_dotenv

load_dotenv()

async def process_batch_directory(directory: str):
    core = AnalysisCore()
    path = Path(directory)
    
    if not path.exists():
        print(f"Directorio no encontrado: {directory}")
        return

    files = list(path.glob("*.pdf"))
    print(f"🚀 Iniciando procesamiento masivo de {len(files)} archivos en {directory}...")
    
    for file_path in files:
        print(f"Processing: {file_path.name}...")
        try:
            # Ejecutar de forma asíncrona (run_in_executor no es estrictamente necesario aquí si es un script batch simple, 
            # pero mantenemos consistencia)
            result = core.process_and_analyze(str(file_path))
            
            if result["status"] == "duplicate":
                print(f"  ⏭️ Duplicado ({result['reason']}). Skipping analysis.")
            else:
                print(f"  ✅ Procesado. ID: {result['doc_id']}")
                if result.get('snippets'):
                    print(f"     Resumen: {result['snippets'].get('summary_slide')}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    # Procesar lo que haya bajado el UserBot
    import sys
    # Permitir pasar directorio como argumento, defecto al de canales
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "data/uploads_channels"
    
    asyncio.run(process_batch_directory(target_dir))
