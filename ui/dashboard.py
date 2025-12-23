import streamlit as st
import requests
import json
from pathlib import Path

# Configuración
st.set_page_config(page_title="MedFlix Core", layout="wide", page_icon="🧬")

API_URL = "http://localhost:8001"

st.title("🧬 MedFlix Core: Auditoría Epistemológica")

# Sidebar
with st.sidebar:
    st.header("Biblioteca")
    st.info("Sube un paper para comenzar el análisis.")
    
    # Buscador RAG (Placeholder funcional)
    query = st.text_input("Buscar en mi biblioteca:", placeholder="Ej: Ventilación prono...")
    if query:
        if st.button("Buscar"):
            try:
                res = requests.get(f"{API_URL}/query", params={"q": query})
                if res.status_code == 200:
                    results = res.json()
                    st.write(results)
                else:
                    st.error("Error al buscar")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

# Área de Upload
uploaded_file = st.file_uploader("Arrastra tu PDF aquí", type="pdf")

if uploaded_file:
    if st.button("Analizar con IA 🧠"):
        with st.spinner("Leyendo PDF, extrayendo texto y realizando Auditoría Epistemológica..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                response = requests.post(f"{API_URL}/upload", files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "duplicate":
                        st.warning(f"⚠️ {data['message']}")
                        st.info("Este paper ya existe en tu base de datos.")
                        # Si quisiéramos mostrar el análisis existente, necesitaríamos endpoint GET /analysis/{id}
                    else:
                        st.success("✅ Análisis Completado")
                        
                        # Tabs para organizar la info
                        tab1, tab2, tab3 = st.tabs(["Auditoría Crítica", "Snippets & Datos", "Raw JSON"])
                        
                        with tab1:
                            st.markdown("## Auditoría Epistemológica (The Lancet Persona)")
                            st.markdown(data.get("analysis", "No analysis available."))
                            
                        with tab2:
                            snippets = data.get("snippets", {})
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("N (Muestra)", snippets.get("n_study", "N/A"))
                                st.metric("Tipo Estudio", snippets.get("study_type", "N/A"))
                            with col2:
                                st.metric("NNT", snippets.get("nnt", "N/A"))
                            
                            st.subheader("Slide Summary")
                            st.info(snippets.get("summary_slide", "N/A"))
                            
                        with tab3:
                            st.json(data)
                            
                else:
                    st.error(f"Error del servidor: {response.text}")
                    
            except Exception as e:
                st.error(f"Error conectando con el backend: {e}")
                st.warning("¿Está corriendo el servidor FastAPI? (uvicorn app.main:app)")

st.divider()
st.caption("MedFlix Core v0.1 | Powered by Groq & Llama 3")
