import streamlit as st
import requests
import time
import json
from pathlib import Path

# Configuración de página
st.set_page_config(
    page_title="MedFlix Core", 
    layout="wide", 
    page_icon="🧬",
    initial_sidebar_state="expanded"
)

API_URL = "http://localhost:8005"

# --- CUSTOM CSS: GLASSMORPHISM & MODERN UI ---
st.markdown("""
<style>
    /* Fuentes e Importaciones */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Fondo general */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(30, 30, 40) 0%, rgb(15, 15, 20) 90%);
        color: #e0e0e0;
    }

    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    }

    /* Títulos con gradiente */
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }

    /* Botones personalizados */
    .stButton > button {
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(58, 123, 213, 0.4);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(20, 20, 25, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Métricas */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        color: #00d2ff !important;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1 style='text-align: center; margin-bottom: 40px;'>🧬 MedFlix Core</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; margin-top: -30px;'>Sistema de Auditoría Epistemológica con IA</p>", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.history = []

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h3>📚 Biblioteca</h3>", unsafe_allow_html=True)
    st.info("Sube un paper para comenzar el análisis asíncrono.")
    
    st.markdown("---")
    st.markdown("#### 🔍 Buscador RAG")
    query = st.text_input("Buscar en papers:", placeholder="Ej: Ventilación prono...")
    if query:
        if st.button("Buscar", key="search_btn"):
            try:
                res = requests.get(f"{API_URL}/query", params={"q": query})
                if res.status_code == 200:
                    results = res.json()
                    st.success("Resultados encontrados:")
                    st.json(results) # Mejorar visualziación luego si hay tiempo
                else:
                    st.error("Error al buscar")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

    st.markdown("---")
    st.markdown("#### 🕒 Historial Reciente")
    for item in st.session_state.history[-5:]:
        st.caption(f"📄 {item}")

# --- MAIN CONTENT ---

# Contenedor de subida estilo 'Glass'
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.subheader("📤 Subir Paper (PDF)")
uploaded_file = st.file_uploader("", type="pdf", label_visibility="collapsed")

if uploaded_file:
    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_btn = st.button("Analizar con IA 🧠", type="primary")
    
    if analyze_btn:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 1. Subir archivo e iniciar Job
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            status_text.text("Subiendo archivo...")
            response = requests.post(f"{API_URL}/upload", files=files)
            
            if response.status_code == 200:
                upload_data = response.json()
                job_id = upload_data["job_id"]
                st.session_state.history.append(uploaded_file.name)
                
                # 2. Polling
                msg_placeholder = st.empty()
                
                while True:
                    status_res = requests.get(f"{API_URL}/jobs/{job_id}")
                    if status_res.status_code != 200:
                        st.error("Error consultando estado del trabajo.")
                        break
                        
                    job_data = status_res.json()
                    status = job_data["status"]
                    
                    if status == "pendiente":
                        status_text.text("⏳ En cola...")
                        progress_bar.progress(20)
                    elif status == "procesando":
                        status_text.text("🧠 Realizando Auditoría Epistemológica y analizando datos...")
                        progress_bar.progress(60)
                    elif status == "completado":
                        progress_bar.progress(100)
                        status_text.text("✅ ¡Completado!")
                        
                        # Mostrar Resultados
                        st.markdown('</div>', unsafe_allow_html=True) # Cerrar card de subida
                        
                        # Resultados
                        if job_data.get("message") and "duplicado" in job_data["message"].lower():
                             st.warning(f"⚠️ {job_data['message']}")
                        
                        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                        st.success("Análisis Finalizado Exitosamente")
                        
                        # Guardar doc_id para exportar
                        current_doc_id = job_data.get("doc_id", "")
                        
                        tab1, tab2, tab3, tab4 = st.tabs(["📝 Auditoría Crítica", "📊 Datos & Snippets", "📈 Gráficos", "🔍 Raw Data"])
                        
                        with tab1:
                            st.markdown("### Auditoría Epistemológica")
                            st.markdown(job_data.get("analysis", "No análisis disponible."))
                            
                        with tab2:
                            snippets = job_data.get("snippets", {})
                            c1, c2, c3 = st.columns(3)
                            c1.metric("N (Muestra)", snippets.get("n_study", "N/A"))
                            c2.metric("NNT", snippets.get("nnt", "N/A"))
                            c3.metric("Tipo Estudio", snippets.get("study_type", "N/A"))
                            
                            st.info(f"💡 **Slide Summary**: {snippets.get('summary_slide', 'N/A')}")
                            
                            # Botón Exportar para Presentación
                            st.markdown("---")
                            st.subheader("📤 Exportar para Presentación")
                            
                            col_cite1, col_cite2 = st.columns(2)
                            with col_cite1:
                                if st.button("📋 Generar Cita Vancouver", key="cite_vancouver"):
                                    try:
                                        cite_res = requests.get(f"{API_URL}/citar/{current_doc_id}?style=vancouver")
                                        if cite_res.status_code == 200:
                                            cita = cite_res.json().get("cita", "")
                                            st.code(cita, language=None)
                                        else:
                                            st.error("Error generando cita")
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                            
                            with col_cite2:
                                if st.button("📋 Generar Cita APA", key="cite_apa"):
                                    try:
                                        cite_res = requests.get(f"{API_URL}/citar/{current_doc_id}?style=apa")
                                        if cite_res.status_code == 200:
                                            cita = cite_res.json().get("cita", "")
                                            st.code(cita, language=None)
                                        else:
                                            st.error("Error generando cita")
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                        
                        with tab3:
                            st.markdown("### Gráficos Analizados")
                            graficos = job_data.get("graficos_analizados", [])
                            
                            if not graficos:
                                st.info("No se detectaron gráficos en este documento.")
                            else:
                                for i, grafico in enumerate(graficos):
                                    with st.expander(f"📊 Gráfico {i+1} - Página {grafico.get('pagina', '?')} ({grafico.get('dimensiones', 'N/A')})"):
                                        st.markdown(f"**Análisis Visual:**")
                                        st.markdown(grafico.get("analisis_visual", "Sin análisis"))
                                        
                                        # Mostrar imagen si existe
                                        ruta = grafico.get("ruta_local", "")
                                        if ruta:
                                            try:
                                                st.image(ruta, caption=f"Gráfico {i+1}")
                                            except:
                                                st.caption(f"Imagen guardada en: {ruta}")
                            
                        with tab4:
                            st.json(job_data)
                            
                        st.markdown('</div>', unsafe_allow_html=True)
                        break
                        
                    elif status == "fallido":
                        st.error(f"❌ Error en el análisis: {job_data.get('message')}")
                        break
                    
                    time.sleep(2) # Esperar 2 segundos antes de volver a consultar
                    
            else:
                st.error(f"Error iniciando subida: {response.text}")

        except Exception as e:
            st.error(f"Error de conexión: {e}")
else:
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; font-size: 0.8rem; opacity: 0.7;'>MedFlix Core v0.2 | Powered by Groq & Llama 3</p>", unsafe_allow_html=True)
