
import requests

try:
    print("🚀 Triggering Manual Scan...")
    res = requests.post("http://localhost:8005/scan-channels")
    if res.status_code == 200:
        print(f"✅ Éxito: {res.json()}")
    else:
        print(f"❌ Error {res.status_code}: {res.text}")
except Exception as e:
    print(f"❌ Error conexión: {e}")
