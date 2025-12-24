"""
Servicio de Enriquecimiento de Metadatos Multi-Fuente
Integra DOI validation, PubMed (MeSH, afiliaciones, abstract estructurado) y CrossRef (funders, license, referencias)
"""

from habanero import Crossref
import requests
import logging
import re
from typing import Dict, Optional, List
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class MetadataService:
    """Servicio de metadatos multi-fuente con merge inteligente."""
    
    def __init__(self):
        self.cr = Crossref()
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        # Cache simple de DOIs validados
        self._doi_cache = {}
    
    # ==================== VALIDACIÓN DOI ====================
    
    def validar_doi(self, doi: str) -> Dict:
        """
        Valida un DOI verificando formato y resolución via doi.org.
        Retorna: {valido: bool, url_resuelta: str, error: str}
        """
        if not doi:
            return {"valido": False, "error": "DOI vacío"}
        
        # Verificar cache
        if doi in self._doi_cache:
            return self._doi_cache[doi]
        
        # Validar formato DOI (10.XXXX/...)
        doi_pattern = r'^10\.\d{4,}/[^\s]+$'
        if not re.match(doi_pattern, doi):
            result = {"valido": False, "error": "Formato DOI inválido"}
            self._doi_cache[doi] = result
            return result
        
        # Resolver via doi.org
        try:
            resp = requests.head(
                f"https://doi.org/{doi}",
                allow_redirects=True,
                timeout=10
            )
            if resp.status_code == 200:
                result = {
                    "valido": True,
                    "url_resuelta": resp.url,
                    "error": None
                }
            else:
                result = {
                    "valido": False,
                    "url_resuelta": None,
                    "error": f"HTTP {resp.status_code}"
                }
        except Exception as e:
            result = {"valido": False, "error": str(e)}
        
        self._doi_cache[doi] = result
        return result
    
    # ==================== PUBMED EXTENDIDO ====================
    
    def _try_pubmed(self, doi: str) -> Dict:
        """Busca metadata extendida en PubMed usando DOI."""
        try:
            # Paso 1: Buscar PMID por DOI
            search_url = f"{self.pubmed_base}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": f"{doi}[doi]",
                "retmode": "json"
            }
            resp = requests.get(search_url, params=params, timeout=10)
            data = resp.json()
            
            id_list = data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return {}
            
            pmid = id_list[0]
            
            # Paso 2: Obtener detalles del artículo (XML completo)
            fetch_url = f"{self.pubmed_base}/efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml"
            }
            resp = requests.get(fetch_url, params=params, timeout=15)
            
            # Parsear XML
            root = ET.fromstring(resp.text)
            article = root.find(".//Article")
            if article is None:
                return {}
            
            # === CAMPOS BÁSICOS ===
            title_el = article.find(".//ArticleTitle")
            title = title_el.text if title_el is not None else None
            
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else None
            
            year_el = article.find(".//PubDate/Year")
            year = int(year_el.text) if year_el is not None and year_el.text else None
            
            # === ABSTRACT ESTRUCTURADO ===
            abstract_sections = {}
            abstract_full = ""
            abstract_elements = article.findall(".//Abstract/AbstractText")
            
            for abs_el in abstract_elements:
                label = abs_el.get("Label", "texto")  # BACKGROUND, METHODS, RESULTS, etc.
                text = abs_el.text or ""
                label_lower = label.lower()
                
                # Mapear labels comunes a español
                label_map = {
                    "background": "antecedentes",
                    "objective": "objetivo",
                    "objectives": "objetivo",
                    "methods": "metodos",
                    "results": "resultados",
                    "conclusions": "conclusiones",
                    "conclusion": "conclusiones"
                }
                mapped_label = label_map.get(label_lower, label_lower)
                abstract_sections[mapped_label] = text
                abstract_full += f"{text} "
            
            # Si solo hay un AbstractText sin Label, es abstract simple
            if len(abstract_elements) == 1 and not abstract_elements[0].get("Label"):
                abstract_full = abstract_elements[0].text or ""
            
            # === AUTORES CON AFILIACIONES ===
            autores = []
            affiliaciones = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                first = author.find("ForeName")
                if last is not None:
                    nombre = f"{first.text if first is not None else ''} {last.text}".strip()
                    autores.append(nombre)
                    
                    # Afiliaciones del autor
                    for aff in author.findall(".//AffiliationInfo/Affiliation"):
                        if aff.text:
                            affiliaciones.append({
                                "autor": nombre,
                                "institucion": aff.text
                            })
            
            # === MeSH TERMS ===
            mesh_terms = []
            mesh_list = root.find(".//MeshHeadingList")
            if mesh_list is not None:
                for mesh in mesh_list.findall(".//MeshHeading"):
                    descriptor = mesh.find("DescriptorName")
                    if descriptor is not None and descriptor.text:
                        # Incluir qualifiers si existen
                        qualifiers = [q.text for q in mesh.findall("QualifierName") if q.text]
                        if qualifiers:
                            mesh_terms.append(f"{descriptor.text}/{'/'.join(qualifiers)}")
                        else:
                            mesh_terms.append(descriptor.text)
            
            return {
                "doi": doi,
                "pmid": pmid,
                "titulo": title,
                "revista": journal,
                "año": year,
                "autores": autores,
                "abstract": abstract_full.strip(),
                "abstract_estructurado": abstract_sections if len(abstract_sections) > 1 else {},
                "affiliaciones": affiliaciones,
                "mesh_terms": mesh_terms,
            }
            
        except Exception as e:
            logger.debug(f"PubMed lookup falló para DOI {doi}: {e}")
            return {}
    
    # ==================== CROSSREF EXTENDIDO ====================
    
    def _try_crossref(self, doi: str) -> Dict:
        """Consulta CrossRef API para obtener metadatos extendidos."""
        try:
            res = self.cr.works(ids=doi)
            message = res.get('message', {})
            
            # === CAMPOS BÁSICOS ===
            titles = message.get('title', [])
            title = titles[0] if titles else None
            
            container_titles = message.get('container-title', [])
            journal = container_titles[0] if container_titles else None
            
            issued = message.get('issued', {}).get('date-parts', [])
            year = issued[0][0] if issued and issued[0] else None
            
            publish_date = None
            if issued and len(issued[0]) >= 3:
                publish_date = f"{issued[0][0]}-{issued[0][1]:02d}-{issued[0][2]:02d}"
            elif issued and len(issued[0]) == 2:
                publish_date = f"{issued[0][0]}-{issued[0][1]:02d}-01"
            
            # Autores
            autores = []
            for auth in message.get('author', []):
                name = f"{auth.get('given', '')} {auth.get('family', '')}".strip()
                if name:
                    autores.append(name)
            
            # Abstract (limpiar HTML)
            abstract = message.get('abstract', '')
            if abstract and "<" in abstract:
                abstract = re.sub('<[^<]+?>', '', abstract)
            
            # === FUNDERS (Financiadores) ===
            funders = []
            for funder in message.get('funder', []):
                funder_entry = {
                    "nombre": funder.get('name'),
                    "doi": funder.get('DOI'),
                    "award": funder.get('award', [])
                }
                if funder_entry["nombre"]:
                    funders.append(funder_entry)
            
            # === LICENSE ===
            license_url = None
            licenses = message.get('license', [])
            if licenses:
                # Preferir la primera URL disponible
                license_url = licenses[0].get('URL')
            
            # === CROSSMARK STATUS ===
            crossmark_status = "current"  # default
            # Verificar si hay actualizaciones o retracciones
            update_to = message.get('update-to', [])
            if update_to:
                crossmark_status = "actualizado"
            # Verificar assertions (retracciones, correcciones)
            for assertion in message.get('assertion', []):
                if assertion.get('name') == 'retracted':
                    crossmark_status = "retractado"
                    break
                elif assertion.get('name') == 'correction':
                    crossmark_status = "corregido"
            
            # === REFERENCIAS ===
            referencias = []
            for ref in message.get('reference', []):
                ref_doi = ref.get('DOI')
                if ref_doi:
                    referencias.append({
                        "doi": ref_doi,
                        "key": ref.get('key', ''),
                        "año": ref.get('year')
                    })
            
            # === TIPO DE ESTUDIO (aproximado) ===
            tipo = message.get('type', '')  # journal-article, book-chapter, etc.
            
            return {
                "doi": doi,
                "titulo": title,
                "revista": journal,
                "año": year,
                "fecha_publicacion": publish_date,
                "autores": autores,
                "abstract": abstract.strip() if abstract else None,
                "funders": funders,
                "license": license_url,
                "crossmark_status": crossmark_status,
                "referencias": referencias,
                "tipo_crossref": tipo,
            }
            
        except Exception as e:
            logger.error(f"Error consultando CrossRef para DOI {doi}: {e}")
            return {}
    
    # ==================== MERGE INTELIGENTE ====================
    
    def _fusionar_metadatos(self, pubmed: Dict, crossref: Dict) -> Dict:
        """
        Fusiona datos de PubMed y CrossRef con estrategia de priorización:
        - PMID, MeSH, afiliaciones, abstract estructurado → PubMed
        - Funders, license, referencias → CrossRef
        - Título, abstract, autores → PubMed si disponible, sino CrossRef
        - Año → El más temprano válido
        """
        merged = {}
        
        # Campos exclusivos de PubMed
        merged["pmid"] = pubmed.get("pmid")
        merged["mesh_terms"] = pubmed.get("mesh_terms", [])
        merged["affiliaciones"] = pubmed.get("affiliaciones", [])
        merged["abstract_estructurado"] = pubmed.get("abstract_estructurado", {})
        
        # Campos exclusivos de CrossRef
        merged["funders"] = crossref.get("funders", [])
        merged["license"] = crossref.get("license")
        merged["referencias"] = crossref.get("referencias", [])
        merged["crossmark_status"] = crossref.get("crossmark_status")
        merged["fecha_publicacion"] = crossref.get("fecha_publicacion")
        
        # Campos con prioridad PubMed > CrossRef
        merged["titulo"] = pubmed.get("titulo") or crossref.get("titulo")
        merged["revista"] = pubmed.get("revista") or crossref.get("revista")
        merged["autores"] = pubmed.get("autores") if pubmed.get("autores") else crossref.get("autores", [])
        merged["abstract"] = pubmed.get("abstract") or crossref.get("abstract")
        
        # DOI (debería ser el mismo)
        merged["doi"] = pubmed.get("doi") or crossref.get("doi")
        
        # Año: preferir el más temprano (evitar años futuros erróneos)
        pubmed_year = pubmed.get("año")
        crossref_year = crossref.get("año")
        if pubmed_year and crossref_year:
            merged["año"] = min(pubmed_year, crossref_year)
        else:
            merged["año"] = pubmed_year or crossref_year
        
        return merged
    
    # ==================== API PRINCIPAL ====================
    
    def get_metadata_by_doi(self, doi: str, validar: bool = True) -> Dict:
        """
        Obtiene metadatos enriquecidos para un DOI.
        Consulta ambas fuentes y fusiona resultados.
        
        Args:
            doi: El DOI del paper
            validar: Si True, valida el DOI via doi.org primero
            
        Returns:
            Dict con metadatos fusionados y metadata_source indicando origen
        """
        if not doi:
            return {}
        
        # Normalizar DOI (quitar prefijos comunes)
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")
        elif doi.startswith("http://doi.org/"):
            doi = doi.replace("http://doi.org/", "")
        elif doi.startswith("doi:"):
            doi = doi.replace("doi:", "")
        
        # Validación DOI (opcional pero recomendada)
        doi_validado = False
        if validar:
            validation = self.validar_doi(doi)
            doi_validado = validation.get("valido", False)
            if not doi_validado:
                logger.warning(f"DOI no válido: {doi} - {validation.get('error')}")
                # Continuamos de todos modos, quizás las APIs lo tengan
        
        # Consultar ambas fuentes
        pubmed_data = self._try_pubmed(doi)
        crossref_data = self._try_crossref(doi)
        
        # Determinar fuente y fusionar
        if pubmed_data and crossref_data:
            meta = self._fusionar_metadatos(pubmed_data, crossref_data)
            meta["metadata_source"] = "merged"
            logger.info(f"✅ Metadatos fusionados para DOI {doi} (PubMed + CrossRef)")
        elif pubmed_data:
            meta = pubmed_data
            meta["metadata_source"] = "pubmed"
            logger.info(f"✅ Metadatos de PubMed para DOI {doi}")
        elif crossref_data:
            meta = crossref_data
            meta["metadata_source"] = "crossref"
            logger.info(f"✅ Metadatos de CrossRef para DOI {doi}")
        else:
            logger.warning(f"⚠️ No se encontraron metadatos para DOI {doi}")
            return {}
        
        # Agregar estado de validación
        meta["doi_validado"] = doi_validado
        
        return meta
    
    # ==================== UTILIDADES ====================
    
    def enriquecer_paper(self, paper_data: Dict) -> Dict:
        """
        Toma datos parciales de un paper y los enriquece con metadatos externos.
        Útil para llenar campos faltantes sin sobrescribir datos existentes.
        """
        doi = paper_data.get("doi")
        if not doi:
            return paper_data
        
        meta = self.get_metadata_by_doi(doi)
        if not meta:
            return paper_data
        
        # Solo llenar campos vacíos
        enriched = paper_data.copy()
        for key, value in meta.items():
            if key not in enriched or not enriched[key]:
                enriched[key] = value
        
        return enriched
