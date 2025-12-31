
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
    
    st.divider()
    st.markdown("### 📂 Biblioteca")
    
    # Papers (solo con DOI)
    if st.button("📄 Papers", use_container_width=True):
        st.session_state.current_view = "categoria_papers"
        st.rerun()
    
    # Libros de Medicina (por especialidad)
    if st.button("📚 Libros de Medicina", use_container_width=True):
        st.session_state.current_view = "categoria_libros"
        st.rerun()
    
    # EKG Dojo (quizzes ECG)
    if st.button("🥋 EKG Dojo", use_container_width=True):
        st.session_state.current_view = "ekg_dojo"
        st.rerun()

    # Guías de Práctica Clínica (Nuevo Fase 2)
    if st.button("📜 Guías (GPC)", use_container_width=True):
        st.session_state.current_view = "categoria_guias"
        st.rerun()
    
    # Calculadoras (Nuevo Fase 2)
    if st.button("🧮 Calculadoras", use_container_width=True):
        st.session_state.current_view = "calculadoras"
        st.rerun()
    
    st.divider()
    st.markdown("### ⚙️ Gestión")
    
    # Sin Categorizar (incluye eliminados como sub-sección)
    if st.button("❓ Sin Categorizar", use_container_width=True):
        st.session_state.current_view = "sin_categorizar"
        st.rerun()
    
    # Canales Telegram
    if st.button("🤖 Canales Telegram", use_container_width=True):
        st.session_state.current_view = "channels"
        st.rerun()
        
    st.divider()
    
    # 🔍 BUSCADOR GLOBAL
    st.markdown("### 🔍 Buscar")
    search_query = st.text_input("Título, autor o tema...", key="global_search_input")
    if search_query:
        if st.button("Buscar en Biblioteca", type="primary", use_container_width=True):
            st.session_state.current_view = "search_results"
            st.session_state.search_q = search_query
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
        
        # Imagen (Prioridad: Libro -> IA Thumbnail -> Placeholder)
        image_data = "https://via.placeholder.com/300x160/1a1a1a/cccccc?text=Paper"
        
        # 1. Intentar portada de libro descargada
        if paper.get("cover_path"):
            p = Path(paper["cover_path"])
            if p.exists(): image_data = str(p)
            elif (Path("data/covers") / p.name).exists(): image_data = str(Path("data/covers") / p.name)
            elif p.name.startswith("covers/"): # Si ya viene con el prefijo
                image_data = f"data/{paper['cover_path']}" if not paper['cover_path'].startswith("/") else paper['cover_path'][1:]
        
        # 2. Intentar thumbnail de IA
        if image_data.startswith("http") and img_path:
            p = Path(img_path)
            if p.exists(): image_data = str(p)
            elif (Path("data/thumbnails") / p.name).exists(): image_data = str(Path("data/thumbnails") / p.name)
        
        st.image(image_data, use_container_width=True)
            
        st.markdown(f"**{title[:50]}...**")
        q_val = int(score*10) if score <= 10 else int(score) # Manejar 0.8 vs 8.5
        st.caption(f"⭐ {q_val}% Match | {year}")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            if st.button("Ver", key=f"{key_prefix}_{paper['id']}", use_container_width=True):
                st.session_state.selected_paper_id = paper['id']
                st.session_state.current_view = "detail"
                st.rerun()
        with c2:
            # Popover para Modo Guardia (⚡ Vista Rápida)
            with st.popover("⚡", use_container_width=True):
                st.markdown(f"**{title}**")
                
                # Intentar obtener clinical_insights si están disponibles
                # En list_papers, to_card_dict NO incluye clinical_insights por performance
                # Pero to_dict sí. Si no está, avisamos.
                insights = paper.get("clinical_insights")
                if insights and insights.get("bottom_line"):
                    st.success(f"**Bottom Line:** {insights['bottom_line']}")
                    if insights.get("key_dosages"):
                        st.info(f"💊 **Dosis:** {', '.join(insights['key_dosages'])}")
                    if insights.get("safety_warnings"):
                        st.warning(f"⚠️ **Seguridad:** {', '.join(insights['safety_warnings'])}")
                    
                    if insights.get("suggested_calculators"):
                        st.info(f"🧮 **Calculadoras:** {', '.join(insights['suggested_calculators'][:3])}")
                        
                    st.caption(f"🛡️ {insights.get('safety_disclaimer', '')}")
                else:
                    st.info("Insights no disponibles en vista previa. Abre el paper para generarlos.")

# --- VISTAS ---

# 1. VIEW DETALLE (Prioridad si hay ID seleccionado)
if st.session_state.current_view == "detail" and st.session_state.selected_paper_id:
    paper = get_paper_details(st.session_state.selected_paper_id)
    if paper:
        # Header
        c1, c2 = st.columns([1, 10])
        if c1.button("⬅ Atrás"):
             st.session_state.current_view = "home"
             st.session_state.selected_paper_id = None
             st.rerun()
        c2.title(paper.get("titulo"))
        
        # Technical Info Block
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("⭐ Calidad", f"{paper.get('score_calidad', 0)}/10")
        
        is_libro = paper.get("categoria") == "libros"
        
        if is_libro:
            # Info para LIBROS
            isbn = paper.get("isbn") or "N/A"
            m2.markdown(f"**ISBN**\n\n{isbn}")
            
            pags = paper.get("num_paginas") or "N/A"
            idioma = paper.get("idioma") or "Sin definir"
            m3.markdown(f"**Páginas:** {pags}\n\n**Idioma:** {idioma}")
            
            editorial = paper.get("editorial") or "N/A"
            edicion = paper.get("edicion") or "N/A"
            m4.markdown(f"**Editorial:** {editorial}\n\n**Edición:** {edicion}")
        else:
            # Info para PAPERS
            doi = paper.get("doi")
            if doi:
                m2.markdown(f"**DOI**\n\n[{doi}](https://doi.org/{doi})")
            else:
                m2.metric("DOI", "N/A")
                
            m3.markdown(f"**Muestra:** {paper.get('n_muestra', 'N/A')}\n\n**NNT:** {paper.get('nnt', 'N/A')}")
            
            revista = paper.get('revista') or "N/A"
            fecha = paper.get('fecha_publicacion_exacta') or paper.get('año')
            m4.markdown(f"**Revista:** {revista}\n\n**Fecha:** {fecha}\n\n**Tipo:** {paper.get('tipo_estudio')}")
        
        # Botones de Acción Rápidos
        cols_act = st.columns([1,1,1,3])
        with cols_act[0]:
            if st.button("📑 Citar", use_container_width=True):
                st.session_state.show_citation = True
        
        if st.session_state.get("show_citation"):
            with st.expander("📝 Generar Cita", expanded=True):
                c_style = st.selectbox("Estilo", ["vancouver", "apa", "harvard"])
                try:
                    res_cite = requests.get(f"{API_URL}/papers/citar/{paper['id']}", params={"style": c_style})
                    if res_cite.status_code == 200:
                        st.code(res_cite.json()["cita"])
                    else:
                        st.error("No se pudo generar la cita")
                except:
                    st.error("Error conectando con el servicio de citas")
                if st.button("Cerrar"):
                    st.session_state.show_citation = False
                    st.rerun()

        # ⚡ SECCIÓN MODO GUARDIA (UCI/ER)
        insights = paper.get("clinical_insights")
        if insights and insights.get("bottom_line"):
            with st.container(border=True):
                st.markdown("### ⚡ Modo Guardia: Quick Insights")
                c_i1, c_i2, c_i3 = st.columns([3, 2, 1])
                with c_i1:
                    st.success(f"**Conclusión Directa:**\n\n{insights['bottom_line']}")
                with c_i2:
                    if insights.get("key_dosages"):
                        st.info(f"💊 **Dosis Sugeridas:**\n\n- " + "\n- ".join(insights['key_dosages']))
                    if insights.get("safety_warnings"):
                        st.warning(f"⚠️ **Advertencias:**\n\n- " + "\n- ".join(insights['safety_warnings']))
                with c_i3:
                    st.metric("🎓 Evidencia", insights.get('grade', 'N/A'))
                    st.caption(f"*{insights.get('safety_disclaimer', '')}*")
                    if st.button("🔄 Regenerar", key=f"re_ins_{paper['id']}"):
                        with st.spinner("Analizando dosis..."):
                            requests.post(f"{API_URL}/papers/{paper['id']}/clinical-insights")
                            st.rerun()
            
            # --- RECOMENDACIONES GPC (Fase 2) ---
            gpc_rec = insights.get("gpc_recommendations")
            if gpc_rec:
                with st.expander("📜 Guía de Práctica Clínica - Recomendaciones", expanded=True):
                    c_g1, c_g2 = st.columns(2)
                    with c_g1:
                        if gpc_rec.get("clase_i"):
                            st.success("**Clase I (Fuerte)**\n\n- " + "\n- ".join(gpc_rec["clase_i"]))
                        if gpc_rec.get("clase_iia"):
                            st.info("**Clase IIa (Sugerida)**\n\n- " + "\n- ".join(gpc_rec["clase_iia"]))
                    with c_g2:
                        if gpc_rec.get("contraindicaciones_iii"):
                            st.error("**Clase III (No realizar)**\n\n- " + "\n- ".join(gpc_rec["contraindicaciones_iii"]))
                        if gpc_rec.get("puntos_clave"):
                            st.warning("**Puntos Clave**\n\n- " + "\n- ".join(gpc_rec["puntos_clave"]))

            # --- CALCULADORAS SUGERIDAS (Fase 2) ---
            calc_sug = insights.get("suggested_calculators")
            if calc_sug:
                st.markdown("🔍 **Calculadoras Sugeridas:** " + ", ".join([f"`{c}`" for c in calc_sug]))
                if st.button("🧮 Abrir Panel de Calculadoras", key=f"open_calc_{paper['id']}"):
                    st.session_state.current_view = "calculadoras"
                    st.rerun()
        else:
            if not is_libro: # Solo para papers por ahora
                with st.container(border=True):
                    st.info("⚡ El **Modo Guardia** no está activo para este documento.")
                    if st.button("🚀 Generar Insights (Dosis y Seguridad)", key=f"gen_ins_{paper['id']}", type="primary"):
                        with st.spinner("IA analizando soporte vital..."):
                            requests.post(f"{API_URL}/papers/{paper['id']}/clinical-insights")
                            st.rerun()

        st.markdown("---")

        # Tabs
        title_tab1 = "📄 Descripción & PDF" if is_libro else "📄 Análisis & PDF"
        tab1, tab2, tab3 = st.tabs([title_tab1, "💬 Chat con IA", "✏️ Metadatos"])
        
        with tab1:
            col_info, col_pdf = st.columns([1, 1])
            with col_info:
                header_analisis = "### 📚 Descripción y Análisis" if is_libro else "### Review Epistemológico"
                st.markdown(header_analisis)
                st.write(paper.get("analisis_completo", "Pendiente..."))
            
            with col_pdf:
                fpath = paper.get("archivo_path")
                if fpath:
                    p_path = Path(fpath)
                    fname = p_path.name
                    
                    real_file_path = None
                    if p_path.exists():
                        real_file_path = p_path
                    elif (Path("data/uploads") / fname).exists():
                         real_file_path = Path("data/uploads") / fname
                    elif (Path("data/uploads_channels") / fname).exists():
                         real_file_path = Path("data/uploads_channels") / fname

                    if "uploads_channels" in str(fpath):
                        pdf_url = f"{API_URL}/static/uploads_channels/{fname}"
                    else:
                        pdf_url = f"{API_URL}/static/pdfs/{fname}"
                    
                    st.markdown(f"### 📑 Documento Original")
                    
                    if real_file_path:
                        try:
                            with open(real_file_path, "rb") as f:
                                pdf_bytes = f.read()
                                st.download_button(
                                    label="📥 Descargar PDF",
                                    data=pdf_bytes,
                                    file_name=fname,
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Error leyendo archivo: {e}")
                    else:
                        st.warning("⚠️ El archivo PDF no se encuentra.")
                        
                    st.markdown(f'<iframe src="{pdf_url}" width="100%" height="600px"></iframe>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown(f"### 💬 Pregúntale a este {'Libro' if is_libro else 'Paper'}")
            k_chat = f"chat_{paper['id']}"
            if k_chat not in st.session_state:
                st.session_state[k_chat] = []

            for msg in st.session_state[k_chat]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            prompt = st.chat_input(f"Escribe tu pregunta sobre este {'libro' if is_libro else 'estudio'}...")
            if prompt:
                st.session_state[k_chat].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                
                with st.spinner("Analizando..."):
                    try:
                        res = requests.post(f"{API_URL}/papers/chat/{paper['id']}", json={"question": prompt})
                        ans = res.json().get("answer", "Error")
                    except Exception as e:
                        ans = f"Error de conexión: {e}"
                
                st.session_state[k_chat].append({"role": "assistant", "content": ans})
                with st.chat_message("assistant"):
                    st.write(ans)

        with tab3:
            st.write("### ✏️ Editar Metadatos")
            
            col_form, col_doi = st.columns([1, 1])
            
            with col_form:
                st.markdown("#### Información Básica")
                new_title = st.text_input("Título", value=paper.get("titulo"))
                new_autores = st.text_area("Autores (uno por línea)", 
                    value="\n".join(paper.get("autores", [])) if paper.get("autores") else "")
                new_year = st.number_input("Año", value=paper.get("año") or 2024, min_value=1900, max_value=2030)
                # Obtener especialidades dinámicas
                try:
                    especialidades_db = requests.get(f"{API_URL}/papers/especialidades").json()
                except:
                    especialidades_db = ["Cardiología", "UCI", "Infectología", "Neurología", "Neumonía", "ECG"]
                
                if "Otra" not in especialidades_db: especialidades_db.append("Otra")
                
                current_spec = paper.get("especialidad") or "Otra"
                if current_spec not in especialidades_db:
                    especialidades_db.insert(0, current_spec)
                
                new_specialty = st.selectbox("Especialidad", 
                    especialidades_db,
                    index=especialidades_db.index(current_spec)
                )
                new_tipo = st.selectbox("Tipo de Estudio",
                    ["RCT", "Systematic Review", "Meta-análisis", "Cohorte", "Caso-Control", "Observacional", "Otro"],
                    index=0 if not paper.get("tipo_estudio") else
                        (["RCT", "Systematic Review", "Meta-análisis", "Cohorte", "Caso-Control", "Observacional", "Otro"].index(paper.get("tipo_estudio"))
                         if paper.get("tipo_estudio") in ["RCT", "Systematic Review", "Meta-análisis", "Cohorte", "Caso-Control", "Observacional", "Otro"] else 6)
                )
                
                if st.button("💾 Guardar Cambios", use_container_width=True, type="primary"):
                    updates = {
                        "titulo": new_title,
                        "autores": [a.strip() for a in new_autores.split("\n") if a.strip()],
                        "año": int(new_year),
                        "especialidad": new_specialty,
                        "tipo_estudio": new_tipo
                    }
                    try:
                        requests.put(f"{API_URL}/papers/{paper['id']}", json=updates)
                        st.success("✅ Metadatos guardados correctamente!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            with col_doi:
                st.markdown("#### 🔗 Actualizar DOI y Metadatos")
                
                current_doi = paper.get("doi", "")
                doi_status = "✅ Validado" if paper.get("doi_validado") else "⚠️ No validado"
                metadata_source = paper.get("metadata_source", "Sin enriquecer")
                
                st.info(f"""
                **DOI actual:** {current_doi or 'No disponible'}  
                **Estado:** {doi_status}  
                **Fuente metadatos:** {metadata_source}
                """)
                
                new_doi = st.text_input("Nuevo DOI (opcional)", 
                    value=current_doi,
                    placeholder="10.1000/ejemplo",
                    help="Ingrese un DOI para actualizar o deje el existente para solo enriquecer")
                
                st.markdown("---")
                st.markdown("**Datos que se actualizarán:**")
                st.caption("• Título, autores, revista, año")
                st.caption("• Abstract estructurado (si está disponible)")
                st.caption("• Términos MeSH, afiliaciones")
                st.caption("• Financiadores, licencia, referencias")
                st.caption("• Estado CrossMark (retractado, actualizado)")
                
                if st.button("🔄 Actualizar desde DOI", use_container_width=True, type="secondary"):
                    with st.spinner("Consultando PubMed y CrossRef..."):
                        try:
                            payload = {"doi": new_doi} if new_doi else {}
                            res = requests.post(
                                f"{API_URL}/papers/{paper['id']}/enrich-doi", 
                                json=payload,
                                timeout=30
                            )
                            if res.status_code == 200:
                                data = res.json()
                                st.success(f"✅ {data.get('mensaje', 'Actualizado')}")
                                if data.get("campos_actualizados"):
                                    st.info(f"Campos actualizados: {', '.join(data['campos_actualizados'])}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                error_detail = res.json().get("detail", res.text)
                                st.error(f"❌ Error: {error_detail}")
                        except requests.exceptions.Timeout:
                            st.error("⏱️ Tiempo de espera agotado. Intente nuevamente.")
                        except Exception as e:
                            st.error(f"❌ Error de conexión: {e}")
                
                # Mostrar metadatos enriquecidos si existen
                if paper.get("mesh_terms"):
                    with st.expander("🏷️ Términos MeSH"):
                        for term in paper.get("mesh_terms", []):
                            st.caption(f"• {term}")
                
                if paper.get("funders"):
                    with st.expander("💰 Financiadores"):
                        for funder in paper.get("funders", []):
                            st.caption(f"• {funder.get('nombre', 'Desconocido')}")

                # --- NUEVA SECCIÓN METADATOS LIBRO ---
                if paper.get("categoria") == "libros":
                    st.markdown("---")
                    st.markdown("#### 📚 Enriquecer Libro")
                    
                    st.info(f"""
                    **ISBN:** {paper.get('isbn') or 'No disponible'}  
                    **Editorial:** {paper.get('editorial') or 'N/A'}  
                    **Edición:** {paper.get('edicion') or 'N/A'}
                    """)
                    
                    search_isbn = st.text_input("ISBN para buscar", 
                        value=paper.get("isbn", ""), 
                        placeholder="978...",
                        help="Deje vacío para intentar detectar automáticamente del título")
                    
                    if st.button("🔍 Buscar Metadatos Online", use_container_width=True, type="primary"):
                        with st.spinner("Buscando en OpenLibrary y Google Books..."):
                            try:
                                payload = {"isbn": search_isbn} if search_isbn else {}
                                res = requests.put(
                                    f"{API_URL}/papers/{paper['id']}/enrich-book",
                                    json=payload,
                                    timeout=30
                                )
                                if res.status_code == 200:
                                    st.success("✅ ¡Libro enriquecido!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error: {res.json().get('detail', 'Ocurrió un error')}")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")


    else:
        st.error("Paper no encontrado")

# 2. VIEW HOME (Swimlanes)
elif st.session_state.current_view == "home":
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

# 2.6 VIEW PAPERS (Categoría: papers con DOI)
elif st.session_state.current_view == "categoria_papers":
    st.markdown("## 📄 Papers Científicos")
    st.markdown("Estudios con DOI validado y metadatos enriquecidos.")
    
    try:
        res = requests.get(f"{API_URL}/papers", params={"categoria": "papers", "limit": 50})
        papers_list = res.json() if res.status_code == 200 else []
    except:
        papers_list = []
    
    if not papers_list:
        st.info("No hay papers en esta categoría. Los estudios con DOI aparecerán aquí.")
    else:
        for i in range(0, len(papers_list), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(papers_list):
                    with cols[j]:
                        render_card(papers_list[i+j], f"papers_{i}")

# 2.7 VIEW LIBROS (Categoría: libros por especialidad)
elif st.session_state.current_view == "categoria_libros":
    st.markdown("## 📚 Libros de Medicina")
    st.markdown("Libros y manuales organizados por especialidad.")
    
    try:
        res = requests.get(f"{API_URL}/papers", params={"categoria": "libros", "limit": 50})
        libros = res.json() if res.status_code == 200 else []
    except:
        libros = []
    
    if not libros:
        st.info("No hay libros en esta categoría. Los documentos con más de 200 páginas se catalogarán aquí.")
    else:
        by_specialty = {}
        for libro in libros:
            spec = libro.get("especialidad") or "General"
            if spec not in by_specialty:
                by_specialty[spec] = []
            by_specialty[spec].append(libro)
        
        for specialty, books in by_specialty.items():
            st.markdown(f"### {specialty}")
            cols = st.columns(4)
            for i, book in enumerate(books[:8]):
                with cols[i % 4]:
                    render_card(book, f"libro_{specialty}")

# 2.8.5 VIEW CATEGORIA GUIAS (Fase 2)
elif st.session_state.current_view == "categoria_guias":
    st.markdown("## 📜 Guías de Práctica Clínica (GPC)")
    st.markdown("Recomendaciones oficiales y consensos internacionales.")
    
    try:
        # Buscamos papers que tengan 'guía' o similar en el tipo o título
        res = requests.get(f"{API_URL}/papers", params={"limit": 50})
        all_p = res.json() if res.status_code == 200 else []
        # Filtrado simple en frontend por ahora (o podríamos añadir un filtro al endpoint)
        guias = [p for p in all_p if any(kw in (p.get('titulo') or "").lower() for kw in ["guía", "guia", "guideline"])]
    except:
        guias = []
    
    if not guias:
        st.info("No se han identificado Guías de Práctica Clínica todavía.")
    else:
        for i in range(0, len(guias), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(guias):
                    with cols[j]:
                        render_card(guias[i+j], f"gpc_{i}")

# 2.8.6 VIEW CALCULADORAS (Fase 2)
elif st.session_state.current_view == "calculadoras":
    st.markdown("## 🧮 Calculadoras Clínicas")
    st.markdown("Herramientas de cálculo rápido para soporte vital.")
    
    c_tab1, c_tab2, c_tab3 = st.tabs(["SOFA Score", "qSOFA", "Wells (TEP)"])
    
    with c_tab1:
        st.subheader("Sequential Organ Failure Assessment (SOFA)")
        col1, col2 = st.columns(2)
        with col1:
            resp = st.selectbox("Respiración (PaO2/FiO2)", [">400", "<400", "<300", "<200 (con soporte)", "<100 (con soporte)"], index=0)
            plat = st.selectbox("Coagulación (Plaquetas x10³/mm³)", [">150", "<150", "<100", "<50", "<20"], index=0)
            liver = st.selectbox("Hígado (Bilirrubina mg/dL)", ["<1.2", "1.2-1.9", "2.0-5.9", "6.0-11.9", ">12.0"], index=0)
        with col2:
            cv = st.selectbox("Cardiovascular (PAM / Vasopresores)", ["PAM >= 70 mmHg", "PAM < 70 mmHg", "Dopa < 5 o Dobuta", "Dopa 6-15 o Nor/Adr <= 0.1", "Dopa > 15 o Nor/Adr > 0.1"], index=0)
            gcs = st.slider("SNC (Glasgow Coma Scale)", 3, 15, 15)
            renal = st.selectbox("Renal (Creatinina o Gasto Urinario)", ["<1.2", "1.2-1.9", "2.0-3.4", "3.5-4.9 o <500ml/d", ">5.0 o <200ml/d"], index=0)
        
        # Lógica de cálculo simplificada para demo
        score_val = 0
        if st.button("Calcular SOFA"):
            # En una implementación real sumaríamos los puntos de cada selectbox
            st.metric("SOFA Score", "Calculando...", delta="Demo")
            st.warning("Implementación completa de lógica aritmética pendiente.")

    with c_tab2:
        st.subheader("quick SOFA (qSOFA)")
        r1 = st.checkbox("Frecuencia Respiratoria >= 22/min")
        r2 = st.checkbox("Alteración del estado mental (GCS < 15)")
        r3 = st.checkbox("Presión Arterial Sistólica <= 100 mmHg")
        qscore = sum([r1, r2, r3])
        st.metric("qSOFA Score", qscore)
        if qscore >= 2:
            st.error("⚠️ Riesgo elevado de mortalidad o estancia prolongada en UCI.")
        else:
            st.success("Bajo riesgo.")

    with c_tab3:
        st.subheader("Criterios de Wells para TEP")
        # Simulación de lista de criterios
        st.info("Calculadora de Wells en desarrollo...")

# 2.8 VIEW SIN CATEGORIZAR (con sub-sección Eliminados)
elif st.session_state.current_view == "sin_categorizar":
    st.markdown("## ❓ Sin Categorizar")
    st.markdown("Documentos pendientes de clasificar.")
    
    tab_sin_cat, tab_deleted = st.tabs(["📋 Pendientes", "🗑️ Eliminados"])
    
    with tab_sin_cat:
        try:
            res = requests.get(f"{API_URL}/papers", params={"categoria": "sin_categorizar", "limit": 50})
            sin_cat = res.json() if res.status_code == 200 else []
        except:
            sin_cat = []
        
        if not sin_cat:
            st.success("✅ No hay documentos sin categorizar.")
        else:
            st.warning(f"Hay {len(sin_cat)} documentos pendientes de clasificar.")
            for paper in sin_cat:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    with c1:
                        st.markdown(f"**{paper.get('titulo', 'Sin título')[:100]}**")
                        if paper.get("abstract"):
                            st.caption(f"{paper['abstract'][:150]}...")
                        elif paper.get("descripcion_libro"):
                            st.caption(f"{paper['descripcion_libro'][:150]}...")
                        st.caption(f"📅 Recibido: {paper.get('fecha_subida', 'Unknown')[:10]} | 📑 Páginas: {paper.get('num_paginas', 'N/A')}")
                    with c2:
                        # Mover con botón destacado
                        opts = ["papers", "libros", "ekg_dojo", "sin_categorizar"]
                        curr_idx = opts.index(paper.get("categoria", "sin_categorizar"))
                        nueva_cat = st.selectbox("Clasificar como:", opts, index=curr_idx, key=f"cat_sel_{paper['id']}")
                        if st.button("🚀 Asignar", key=f"move_{paper['id']}", use_container_width=True):
                            requests.put(f"{API_URL}/papers/{paper['id']}/categoria", json={"categoria": nueva_cat})
                            st.success(f"Movido a {nueva_cat}")
                            time.sleep(0.5)
                            st.rerun()
                    with c3:
                        if st.button("🔍 Ver", key=f"view_sc_{paper['id']}", use_container_width=True):
                            st.session_state.selected_paper_id = paper['id']
                            st.session_state.current_view = "detail"
                            st.rerun()
                        if st.button("🗑️", key=f"del_{paper['id']}", use_container_width=True):
                            requests.delete(f"{API_URL}/papers/{paper['id']}")
                            st.rerun()
    
    with tab_deleted:
        try:
            res = requests.get(f"{API_URL}/papers/deleted", params={"limit": 50})
            deleted = res.json() if res.status_code == 200 else []
        except:
            deleted = []
        
        if not deleted:
            st.info("No hay documentos eliminados.")
        else:
            st.markdown(f"**{len(deleted)}** eliminados (no se volverán a descargar)")
            for paper in deleted:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 2])
                    with c1:
                        st.markdown(f"**{paper.get('titulo', 'Sin título')[:50]}...**")
                    with c2:
                        if st.button("🔄 Restaurar", key=f"rest_{paper['id']}"):
                            requests.put(f"{API_URL}/papers/{paper['id']}/restore")
                            st.rerun()
                        if st.button("⛔ Borrar", key=f"perm_{paper['id']}"):
                            requests.delete(f"{API_URL}/papers/{paper['id']}/permanent")
                            st.rerun()

# 2.9 VIEW SEARCH RESULTS
elif st.session_state.current_view == "search_results":
    q = st.session_state.get("search_q", "")
    st.markdown(f"## 🔍 Resultados para: *{q}*")
    
    try:
        res = requests.get(f"{API_URL}/papers/search", params={"q": q, "limit": 20})
        results = res.json() if res.status_code == 200 else []
    except:
        results = []
    
    if not results:
        st.info("No se encontraron documentos exactos. Probando búsqueda semántica (IA)...")
        # Fallback a RAG
        try:
            res_rag = requests.get(f"{API_URL}/papers/query", params={"q": q})
            results = res_rag.json() if res_rag.status_code == 200 else []
        except:
            results = []
            
    if not results:
        st.warning("No se encontraron resultados ni siquiera con IA.")
    else:
        for i in range(0, len(results), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(results):
                    with cols[j]:
                        render_card(results[i+j], f"search_{i}")

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
        new_channel = c1.text_input("Username del Canal (ej: @librosmedicina)", key="new_channel_input")
        new_name = c2.text_input("Nombre Descriptivo (Opcional)", key="new_name_input")
        if c3.button("Añadir", type="primary", use_container_width=True, key="add_channel_btn"):
            if new_channel:
                if not new_channel.startswith("@"):
                    new_channel = "@" + new_channel
                try:
                    res = requests.post(f"{API_URL}/channels", params={"username": new_channel, "nombre": new_name}, timeout=10)
                    if res.status_code == 200:
                        st.success(f"✅ Canal {new_channel} añadido correctamente")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error: {res.text}")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Timeout - La API está ocupada. Intenta de nuevo.")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
            else:
                st.warning("⚠️ Ingresa el username del canal")

    
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
