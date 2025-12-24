
import streamlit as st
import requests
import time
from pathlib import Path

# Configuración de página - Estilo "Wide" para efecto Netflix
st.set_page_config(
    page_title="MedFlix - Catálogo Médico", 
    layout="wide", 
    page_icon="🧬",
    initial_sidebar_state="collapsed"
)

# Constantes
API_URL = "http://api:8005"


# --- CSS PERSONALIZADO: ESTILO NETFLIX ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #141414; /* Fondo Netflix Dark */
        color: #e5e5e5;
    }
    
    .stApp {
        background-color: #141414;
    }
    
    /* Header Transparente */
    header {visibility: hidden;}
    
    /* Títulos de Carrusel */
    h3 {
        color: #e5e5e5;
        font-weight: 600;
        font-size: 1.4rem;
        margin-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
    
    /* Tarjetas de Paper */
    .paper-card {
        background-color: #1f1f1f;
        border-radius: 4px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        cursor: pointer;
        overflow: hidden;
        margin-bottom: 10px;
        position: relative;
    }
    .paper-card:hover {
        transform: scale(1.05); /* Efecto pop */
        z-index: 10;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    
    .card-img {
        width: 100%;
        height: 160px;
        object-fit: cover;
    }
    
    .card-content {
        padding: 10px;
    }
    
    .card-title {
        font-size: 0.95rem;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 4px;
    }
    
    .card-meta {
        font-size: 0.75rem;
        color: #a3a3a3;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .score-badge {
        color: #46d369; /* Verde Netflix */
        font-weight: 700;
        font-size: 0.8rem;
    }
    
    .quality-hd {
        border: 1px solid #a3a3a3;
        border-radius: 2px;
        padding: 0 4px;
        font-size: 0.6rem;
    }

    /* Botón Hero */
    .hero-btn {
        background-color: white;
        color: black;
        border: none;
        padding: 10px 24px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 1.1rem;
        cursor: pointer;
    }
    .hero-btn:hover {
        background-color: rgba(255,255,255,0.75);
    }
    
    /* Modal Personalizado (simulado con expander forzado o sidebar) */
    
</style>
""", unsafe_allow_html=True)

# --- ESTADO DE SESIÓN ---
if 'selected_paper_id' not in st.session_state:
    st.session_state.selected_paper_id = None
if 'current_view' not in st.session_state:
    st.session_state.current_view = "catalog"
if 'active_jobs' not in st.session_state:
    st.session_state.active_jobs = [] # List of job_ids

# --- JOB POLLING ---
def poll_jobs():
    """Consulta estado de jobs activos y notifica."""
    if not st.session_state.active_jobs:
        return

    completed_jobs = []
    for job_id in st.session_state.active_jobs:
        try:
            res = requests.get(f"{API_URL}/jobs/{job_id}")
            if res.status_code == 200:
                data = res.json()
                status = data.get("status")
                if status == "completado":
                     st.toast(f"✅ Análisis completado para Paper ID: {data.get('doc_id')}")
                     completed_jobs.append(job_id)
                elif status == "fallido":
                     st.error(f"❌ Falló análisis: {data.get('message')}")
                     completed_jobs.append(job_id)
        except:
            pass
    
    # Limpiar jobs terminados
    for job in completed_jobs:
        st.session_state.active_jobs.remove(job)
        if completed_jobs:
            time.sleep(1)
            st.rerun()

# Llamar polling al inicio de cada render
poll_jobs()

# --- FUNCIONES API ---
def get_recent_papers():
    try:
        response = requests.get(f"{API_URL}/papers", params={"limit": 8})
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error conectando con API: {e}")
    return []

# --- NAVEGACIÓN PRINCIPAL ---
nav_col1, nav_col2, nav_col3 = st.columns([1,1,6])
with nav_col1:
    if st.button("🎬 Catálogo", use_container_width=True):
        st.session_state.current_view = "catalog"
        st.session_state.selected_paper_id = None
        st.rerun()
with nav_col2:
    if st.button("🤖 Canales", use_container_width=True):
        st.session_state.current_view = "channels"
        st.session_state.selected_paper_id = None
        st.rerun()

# --- VISTA: CANALES TELEGRAM ---
if st.session_state.current_view == "channels":
    st.markdown("## 🤖 Gestión de Canales de Telegram")
    st.markdown("Configura los canales que MedFlix debe monitorear automáticamente.")
    
    # 1. Añadir Canal
    with st.expander("➕ Añadir Nuevo Canal", expanded=False):
        c1, c2, c3 = st.columns([3, 2, 1])
        new_channel = c1.text_input("Username del Canal (ej: @librosmedicina)")
        new_name = c2.text_input("Nombre Descriptivo (Opcional)")
        if c3.button("Añadir", type="primary", use_container_width=True):
            if new_channel:
                try:
                    res = requests.post(f"{API_URL}/channels", params={"username": new_channel, "nombre": new_name})
                    if res.status_code == 200:
                        st.success(f"Canal {new_channel} añadido correctamente")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
    
    # 2. Lista de Canales
    st.markdown("### Canales Monitoreados")
    
    # Trigger Escaneo Manual
    if st.button("🔄 Escanear Todos Ahora"):
        try:
            requests.post(f"{API_URL}/scan-channels")
            st.toast("Escaneo iniciado en segundo plano...")
        except:
            st.error("No se pudo iniciar el escaneo")

    try:
        channels = requests.get(f"{API_URL}/channels").json()
        if not channels:
            st.info("No hay canales configurados.")
        else:
            for ch in channels:
                with st.container():
                    st.markdown(f"""
                    <div style="background-color: #1f1f1f; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin:0; color:white;">{ch['nombre']}</h4>
                            <code style="color:#a3a3a3;">{ch['username']}</code>
                        </div>
                        <div style="text-align: right;">
                             <p style="margin:0; font-size: 0.8rem; color:#a3a3a3;">Último escaneo: {ch['last_scan_date'] or 'Nunca'}</p>
                             <p style="margin:0; font-size: 0.8rem; color:#46d369;">ID: {ch['last_scanned_id']}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("🗑️ Eliminar", key=f"del_{ch['username']}"):
                        requests.delete(f"{API_URL}/channels/{ch['username']}")
                        st.rerun()
                        
    except Exception as e:
        st.error(f"Error al cargar canales: {e}")

# --- VISTA: CATÁLOGO ---
elif st.session_state.current_view == "catalog":
    
    # --- DETALLE DEL PAPER (Modal-like) ---
    if st.session_state.selected_paper_id:
        # Mostrar detalle
        try:
            res = requests.get(f"{API_URL}/papers/{st.session_state.selected_paper_id}")
            if res.status_code == 200:
                paper = res.json()
                
                # Header con Botón Atrás
                c1, c2 = st.columns([1, 10])
                with c1:
                    if st.button("⬅ Volver"):
                        st.session_state.selected_paper_id = None
                        st.rerun()
                with c2:
                    st.title(paper.get("titulo", "Sin Título"))
                
                # Metadatos Principales
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Score Calidad", f"{paper.get('score_calidad', 0)}/10")
                m2.metric("N (Muestra)", paper.get("n_muestra", "N/A"))
                m3.metric("NNT", paper.get("nnt", "N/A"))
                m4.caption(f"Especialidad: {paper.get('especialidad')}\nTipo: {paper.get('tipo_estudio')}")
                
                st.divider()
                
                # Contenido del Análisis
                col_text, col_vis = st.columns([2, 1])
                
                with col_text:
                    st.markdown("### 🧐 Auditoría Epistemológica")
                    analysis_text = paper.get("analisis_completo", "")
                    if analysis_text:
                        st.markdown(analysis_text)
                    else:
                        st.info("El análisis está vacío o pendiente.")
                
                with col_vis:
                    st.markdown("### 📊 Análisis Visual")
                    # Placeholder para imágenes (cuando funcionen)
                    imgs = paper.get("imagenes", [])
                    if imgs:
                        for img in imgs:
                            # TODO: Servir imagenes estáticas
                             st.warning("Imagen detectada (rendering pendiente)")
                    else:
                        st.info("No se detectaron gráficos analizables.")

            else:
                 st.error("No se pudo cargar el paper.")
                 if st.button("Cerrar"):
                    st.session_state.selected_paper_id = None
                    st.rerun()
        except Exception as e:
            st.error(f"Error cargando detalle: {e}") 
    else:
        # Si no hay detalle seleccionado, mostramos la home del catálogo
        
        # --- HERO SECTION ---
        st.markdown("""
        <div style="background: linear-gradient(rgba(0,0,0,0.5), #141414), url('https://source.unsplash.com/1600x900/?hospital,technology'); background-size: cover; height: 60vh; padding: 50px; display: flex; flex-direction: column; justify-content: center;">
            <h1 style="font-size: 4rem; margin-bottom: 10px;">MEDFLIX</h1>
            <h2 style="font-size: 2rem; margin-bottom: 20px;">Auditoría Epistemológica de Vanguardia</h2>
            <p style="font-size: 1.2rem; max-width: 600px; margin-bottom: 30px;">
                Descubre la verdad detrás de los papers médicos. Análisis crítico impulsado por IA, detección de sesgos y extracción visual instantánea.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # --- BARRA DE NAVEGACIÓN / FILTROS ---
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            search = st.text_input("🔍 Buscar títulos, autores, tags...", label_visibility="collapsed")
        with c2:
            especialidad = st.selectbox("Especialidad", ["Todas", "Cardiología", "UCI", "Infectología", "Neurología"])
        with c3:
            tipo = st.selectbox("Tipo Estudio", ["Todos", "RCT", "Meta-análisis", "Cohorte"])
        with c4:
            # Botón de upload abre el modal
            if st.button("📤 Subir Paper", type="primary"):
                st.session_state.show_upload = True
        
        if getattr(st.session_state, 'show_upload', False):
            with st.expander("📤 Cargar Nuevo Paper", expanded=True):
                uploaded_file = st.file_uploader("Arrastra tu PDF aquí", type="pdf")
                if uploaded_file:
                    if st.button("Analizar ahora"):
                        try:
                            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                            with st.spinner("Subiendo y analizando..."):
                                res = requests.post(f"{API_URL}/upload", files=files)
                            
                            if res.status_code == 200:
                                data = res.json()
                                job_id = data.get("job_id")
                                st.session_state.active_jobs.append(job_id)
                                st.success(f"✅ Archivo subido. Analizando en segundo plano (Job: {job_id[:8]})...")
                                st.session_state.show_upload = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Error al subir: {res.text}")
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")
        
        # --- CARRUSELES ---
        def render_card(paper):
            # Renderiza una tarjeta HTML clickable
            title = paper.get("titulo", "Sin título")
            score = paper.get("score_calidad") or 0
            year = paper.get("año", "")
            ptype = paper.get("tipo_estudio", "Paper")
            img_path = paper.get("thumbnail_path") 
            
            # Resolver ruta de imagen 
            # Si es local path, la convertimos a URL del endpoint estático de FastAPI
            if img_path:
                filename = Path(img_path).name
                img_url = f"{API_URL}/static/thumbnails/{filename}"
            else:
                 # Placeholder si no hay imagen
                img_url = f"https://via.placeholder.com/300x160/1a1a1a/cccccc?text={ptype}"

            with st.container():
                st.image(img_url, use_container_width=True)
                st.markdown(f"**{title}**")
                st.markdown(f"<span class='score-badge'>{int(score*10)}% Match</span> <span class='quality-hd'>{ptype}</span> {year}", unsafe_allow_html=True)
                if st.button("Ver Análisis", key=f"btn_{paper['id']}", use_container_width=True):
                    st.session_state.selected_paper_id = paper['id']
                    st.rerun()

        # 1. Agregados Recientemente
        st.markdown("<h3>Nuevos Lanzamientos</h3>", unsafe_allow_html=True)
        cols = st.columns(4)
        papers = get_recent_papers()
        if not papers:
            st.info("No hay papers procesados aún. ¡Sube uno o añade canales!")
        
        for i, col in enumerate(cols):
            with col:
                if i < len(papers):
                    render_card(papers[i])
