
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

# --- CSS PERSONALIZADO ---
def load_css():
    with open("ui/style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
load_css()

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

    if st.button("🥋 EKG Dojo", use_container_width=True):
        st.session_state.current_view = "ekg_dojo"
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

# --- COMPONENTE HERO ---
def render_hero(paper):
    """Renderiza el banner principal."""
    if not paper: return

    title = paper.get("titulo", "Sin Título")
    desc = paper.get("resumen_slide") or "Un paper importante..."
    score = paper.get("score_calidad") or 0
    img_path = paper.get("thumbnail_path")
    
    # Resolver imagen
    img_url = "https://via.placeholder.com/1200x600/1a1a1a/cccccc?text=MEDFLIX+HERO" # Fallback
    
    # Truco para usar imagen local como background en CSS: base64
    import base64
    
    bg_style = ""
    if img_path:
        p = Path(img_path)
        real_path = None
        if p.exists(): real_path = p
        elif (Path("data/thumbnails") / p.name).exists(): real_path = Path("data/thumbnails") / p.name
        
        if real_path:
            try:
                with open(real_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                    img_url_b64 = f"data:image/jpeg;base64,{encoded_string}"
                    bg_style = f"background-image: url('{img_url_b64}');"
            except: pass
    
    if not bg_style:
        bg_style = f"background-image: url('{img_url}');"

    html = f"""
    <div class="hero-container" style="{bg_style}">
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <div class="hero-title">{title}</div>
            <div class="hero-meta">⭐ {score}/10 Match | {paper.get('año', '')} | {paper.get('especialidad', 'General')}</div>
            <div class="hero-desc">{desc}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    
    # Botones fuera del HTML para usar funcionalidad nativa de Streamlit
    c1, c2, c3 = st.columns([1,1,4])
    if c1.button("▶ Ver Paper", key=f"hero_play_{paper['id']}", type="primary", use_container_width=True):
        st.session_state.selected_paper_id = paper['id']
        st.session_state.current_view = "detail"
        st.rerun()
    if c2.button("➕ Mi Lista", key=f"hero_list_{paper['id']}", use_container_width=True):
        st.toast("Añadido a mi lista (Simulación)")


# --- COMPONENTE TARJETA ---
def render_card(paper, key_prefix="card"):
    """Renderiza una tarjeta."""
    title = paper.get("titulo", "Sin título")
    score = paper.get("score_calidad") or 0
    year = paper.get("año", "")
    ptype = paper.get("tipo_estudio", "Paper")
    img_path = paper.get("thumbnail_path")
    
    with st.container(): # Container simple, el estilo viene de CSS global si se puede o se inyecta
        # Hack para aplicar estilo de tarjeta: no podemos envolver fácilmente en div con clase custom
        # y meter widgets dentro. Streamlit no permite widgets dentro de HTML blocks.
        # Usaremos el contenedor nativo y st.image. El CSS hover se aplica a todo .stVerticalBlock dentro de col? Dificil.
        # Alternativa: HTML puro para la tarjeta con un link (<a>) que ejecute JS? No.
        # Streamlit button es necesario para state.
        # Usaremos diseño standard pero limpio.
        
        # Imagen
        image_data = "https://via.placeholder.com/300x160/1a1a1a/cccccc?text=Paper"
        if img_path:
            p = Path(img_path)
            if p.exists(): image_data = str(p)
            elif (Path("data/thumbnails") / p.name).exists(): image_data = str(Path("data/thumbnails") / p.name)
        
        st.image(image_data, use_container_width=True)
            
        st.markdown(f"**{title[:50]}...**")
        st.caption(f"⭐ {int(score*10)}% | {year}")
        if st.button("Ver", key=f"{key_prefix}_{paper['id']}", use_container_width=True):
             st.session_state.selected_paper_id = paper['id']
             st.session_state.current_view = "detail"
             st.rerun()

# --- VISTAS ---

# 1. VIEW DETALLE (Igual que antes pero limpiaremos esto en otro paso si hace falta)
# ... CODIGO DETALLE MANTENIDO PORQUE NO ESTOY RE-ESCRIBIENDO EL HEADER, SOLO EL BLOQUE INFERIOR

# 2. VIEW HOME (Swimlanes)
if st.session_state.current_view == "home":
    # Cargar Stats
    try:
        stats = requests.get(f"{API_URL}/papers/stats").json()
        specs = stats.get("especialidades_breakdown", {})
    except:
        specs = {}

    # 1. Fetch TOP Paper for Hero
    # O random high score
    top_papers = fetch_papers(limit=1, sort="quality")
    if top_papers:
        hero_paper = top_papers[0]
        render_hero(hero_paper)

    # 2. Swimlanes
    st.markdown('<div class="swimlane-header">🔥 Nuevos Lanzamientos</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    recientes = fetch_papers(limit=5, sort="recent")
    for i, p in enumerate(recientes):
        with cols[i]:
            render_card(p, "recent")
            
    st.markdown('<div class="swimlane-header">⭐ Top Evidencia (RCTs & Reviews)</div>', unsafe_allow_html=True)
    cols2 = st.columns(5)
    top = fetch_papers(limit=5, sort="quality")
    for i, p in enumerate(top):
        with cols2[i]:
            render_card(p, "top")
            
    # Swimlane 3: Especialidades
    uci_count = specs.get('UCI', 0)
    if uci_count > 0:
        st.markdown(f'<div class="swimlane-header">🏥 Cuidados Críticos ({uci_count})</div>', unsafe_allow_html=True)
        cols3 = st.columns(5)
        uci = fetch_papers(limit=5, specialty="UCI")
        for i, p in enumerate(uci):
            with cols3[i]:
                render_card(p, "uci")

# 2.5 VIEW EKG DOJO (Nuevo Fase 10)
elif st.session_state.current_view == "ekg_dojo":
    st.markdown("## 🥋 EKG Dojo: Desafíos Diagnósticos")
    st.markdown("Pon a prueba tus habilidades interpretando trazados reales analizados por IA.")
    
    # Fetch quizzes
    try:
        res = requests.get(f"{API_URL}/papers", params={"is_quiz": True, "limit": 50})
        quizzes = res.json() if res.status_code == 200 else []
    except:
        quizzes = []

    if not quizzes:
        st.info("Aún no hay desafíos disponibles. Esperando nuevos casos de ECG...")
    else:
        c_list, c_play = st.columns([1, 3])
        
        with c_list:
            st.markdown("### Casos Disponibles")
            for q in quizzes:
                with st.container(border=True):
                    st.markdown(f"**Caso #{q['id'][:4]}**")
                    st.caption(f"{q.get('titulo')[:40]}...")
                    if st.button("Jugar", key=f"play_{q['id']}", use_container_width=True):
                         st.session_state.dojo_active_id = q['id']
                         st.session_state.dojo_revealed = False
                         st.rerun()

        with c_play:
            if 'dojo_active_id' in st.session_state:
                q_paper = next((x for x in quizzes if x['id'] == st.session_state.dojo_active_id), None)
                if q_paper:
                     full_q = get_paper_details(q_paper['id'])
                     
                     if full_q and full_q.get('quiz_data'):
                         q_data = full_q['quiz_data']
                         st.markdown(f"### 🏳️ Caso #{full_q['id'][:6]} - {full_q['titulo']}")
                         if full_q.get('thumbnail_path'):
                             t_path = Path(full_q['thumbnail_path'])
                             img_data = None
                             if t_path.exists():
                                 img_data = str(t_path)
                             elif (Path("data/thumbnails") / t_path.name).exists():
                                 img_data = str(Path("data/thumbnails") / t_path.name)
                             
                             if img_data:
                                 st.image(img_data, use_container_width=True)
                         
                         st.markdown("---")
                         st.subheader("❓ Pregunta")
                         st.markdown(f"#### {q_data.get('question', '¿Diagnóstico?')}")
                         
                         with st.form("quiz_form"):
                             selection = st.radio("Selecciona tu respuesta:", q_data.get('options', []))
                             submitted = st.form_submit_button("Responder")
                             if submitted:
                                 st.session_state.dojo_revealed = True
                         
                         if st.session_state.get('dojo_revealed'):
                             correct = q_data.get('correct_answer', '')
                             sel_letter = selection.split(":")[0].strip() if selection else ""
                             corr_letter = correct.split(":")[0].strip() if correct else correct
                             
                             if sel_letter == corr_letter:
                                 st.success("✅ ¡CORRECTO! Bien diagnosticado.")
                                 st.balloons()
                             else:
                                 st.error(f"❌ INCORRECTO. La respuesta era {correct}")
                             
                             with st.expander("📖 Ver Explicación", expanded=True):
                                 st.info(q_data.get('explanation', 'Sin explicación disponible.'))
                     else:
                         st.warning("Este paper no tiene datos de quiz válidos.")
            else:
                st.markdown("👈 Selecciona un caso para empezar el desafío.")

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

# 4. VIEW CHANNELS
elif st.session_state.current_view == "channels":
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
    if st.button("🔄 Escanear Todos Ahora", key="scan_btn"):
        try:
            requests.post(f"{API_URL}/scan-channels")
            st.toast("Escaneo iniciado...")
            
            # Polling de progreso
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.empty()
            
            active = True
            while active:
                time.sleep(1)
                try:
                    status = requests.get(f"{API_URL}/scan-status").json()
                    active = status["active"]
                    
                    # Calcular porcentaje
                    total = status["stats"]["total_canales"] or 1
                    current = status["stats"]["canal_actual"]
                    prog = min(current / total, 1.0)
                    progress_bar.progress(prog)
                    
                    status_text.info(f"{status['message']}")
                    
                    # Mostrar últimos logs
                    logs_md = "\n".join([f"- {l}" for l in status["last_log"][-5:]])
                    log_container.code(logs_md)
                    
                    if not active:
                         stats = status["stats"]
                         if stats["nuevos_descargados"] > 0:
                             st.success(f"✅ Finalizado! Nuevos papers: {stats['nuevos_descargados']}.")
                         else:
                             st.warning("🏁 Finalizado. No se encontraron nuevos papers en los canales monitoreados.")
                             
                except Exception as e:
                     st.error(f"Error obteniendo estado: {e}")
                     break
                     
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
