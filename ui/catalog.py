
import streamlit as st
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional

# Configuración de página - Estilo "Wide" para efecto Netflix
st.set_page_config(
    page_title="MedFlix - Catálogo Médico", 
    layout="wide", 
    page_icon="🧬",
    initial_sidebar_state="collapsed"
)

# Constantes
API_URL = "http://api:8005"

# --- CSS PERSONALIZADO: ESTILO NETFLIX & SWIMLANES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #141414;
        color: #e5e5e5;
    }
    
    .stApp {
        background-color: #141414;
    }
    
    /* Swimlane Container */
    .swimlane-container {
        display: flex;
        overflow-x: auto;
        padding: 5px 0 20px 0;
        gap: 15px;
        scrollbar-width: thin;
        scrollbar-color: #46d369 #1f1f1f;
        scroll-behavior: smooth;
    }
    .swimlane-container::-webkit-scrollbar {
        height: 8px;
    }
    .swimlane-container::-webkit-scrollbar-track {
        background: #1f1f1f;
    }
    .swimlane-container::-webkit-scrollbar-thumb {
        background-color: #46d369;
        border-radius: 4px;
    }

    /* Tarjetas de Paper - Diseño Flex para Swimlane */
    .paper-card-wrapper {
        min-width: 250px;
        max-width: 250px;
        flex: 0 0 auto;
    }

    .paper-card {
        background-color: #1f1f1f;
        border-radius: 4px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        cursor: pointer;
        overflow: hidden;
        position: relative;
        height: 100%;
    }
    .paper-card:hover {
        transform: scale(1.03);
        z-index: 10;
        box-shadow: 0 8px 16px rgba(0,0,0,0.6);
    }
    
    .card-img {
        width: 100%;
        height: 140px;
        object-fit: cover;
    }
    
    .card-content {
        padding: 8px;
    }
    
    .card-title {
        font-size: 0.9rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 2px;
        color: white;
    }
    
    .score-badge {
        color: #46d369;
        font-weight: 700;
        font-size: 0.8rem;
    }
    
    .quality-hd {
        border: 1px solid #a3a3a3;
        border-radius: 2px;
        padding: 0 3px;
        font-size: 0.6rem;
        color: #a3a3a3;
        margin-left: 5px;
    }

    /* Botones Custom */
    .stButton > button {
        border-radius: 4px;
    }

    /* Modal Fake */
    
</style>
""", unsafe_allow_html=True)

# --- ESTADO DE SESIÓN ---
if 'selected_paper_id' not in st.session_state:
    st.session_state.selected_paper_id = None
if 'current_view' not in st.session_state:
    st.session_state.current_view = "home" # home, browse, channels, detail
if 'browse_filter' not in st.session_state:
    st.session_state.browse_filter = {} # {specialty, sort, query}
if 'active_jobs' not in st.session_state:
    st.session_state.active_jobs = [] 
if 'page' not in st.session_state:
    st.session_state.page = 1

# --- FUNCIONES API HELPER ---
def fetch_papers(limit=10, offset=0, specialty=None, sort="recent"):
    params = {"limit": limit, "offset": offset, "sort": sort}
    if specialty and specialty != "Todas":
        params["specialty"] = specialty
    try:
        res = requests.get(f"{API_URL}/papers", params=params)
        return res.json() if res.status_code == 200 else []
    except:
        return []

def get_paper_details(pid):
    try:
        res = requests.get(f"{API_URL}/papers/{pid}")
        return res.json() if res.status_code == 200 else None
    except:
        return None

def poll_jobs():
    if not st.session_state.active_jobs: return
    completed = []
    for job_id in st.session_state.active_jobs:
        try:
            res = requests.get(f"{API_URL}/jobs/{job_id}")
            if res.status_code == 200:
                data = res.json()
                if data["status"] == "completado":
                     st.toast(f"✅ Análisis listo: {data.get('doc_id')}")
                     completed.append(job_id)
                elif data["status"] == "fallido":
                     st.error(f"❌ Falló job {job_id[:6]}")
                     completed.append(job_id)
        except: pass
    for job in completed:
        st.session_state.active_jobs.remove(job)
        if completed:time.sleep(1);st.rerun()

poll_jobs()

# --- SIDEBAR DE NAVEGACIÓN Y FILTROS ---
with st.sidebar:
    st.title("🧬 MEDFLIX")
    
    if st.button("🏠 Inicio", use_container_width=True):
        st.session_state.current_view = "home"
        st.rerun()
        
    if st.button("🔍 Explorar Todo", use_container_width=True):
        st.session_state.current_view = "browse"
        st.session_state.browse_filter = {} # Reset
        st.rerun()

    if st.button("🤖 Canales Telegram", use_container_width=True):
        st.session_state.current_view = "channels"
        st.rerun()
        
    st.divider()
    
    # Filtros solo visibles en Browse o Home
    if st.session_state.current_view in ["browse", "home"]:
        st.markdown("### Filtros Rápidos")
        spec = st.selectbox("Especialidad", ["Todas", "Cardiología", "UCI", "Infectología", "Neurología", "Neumonía"])
        stype = st.selectbox("Tipo Estudio", ["Todos", "RCT", "Systematic Review", "Cohorte"])
        
        if st.button("Aplicar Filtros"):
             st.session_state.current_view = "browse"
             st.session_state.browse_filter = {"specialty": spec, "type": stype}
             st.session_state.page = 1
             st.rerun()

    st.divider()
    # Upload Rápido
    with st.expander("📤 Subir Paper"):
        uploaded_file = st.file_uploader("PDF", type="pdf")
        if uploaded_file and st.button("Subir y Analizar"):
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            try:
                res = requests.post(f"{API_URL}/upload", files=files)
                if res.status_code == 200:
                    jid = res.json()["job_id"]
                    st.session_state.active_jobs.append(jid)
                    st.success("Subido. Procesando...")
                    time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- COMPONENTE TARJETA ---
def render_card(paper, key_prefix="card"):
    """Renderiza una tarjeta que NO usa HTML raw para layout por limitaciones de Streamlit events inside HTML.
       Usaremos st.container y st.image nativos para interactivity.
    """
    title = paper.get("titulo", "Sin título")
    score = paper.get("score_calidad") or 0
    year = paper.get("año", "")
    ptype = paper.get("tipo_estudio", "Paper")
    img_path = paper.get("thumbnail_path")
    
    if img_path:
        filename = Path(img_path).name
        img_url = f"{API_URL}/static/thumbnails/{filename}"
    else:
        img_url = f"https://via.placeholder.com/300x160/1a1a1a/cccccc?text={ptype}"

    with st.container(border=True): # Streamlit 1.30+
        st.image(img_url, use_container_width=True)
        st.markdown(f"**{title}**")
        st.caption(f"⭐ {int(score*10)}% | {year} | {ptype}")
        if st.button("Ver", key=f"{key_prefix}_{paper['id']}", use_container_width=True):
             st.session_state.selected_paper_id = paper['id']
             st.session_state.current_view = "detail"
             st.rerun()

# --- VISTAS ---

# 1. VIEW DETALLE (Prioridad si hay ID seleccionado)
if st.session_state.current_view == "detail" and st.session_state.selected_paper_id:
    paper = get_paper_details(st.session_state.selected_paper_id)
    if paper:
        # Header
        c1, c2 = st.columns([1, 10])
        if c1.button("⬅ Atrás"):
             st.session_state.current_view = "home" # O la anterior history
             st.session_state.selected_paper_id = None
             st.rerun()
        c2.title(paper.get("titulo"))
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["📄 Análisis & PDF", "💬 Chat con Paper", "✏️ Metadatos"])
        
        with tab1:
            col_info, col_pdf = st.columns([1, 1])
            with col_info:
                st.markdown("### Review Epistemológico")
                st.write(paper.get("analisis_completo", "Pendiente..."))
                st.metric("Calidad", f"{paper.get('score_calidad')}/10")
            
            with col_pdf:
                # PDF Viewer
                fpath = paper.get("archivo_path")
                if fpath:
                    fname = Path(fpath).name
                    # Determinar si es upload normal o channel
                    if "uploads_channels" in fpath:
                        pdf_url = f"{API_URL}/static/uploads_channels/{fname}"
                    else:
                        pdf_url = f"{API_URL}/static/pdfs/{fname}"
                    
                    st.markdown(f"### 📑 Documento Original")
                    st.markdown(f'<iframe src="{pdf_url}" width="100%" height="600px"></iframe>', unsafe_allow_html=True)
                    st.download_button("Descargar PDF", data=requests.get(pdf_url).content, file_name=fname)
        
        with tab2:
            st.markdown("### 💬 Pregúntale a este Paper")
            # Chat history local state for this paper
            k_chat = f"chat_{paper['id']}"
            if k_chat not in st.session_state:
                st.session_state[k_chat] = []

            for msg in st.session_state[k_chat]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            prompt = st.chat_input("Escribe tu pregunta sobre el estudio...")
            if prompt:
                st.session_state[k_chat].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                
                with st.spinner("Analizando..."):
                    try:
                        res = requests.post(f"{API_URL}/chat/{paper['id']}", json={"question": prompt})
                        ans = res.json().get("answer", "Error")
                    except Exception as e:
                        ans = f"Error de conexión: {e}"
                
                st.session_state[k_chat].append({"role": "assistant", "content": ans})
                with st.chat_message("assistant"):
                    st.write(ans)

        with tab3:
            st.write("### Editar Metadatos")
            new_title = st.text_input("Título", value=paper.get("titulo"))
            if st.button("Guardar Cambios"):
                 requests.put(f"{API_URL}/papers/{paper['id']}", json={"titulo": new_title})
                 st.success("Guardado!")
                 time.sleep(0.5)
                 st.rerun()

    else:
        st.error("Paper no encontrado")

# 2. VIEW HOME (Swimlanes)
elif st.session_state.current_view == "home":
    # HERO
    st.markdown("## 🔥 Nuevos Lanzamientos")
    
    # Swimlane 1: Recientes
    cols = st.columns(5)
    recientes = fetch_papers(limit=5, sort="recent")
    for i, p in enumerate(recientes):
        with cols[i]:
            render_card(p, "recent")
            
    st.divider()
    
    # Swimlane 2: Top Quality
    col_head, col_more = st.columns([5,1])
    col_head.markdown("## ⭐ Top Calidad (Evidence based)")
    if col_more.button("Ver todos Top"):
        st.session_state.current_view = "browse"
        st.session_state.browse_filter = {"sort": "quality"}
        st.rerun()
        
    cols2 = st.columns(5)
    top = fetch_papers(limit=5, sort="quality")
    for i, p in enumerate(top):
        with cols2[i]:
            render_card(p, "top")
            
    st.divider()
    
    # Swimlane 3: Por Especialidad (Ej: UCI)
    st.markdown("## 🏥 Cuidados Críticos (UCI)")
    cols3 = st.columns(5)
    uci = fetch_papers(limit=5, specialty="UCI") # Backend debe soportar 'UCI' si es string parcial
    for i, p in enumerate(uci):
        with cols3[i]:
            render_card(p, "uci")

# 3. VIEW BROWSE (Grid + Paginación)
elif st.session_state.current_view == "browse":
    filt = st.session_state.browse_filter
    st.title(f"Explorando: {filt.get('specialty', 'Todos')} ({filt.get('sort', 'Reciente')})")
    
    limit = 12
    offset = (st.session_state.page - 1) * limit
    
    papers = fetch_papers(limit=limit, offset=offset, specialty=filt.get("specialty"), sort=filt.get("sort"))
    
    # Grid 4x3
    # Dividir lista en chunks de 4
    for i in range(0, len(papers), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(papers):
                with cols[j]:
                    render_card(papers[i+j], f"browse_{st.session_state.page}")
    
    # Paginación
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        col_prev, col_page, col_next = st.columns([1,2,1])
        if st.session_state.page > 1:
            if col_prev.button("◀ Prev"):
                st.session_state.page -= 1
                st.rerun()
        col_page.markdown(f"<p style='text-align:center'>Página <b>{st.session_state.page}</b></p>", unsafe_allow_html=True)
        if len(papers) == limit: # Asumimos que si trae limit, hay más
            if col_next.button("Next ▶"):
                st.session_state.page += 1
                st.rerun()

# 4. VIEW CHANNELS (Legacy)
elif st.session_state.current_view == "channels":
    st.markdown("## 🤖 Gestión de Canales")
    # ... (copiar código simple de channels anterior si es necesario, o resumido)
    channels = requests.get(f"{API_URL}/channels").json()
    for ch in channels:
        st.info(f"📢 {ch['nombre']} ({ch['username']}) - Último ID: {ch['last_scanned_id']}")
