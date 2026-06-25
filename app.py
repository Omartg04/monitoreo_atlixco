"""
Atlixco PIE – Visualizador de Monitoreo y Auditoría de Encuestas
Atlixco, Puebla · Encuesta L2 · 2026
Ejecutar: streamlit run app.py
"""
import copy
import json
import time
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import LoginError

from config import (
    VERDE, VERDE_L, AZUL, AZUL_L, NARANJA, ROJO, AMARILLO, GRIS_BG,
    DUR_MIN_MIN, DUR_MAX_MIN, AUTO_REFRESH_SEC,
    META_GLOBAL, METAS_POR_SECCION,
    SECCIONES_POR_ZONA, SECCIONES_FUERA_MUESTRA,
    ZONA_NOMBRES, ZONA_COLORES,
    GEOJSON_SECCIONES, ATLIXCO_CENTRO, ATLIXCO_ZOOM,
    CANDIDATOS, ATRIBUTOS_BLOQUE7, ROLES,
)
import kpis
import flags
from transform_atlixco import get_encuestas
from bubble_connector import normalizar_nombre

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Atlixco PIE 2026",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; background: {GRIS_BG}; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; }}

.atl-header {{
    background: linear-gradient(120deg, {AZUL} 0%, {AZUL_L} 60%, {VERDE} 100%);
    color: white; padding: 16px 26px; border-radius: 10px;
    display: flex; align-items: center; gap: 18px; margin-bottom: 1.1rem;
}}
.atl-header h1 {{ margin: 0; font-size: 1.5rem; font-weight: 700; line-height: 1.2; }}
.atl-header p  {{ margin: 2px 0 0; font-size: 0.82rem; opacity: 0.82; }}

.kpi-card {{
    background: white; border-radius: 9px; padding: 14px 18px;
    border-left: 5px solid {VERDE}; box-shadow: 0 2px 6px rgba(0,0,0,.07);
    height: 100%;
}}
.kpi-val   {{ font-size: 2rem; font-weight: 700; color: {VERDE};
              font-family: 'IBM Plex Mono', monospace; line-height: 1; }}
.kpi-label {{ font-size: 0.73rem; color: #555; text-transform: uppercase;
              letter-spacing:.05em; margin-top:4px; }}
.kpi-sub   {{ font-size: 0.78rem; color: #888; margin-top: 3px; }}
.kpi-card.azul    {{ border-left-color: {AZUL_L}; }}
.kpi-card.azul .kpi-val {{ color: {AZUL_L}; }}
.kpi-card.naranja {{ border-left-color: {NARANJA}; }}
.kpi-card.naranja .kpi-val {{ color: {NARANJA}; }}
.kpi-card.rojo    {{ border-left-color: {ROJO}; }}
.kpi-card.rojo .kpi-val {{ color: {ROJO}; }}
.kpi-card.amarillo {{ border-left-color: {AMARILLO}; }}
.kpi-card.amarillo .kpi-val {{ color: {AMARILLO}; }}

.sec-title {{
    font-size: 1rem; font-weight: 600; color: {AZUL};
    border-bottom: 2px solid {VERDE_L}; padding-bottom: 3px; margin: 16px 0 10px;
}}
.zona-chip {{
    display: inline-block; font-size: 0.72rem; font-weight: 600;
    padding: 2px 8px; border-radius: 99px; color: white; margin-right: 4px;
}}
.ts-badge {{
    font-size: 0.72rem; color: #888; font-family: 'IBM Plex Mono', monospace;
    background: #eef1f5; border-radius: 4px; padding: 2px 8px; display: inline-block;
}}
section[data-testid="stSidebar"] {{ background: {AZUL}; }}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] .stMarkdown p {{ color: #B8CDE0 !important; }}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{ color: white !important; }}
</style>
""", unsafe_allow_html=True)


# ── Autenticación ──────────────────────────────────────────────────────────────
_raw_users = st.secrets.get("auth", {}).get("credentials", {}).get("usernames", {})
_credentials = {
    "usernames": {
        str(u): {"name": str(d["name"]), "password": str(d["password"])}
        for u, d in _raw_users.items()
    }
}
_cookie_name   = str(st.secrets.get("auth", {}).get("cookie_name",        "atlixco_pie_session"))
_cookie_key    = str(st.secrets.get("auth", {}).get("cookie_key",         "atlixco_pie_dev_key"))
_cookie_expiry = int(st.secrets.get("auth", {}).get("cookie_expiry_days", 1))

authenticator = stauth.Authenticate(_credentials, _cookie_name, _cookie_key, _cookie_expiry)

try:
    authenticator.login(location="main", key="atlixco_pie_login")
except LoginError as e:
    st.error(str(e))
    st.stop()

if not st.session_state.get("authentication_status"):
    if st.session_state.get("authentication_status") is False:
        st.error("Usuario o contraseña incorrectos.")
    else:
        st.info("Ingresa tus credenciales para acceder a Atlixco PIE.")
    st.stop()

_username        = st.session_state["username"]
_rol_cfg         = ROLES.get(_username, {"rol": "zona", "zonas": [], "secciones": []})
_rol             = _rol_cfg.get("rol", "zona")
_secs_permitidas = _rol_cfg.get("secciones", [])

with st.sidebar:
    authenticator.logout(button_name="🔒 Cerrar sesión", location="sidebar", key="atlixco_pie_logout")
    st.markdown(f"**{st.session_state.get('name', _username)}**")
    st.caption("Coordinación estatal" if _rol == "estatal" else
               f"Zonas: {', '.join(ZONA_NOMBRES[z] for z in _rol_cfg.get('zonas', []))}")
    st.markdown("---")


# ── Auto-refresh ───────────────────────────────────────────────────────────────
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()

if time.time() - st.session_state["last_refresh"] > AUTO_REFRESH_SEC:
    st.session_state["last_refresh"] = time.time()
    st.rerun()


# ── Carga de datos ─────────────────────────────────────────────────────────────
API_KEY = st.secrets.get("BUBBLE_API_KEY", "")

_filtro_secciones = None if _rol == "estatal" else _secs_permitidas
with st.spinner("Cargando datos del operativo…"):
    df_raw, ultima_actualizacion = get_encuestas(API_KEY, secciones=_filtro_secciones)

with st.spinner("Calculando flags de calidad…"):
    df_raw = flags.aplicar_todos_los_flags(df_raw) if not df_raw.empty else df_raw


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_geojson(path_str: str):
    p = Path(path_str)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

GEOJSON = load_geojson(GEOJSON_SECCIONES)


# ── Helpers visuales ───────────────────────────────────────────────────────────
def kpi(col, val, label, sub="", cls=""):
    col.markdown(f"""
    <div class="kpi-card {cls}">
      <div class="kpi-val">{val}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)


def color_semaforo(val):
    if val == "verde":    return "background-color:#D4EDDA;color:#155724;font-weight:700"
    if val == "amarillo": return "background-color:#FFF3CD;color:#856404;font-weight:700"
    if val == "rojo":     return "background-color:#F8D7DA;color:#721C24;font-weight:700"
    return ""


def color_pct(val):
    if pd.isna(val): return ""
    if val >= 100: return "background-color:#D4EDDA;color:#155724;font-weight:700"
    if val >= 60:  return "background-color:#FFF3CD;color:#856404;font-weight:700"
    return               "background-color:#F8D7DA;color:#721C24;font-weight:700"


def color_dur(val):
    if pd.isna(val): return ""
    if DUR_MIN_MIN <= val <= DUR_MAX_MIN:
        return "background-color:#D4EDDA;color:#155724;font-weight:600"
    if val < DUR_MIN_MIN:
        return "background-color:#F8D7DA;color:#721C24;font-weight:600"
    return "background-color:#FFF3CD;color:#856404;font-weight:600"


def _bounds_from_geometry(geometry: dict):
    lons, lats = [], []
    def _walk(coords):
        if isinstance(coords[0], (int, float)):
            lons.append(coords[0]); lats.append(coords[1])
        else:
            for c in coords: _walk(c)
    _walk(geometry["coordinates"])
    if not lons: return None
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def pct_bar(df_in, campo, titulo, orden=None, colors=None, height=260):
    if campo not in df_in.columns or df_in[campo].dropna().empty:
        return None
    cnt = df_in[campo].value_counts(normalize=True).mul(100).round(1).reset_index()
    cnt.columns = ["Respuesta", "Porcentaje"]
    if orden:
        cnt["Respuesta"] = pd.Categorical(cnt["Respuesta"], categories=orden, ordered=True)
        cnt = cnt.sort_values("Respuesta")
    else:
        cnt = cnt.sort_values("Porcentaje", ascending=True)
    cs = colors or [VERDE_L, VERDE, AZUL_L, NARANJA, ROJO, AMARILLO, "#aaa"]
    fig = px.bar(cnt, x="Porcentaje", y="Respuesta", orientation="h",
                 color="Respuesta", color_discrete_sequence=cs,
                 text=cnt["Porcentaje"].apply(lambda x: f"{x}%"),
                 title=titulo, height=height)
    fig.update_traces(textposition="outside")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                      showlegend=False, font_family="IBM Plex Sans",
                      margin=dict(t=45, b=5, l=220), xaxis_range=[0, 105])
    return fig


def show_chart(fig, **kwargs):
    if fig:
        st.plotly_chart(fig, use_container_width=True, **kwargs)
    else:
        st.info("Sin datos suficientes para esta gráfica.")


# ── Sidebar — filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Filtros")
    st.markdown("---")

    # Zona
    if _rol == "estatal":
        zona_opts = {0: "Todas las zonas"} | ZONA_NOMBRES
        zona_sel  = st.selectbox(
            "Zona", list(zona_opts.keys()),
            format_func=lambda z: zona_opts[z],
        )
    else:
        zona_sel = _rol_cfg.get("zonas", [0])[0]
        st.markdown(f"**Zona:** {ZONA_NOMBRES.get(zona_sel, zona_sel)}")

    # Sección (filtrada por zona)
    if zona_sel == 0:
        secciones_disp = sorted(METAS_POR_SECCION.keys())
    else:
        secciones_disp = sorted(SECCIONES_POR_ZONA.get(zona_sel, []))

    sec_opts = ["Todas"] + secciones_disp
    sec_sel  = st.selectbox(
        "Sección electoral", sec_opts,
        format_func=lambda s: "Todas" if s == "Todas"
        else f"{s} — {METAS_POR_SECCION.get(s, {}).get('tipo', '')}",
    )

    # Fecha
    if not df_raw.empty and "fecha" in df_raw.columns:
        fechas_disp = sorted(df_raw["fecha"].dropna().unique().tolist())
    else:
        fechas_disp = []
    fecha_sel = st.multiselect(
        "Fecha de levantamiento", fechas_disp, default=fechas_disp,
        format_func=lambda d: d.strftime("%a %d-%b") if hasattr(d, "strftime") else str(d),
    )

    st.markdown("---")

    # Encuestador
    enc_opts = ["Todos"] + (
        sorted(df_raw["encuestador_nombre"].dropna().unique().tolist())
        if not df_raw.empty else []
    )
    enc_sel = st.selectbox("Encuestador", enc_opts)

    st.markdown("---")

    if st.button("🔄 Actualizar datos", use_container_width=True):
        get_encuestas(API_KEY, secciones=_filtro_secciones, force_refresh=True)
        st.session_state["last_refresh"] = time.time()
        st.rerun()

    if ultima_actualizacion:
        ts_local = ultima_actualizacion.astimezone().strftime("%H:%M:%S")
        st.markdown(f'<div class="ts-badge">⏱ Actualizado: {ts_local}</div>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Atlixco PIE** · L2 · 2026")


# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_raw.copy()

if zona_sel != 0:
    df = df[df["zona"] == zona_sel]

if sec_sel != "Todas":
    df = df[df["seccion_electoral"] == sec_sel]

if fecha_sel and "fecha" in df.columns:
    df = df[df["fecha"].isin(fecha_sel)]

if enc_sel != "Todos":
    df = df[df["encuestador_nombre"] == enc_sel]


# ── Header ─────────────────────────────────────────────────────────────────────
if zona_sel == 0:
    titulo_geo = "Atlixco, Puebla"
    zona_color = AZUL
elif sec_sel != "Todas":
    titulo_geo = f"{ZONA_NOMBRES[zona_sel]} — Sección {sec_sel}"
    zona_color = ZONA_COLORES[zona_sel]
else:
    titulo_geo = ZONA_NOMBRES[zona_sel]
    zona_color = ZONA_COLORES[zona_sel]

st.markdown(f"""
<div class="atl-header">
  <div style="font-size:2.2rem">📋</div>
  <div>
    <h1>Monitoreo y Auditoría de Encuestas — {titulo_geo}</h1>
    <p>Data &amp; AI Inclusion Technologies · L2 Atlixco · {len(df):,} registros en vista actual</p>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
if _rol == "estatal":
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "📋  Planeación",
        "📈  Avance vs Meta",
        "🗺️  Mapa de Cobertura",
        "🚩  Flags de Calidad y Sesgo",
        "📊  Resultados del Instrumento",
    ])
else:
    tab0, tab1, tab2, tab3 = st.tabs([
        "📋  Planeación",
        "📈  Avance vs Meta",
        "🗺️  Mapa de Cobertura",
        "🚩  Flags de Calidad y Sesgo",
    ])
    tab4 = None


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — PLANEACIÓN  (100% estático — datos de config.py, sin Bubble)
# ══════════════════════════════════════════════════════════════════════════════
with tab0:

    st.markdown(f"""
    <div class="atl-header" style="margin-bottom:1.4rem">
      <div style="font-size:2rem">🗂️</div>
      <div>
        <h1 style="font-size:1.2rem">Planeación del operativo — Atlixco PIE 2026</h1>
        <p>42 secciones · 6 zonas geográficas · n=840 encuestas objetivo</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs de planeación ─────────────────────────────────────────────────────
    pk1, pk2, pk3, pk4, pk5 = st.columns(5)
    kpi(pk1, "42",          "Secciones en muestra",  "municipio 19 · Atlixco")
    kpi(pk2, "840",         "Meta global",            "encuestas objetivo", "azul")
    kpi(pk3, "6",           "Zonas de operación",     "agrupación geográfica", "naranja")
    total_h = sum(v["cuotas"]["H"] for v in METAS_POR_SECCION.values())
    total_m = sum(v["cuotas"]["M"] for v in METAS_POR_SECCION.values())
    kpi(pk4, f"{total_h}",  "Cuota hombres",          f"{round(100*total_h/840,1)}% del total")
    kpi(pk5, f"{total_m}",  "Cuota mujeres",          f"{round(100*total_m/840,1)}% del total")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Resumen por zona ───────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">Distribución por zona</div>', unsafe_allow_html=True)

    resumen_zonas = []
    for z_id, z_nombre in ZONA_NOMBRES.items():
        secs   = SECCIONES_POR_ZONA[z_id]
        meta_z = sum(METAS_POR_SECCION[s]["meta_encuestas"] for s in secs)
        h_z    = sum(METAS_POR_SECCION[s]["cuotas"]["H"]    for s in secs)
        m_z    = sum(METAS_POR_SECCION[s]["cuotas"]["M"]    for s in secs)
        tipos  = [METAS_POR_SECCION[s]["tipo"] for s in secs]
        n_u    = tipos.count("Urbana")
        n_m    = tipos.count("Mixta")
        n_r    = tipos.count("Rural")
        resumen_zonas.append({
            "zona_id":    z_id,
            "Zona":       z_nombre,
            "Secciones":  len(secs),
            "Meta":       meta_z,
            "% del total": round(100 * meta_z / 840, 1),
            "Cuota H":    h_z,
            "Cuota M":    m_z,
            "Urbanas":    n_u,
            "Mixtas":     n_m,
            "Rurales":    n_r,
        })

    df_zonas = pd.DataFrame(resumen_zonas)

    # Gráfica de carga por zona
    fig_carga = px.bar(
        df_zonas.sort_values("Meta", ascending=True),
        x="Meta", y="Zona", orientation="h",
        color="Zona",
        color_discrete_map={
            ZONA_NOMBRES[z]: ZONA_COLORES[z] for z in ZONA_NOMBRES
        },
        text=df_zonas.sort_values("Meta", ascending=True)["Meta"],
        title="Encuestas objetivo por zona",
        height=320,
    )
    fig_carga.update_traces(textposition="outside")
    fig_carga.update_layout(
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        font_family="IBM Plex Sans", margin=dict(t=45, b=10, l=10),
        xaxis_range=[0, df_zonas["Meta"].max() * 1.15],
    )

    gc1, gc2 = st.columns([3, 2])
    with gc1:
        st.plotly_chart(fig_carga, use_container_width=True)
    with gc2:
        tbl_z = df_zonas[["Zona", "Secciones", "Meta", "% del total",
                           "Cuota H", "Cuota M", "Urbanas", "Mixtas", "Rurales"]].copy()
        tbl_z["% del total"] = tbl_z["% del total"].apply(lambda v: f"{v}%")
        st.dataframe(
            tbl_z.style.set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
            use_container_width=True, hide_index=True,
        )

    # ── Composición por tipo de sección ───────────────────────────────────────
    st.markdown('<div class="sec-title">Composición por tipo de sección</div>',
                unsafe_allow_html=True)

    tipos_global = {"Urbana": 0, "Mixta": 0, "Rural": 0}
    meta_tipo    = {"Urbana": 0, "Mixta": 0, "Rural": 0}
    for v in METAS_POR_SECCION.values():
        tipos_global[v["tipo"]] += 1
        meta_tipo[v["tipo"]]    += v["meta_encuestas"]

    tc1, tc2, tc3 = st.columns(3)
    for col, tipo, color in [
        (tc1, "Urbana", AZUL_L),
        (tc2, "Mixta",  NARANJA),
        (tc3, "Rural",  VERDE),
    ]:
        n   = tipos_global[tipo]
        m   = meta_tipo[tipo]
        col.markdown(f"""
        <div class="kpi-card" style="border-left-color:{color}">
          <div class="kpi-val" style="color:{color}">{n}</div>
          <div class="kpi-label">Secciones {tipo}s</div>
          <div class="kpi-sub">{m} encuestas · {round(100*m/840,1)}% del total</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Mapa de zonas ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">Mapa de zonas de operación</div>',
                unsafe_allow_html=True)

    if GEOJSON is None:
        st.warning(f"No se encontró {GEOJSON_SECCIONES}.")
    else:
        geojson_plan = copy.deepcopy(GEOJSON)
        for feature in geojson_plan["features"]:
            sec   = feature["properties"].get("seccion")
            info  = METAS_POR_SECCION.get(sec)
            if info is None:
                feature["properties"].update({
                    "zona_id": 0, "zona_nombre": "Fuera de muestra",
                    "meta": 0, "tipo": "—", "ln_total": 0,
                })
            else:
                feature["properties"].update({
                    "zona_id":    info["zona"],
                    "zona_nombre": ZONA_NOMBRES[info["zona"]],
                    "meta":       info["meta_encuestas"],
                    "tipo":       info["tipo"],
                    "ln_total":   info["ln_total"],
                    "cuota_h":    info["cuotas"]["H"],
                    "cuota_m":    info["cuotas"]["M"],
                })

        def style_zona(feature):
            z_id = feature["properties"].get("zona_id", 0)
            if z_id == 0:
                return {"fillColor": "#DDDDDD", "color": "#AAAAAA",
                        "weight": 0.5, "fillOpacity": 0.25}
            return {
                "fillColor": ZONA_COLORES[z_id],
                "color":     "#FFFFFF",
                "weight":    1.5,
                "fillOpacity": 0.72,
            }

        tooltip_plan = folium.GeoJsonTooltip(
            fields=["seccion", "zona_nombre", "tipo", "meta", "ln_total",
                    "cuota_h", "cuota_m"],
            aliases=["Sección:", "Zona:", "Tipo:", "Meta enc.:",
                     "Lista nominal:", "Cuota H:", "Cuota M:"],
            localize=True, sticky=True, labels=True,
            style=(
                "background-color:white;border:1px solid #ccc;"
                "border-radius:6px;padding:8px 12px;"
                "font-family:'IBM Plex Sans',sans-serif;font-size:13px;"
            ),
        )

        mapa_plan = folium.Map(
            location=ATLIXCO_CENTRO, zoom_start=ATLIXCO_ZOOM,
            tiles="CartoDB positron",
        )
        folium.GeoJson(
            geojson_plan, style_function=style_zona,
            highlight_function=lambda f: {"fillOpacity": 0.95, "weight": 3,
                                          "color": "#222"},
            tooltip=tooltip_plan, name="Zonas",
        ).add_to(mapa_plan)

        # Leyenda de zonas
        leyenda_html = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                    background:white;padding:10px 14px;border-radius:8px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.15);
                    font-family:'IBM Plex Sans',sans-serif;font-size:12px;">
        """
        for z_id, z_nombre in ZONA_NOMBRES.items():
            color = ZONA_COLORES[z_id]
            leyenda_html += (
                f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">'
                f'<div style="width:14px;height:14px;border-radius:3px;'
                f'background:{color};flex-shrink:0"></div>'
                f'<span>{z_nombre}</span></div>'
            )
        leyenda_html += "</div>"
        mapa_plan.get_root().html.add_child(folium.Element(leyenda_html))

        st_folium(mapa_plan, width="100%", height=520,
                  returned_objects=[], key="mapa_planeacion")

    # ── Detalle por sección ────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">Detalle por sección</div>', unsafe_allow_html=True)

    # Filtro de zona dentro del tab (independiente del sidebar)
    zona_plan_opts = {0: "Todas las zonas"} | ZONA_NOMBRES
    zona_plan_sel  = st.selectbox(
        "Filtrar por zona", list(zona_plan_opts.keys()),
        format_func=lambda z: zona_plan_opts[z],
        key="zona_plan_detalle",
    )

    filas_det = []
    for sec, v in METAS_POR_SECCION.items():
        if zona_plan_sel != 0 and v["zona"] != zona_plan_sel:
            continue
        filas_det.append({
            "Sección":    sec,
            "Zona":       ZONA_NOMBRES[v["zona"]],
            "Tipo":       v["tipo"],
            "Lista nominal": v["ln_total"],
            "Meta total": v["meta_encuestas"],
            "Cuota H":    v["cuotas"]["H"],
            "Cuota M":    v["cuotas"]["M"],
            "% H":        round(100 * v["cuotas"]["H"] / v["meta_encuestas"], 1),
            "% M":        round(100 * v["cuotas"]["M"] / v["meta_encuestas"], 1),
        })

    df_det = pd.DataFrame(filas_det).sort_values(["Zona", "Sección"])

    st.dataframe(
        df_det.style
        .format({"Lista nominal": "{:,}", "% H": "{:.1f}%", "% M": "{:.1f}%"})
        .set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
        use_container_width=True, hide_index=True,
        height=min(80 + len(df_det) * 35, 560),
    )

    # Descarga CSV
    csv_bytes = df_det.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar tabla como CSV",
        data=csv_bytes,
        file_name="planeacion_atlixco_2026.csv",
        mime="text/csv",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — AVANCE VS META
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if df_raw.empty:
        st.info("Sin datos — verifica la conexión a Bubble (config.BUBBLE_ENDPOINT).")
    else:
        # Meta y avance de la vista actual
        if zona_sel == 0 and sec_sel == "Todas":
            meta_vista = META_GLOBAL
            df_kpi     = df_raw
        elif sec_sel != "Todas":
            meta_vista = METAS_POR_SECCION[sec_sel]["meta_encuestas"]
            df_kpi     = df
        else:
            meta_vista = sum(
                METAS_POR_SECCION[s]["meta_encuestas"]
                for s in SECCIONES_POR_ZONA.get(zona_sel, [])
            )
            df_kpi = df

        terminadas_vista = int(df_kpi["terminada"].sum())
        avance_pct_vista = round(100 * terminadas_vista / meta_vista, 1) if meta_vista else 0.0

        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        kpi(r1c1, f"{len(df_kpi):,}",        "Encuestas levantadas",   "en la vista actual")
        kpi(r1c2, f"{terminadas_vista:,}",    "Encuestas terminadas",
            f"{round(100*terminadas_vista/max(len(df_kpi),1),1)}% del total levantado", "azul")
        kpi(r1c3, f"{meta_vista:,}",          "Meta (vista actual)",
            f"Global Atlixco: {META_GLOBAL:,}", "naranja")
        kpi(r1c4, f"{avance_pct_vista}%",     "Avance vs meta",
            f"faltan {max(meta_vista - terminadas_vista, 0):,}",
            "rojo" if avance_pct_vista < 60 else ("amarillo" if avance_pct_vista < 100 else ""))

        df_conf = df_kpi[df_kpi["duracion_confiable"]] if "duracion_confiable" in df_kpi.columns else df_kpi
        prom_t  = round(df_conf["duracion_min"].mean(), 1) if len(df_conf) else 0
        st.caption(f"Duración promedio de entrevista: **{prom_t}'** (rango esperado {DUR_MIN_MIN}–{DUR_MAX_MIN} min)")
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Avance por zona (nueva sección) ────────────────────────────────────
        if zona_sel == 0 and sec_sel == "Todas":
            st.markdown('<div class="sec-title">Avance por zona</div>', unsafe_allow_html=True)
            av_zona = kpis.avance_por_zona(df_raw)
            tbl_zona = av_zona[["zona", "zona_nombre", "n_secciones", "meta", "avance", "pct", "semaforo"]].copy()
            tbl_zona.columns = ["Zona", "Nombre", "Secciones", "Meta", "Avance", "% Avance", "Semáforo"]
            st.dataframe(
                tbl_zona.style
                .map(color_pct, subset=["% Avance"])
                .map(color_semaforo, subset=["Semáforo"])
                .format({"% Avance": "{:.1f}%"})
                .set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
                use_container_width=True, hide_index=True,
            )

        # ── Secciones cubiertas ─────────────────────────────────────────────────
        st.markdown('<div class="sec-title">Secciones — meta vs avance</div>', unsafe_allow_html=True)
        av_sec = kpis.avance_por_seccion(df_kpi)
        if zona_sel != 0:
            av_sec = av_sec[av_sec["zona"] == zona_sel]
        if sec_sel != "Todas":
            av_sec = av_sec[av_sec["seccion"] == sec_sel]

        n_cubiertas = int(av_sec["cubierta"].sum())
        st.caption(f"{n_cubiertas} de {len(av_sec)} secciones alcanzaron su meta.")

        tbl_sec = av_sec[["seccion", "tipo", "zona_nombre", "meta", "avance", "pct", "semaforo"]].copy()
        tbl_sec.columns = ["Sección", "Tipo", "Zona", "Meta", "Avance", "% Avance", "Semáforo"]
        st.dataframe(
            tbl_sec.style
            .map(color_pct,      subset=["% Avance"])
            .map(color_semaforo, subset=["Semáforo"])
            .format({"% Avance": "{:.1f}%"})
            .set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
            use_container_width=True, hide_index=True,
            height=min(80 + len(tbl_sec) * 35, 560),
        )
        st.caption("🟢 ≥100% de meta · 🟡 60–99% · 🔴 <60%")

        # ── Avance por encuestador ──────────────────────────────────────────────
        st.markdown('<div class="sec-title">Avance por encuestador</div>', unsafe_allow_html=True)
        av_enc = kpis.avance_por_encuestador(df_kpi)
        tbl_enc = av_enc[["encuestador_nombre", "zona", "levantadas", "terminadas",
                           "duracion_prom_min", "secciones_trabajadas"]].copy()
        tbl_enc["zona"] = tbl_enc["zona"].apply(
            lambda zl: ", ".join(str(z) for z in zl) if isinstance(zl, list) else str(zl)
        )
        tbl_enc.columns = ["Encuestador", "Zona(s)", "Levantadas", "Terminadas",
                            "Dur. prom (min)", "Secciones"]
        st.dataframe(
            tbl_enc.style
            .map(color_dur, subset=["Dur. prom (min)"])
            .format({"Dur. prom (min)": "{:.1f}"})
            .set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
            use_container_width=True, hide_index=True,
            height=min(80 + len(tbl_enc) * 35, 420),
        )

        with st.expander("📊 Distribución de duraciones (registros confiables)", expanded=False):
            fig_box = px.box(
                df_conf, y="duracion_min", color_discrete_sequence=[VERDE],
                labels={"duracion_min": "Minutos"}, title="Duración de entrevistas",
            )
            fig_box.add_hline(y=DUR_MAX_MIN, line_dash="dash",  line_color=AMARILLO,
                              annotation_text=f"Máx ({DUR_MAX_MIN} min)")
            fig_box.add_hline(y=DUR_MIN_MIN, line_dash="dot",   line_color=ROJO,
                              annotation_text=f"Mín ({DUR_MIN_MIN} min)")
            fig_box.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                  font_family="IBM Plex Sans", margin=dict(t=50, b=10))
            st.plotly_chart(fig_box, use_container_width=True)

        # ── Cuotas H/M ─────────────────────────────────────────────────────────
        st.markdown('<div class="sec-title">Cobertura de cuotas (H / M)</div>', unsafe_allow_html=True)
        cq = kpis.avance_cuotas(df_kpi, sec_sel) if sec_sel != "Todas" \
            else kpis.avance_cuotas_global(df_kpi)
        cq_disp = cq.copy()
        cq_disp.columns = [c.replace("_", " ").title() for c in cq_disp.columns]
        st.dataframe(
            cq_disp.style
            .map(color_pct,      subset=["Pct"])
            .map(color_semaforo, subset=["Semaforo"])
            .format({"Pct": "{:.1f}%"})
            .set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
            use_container_width=True, hide_index=True,
        )
        st.caption("Cuota de género (H/M) respecto a la meta definida en el subconjunto de muestra.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MAPA DE COBERTURA
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec-title">Mapa de cobertura por sección electoral</div>',
                unsafe_allow_html=True)

    if GEOJSON is None:
        st.warning(f"No se encontró {GEOJSON_SECCIONES}. Colócalo junto a app.py.")
    elif df_raw.empty:
        st.info("Sin datos disponibles todavía.")
    else:
        # Para el mapa: respeta zona y fecha pero NO el filtro de sección
        df_mapa = df_raw.copy()
        if zona_sel != 0:
            df_mapa = df_mapa[df_mapa["zona"] == zona_sel]
        if fecha_sel and "fecha" in df_mapa.columns:
            df_mapa = df_mapa[df_mapa["fecha"].isin(fecha_sel)]

        av_sec_all = kpis.avance_por_seccion(df_mapa)
        av_lookup  = av_sec_all.set_index("seccion").to_dict(orient="index")

        secciones_mapa = sorted(av_sec_all["seccion"].tolist())
        zoom_sel = st.selectbox(
            "🔍 Resaltar / hacer zoom a sección", ["Todas"] + secciones_mapa,
            format_func=lambda s: "Todas" if s == "Todas"
            else f"{s} — Z{METAS_POR_SECCION.get(s,{}).get('zona','')} — "
                 f"{METAS_POR_SECCION.get(s,{}).get('tipo','')}",
            key="zoom_seccion_mapa",
        )

        geojson_enriq = copy.deepcopy(GEOJSON)
        bounds_zoom = None
        for feature in geojson_enriq["features"]:
            sec  = feature["properties"].get("seccion")
            info = av_lookup.get(sec)
            z_id = METAS_POR_SECCION.get(sec, {}).get("zona")
            if info is None:
                feature["properties"].update({
                    "meta": 0, "avance": 0, "pct": 0.0,
                    "zona_nombre": "Fuera de muestra", "tipo": "—",
                    "estado": "Fuera de muestra",
                })
            else:
                feature["properties"].update({
                    "meta":       int(info["meta"]),
                    "avance":     int(info["avance"]),
                    "pct":        float(info["pct"]),
                    "zona_nombre": ZONA_NOMBRES.get(z_id, "—"),
                    "tipo":       info["tipo"],
                    "estado":     "🟢 En meta" if info["pct"] >= 100 else
                                  ("🟡 En riesgo" if info["pct"] >= 60 else "🔴 Bajo meta"),
                })
            if zoom_sel != "Todas" and sec == zoom_sel:
                bounds_zoom = _bounds_from_geometry(feature["geometry"])

        def style_sec(feature):
            props = feature["properties"]
            resaltada = zoom_sel != "Todas" and props.get("seccion") == zoom_sel
            if props.get("estado") == "Fuera de muestra":
                base = {"fillColor": "#CCCCCC", "color": "#999999",
                        "weight": 0.6, "fillOpacity": 0.30}
            else:
                pct = props.get("pct", 0)
                if pct >= 100:
                    base = {"fillColor": VERDE,    "color": "#1A5C42",
                            "weight": 1.4, "fillOpacity": 0.78}
                elif pct >= 60:
                    base = {"fillColor": AMARILLO, "color": "#8a6200",
                            "weight": 1.4, "fillOpacity": 0.78}
                else:
                    base = {"fillColor": ROJO,     "color": "#7b1a14",
                            "weight": 1.4, "fillOpacity": 0.78}
            if resaltada:
                base = {**base, "color": AZUL, "weight": 4}
            elif zoom_sel != "Todas":
                base = {**base, "fillOpacity": base["fillOpacity"] * 0.35}
            return base

        tooltip_html = folium.GeoJsonTooltip(
            fields=["seccion", "zona_nombre", "tipo", "estado", "avance", "meta", "pct"],
            aliases=["Sección:", "Zona:", "Tipo:", "Estado:", "Avance:", "Meta:", "% avance:"],
            localize=True, sticky=True, labels=True,
            style=(
                "background-color:white;border:1px solid #2E7D5E;"
                "border-radius:6px;padding:8px 12px;"
                "font-family:'IBM Plex Sans',sans-serif;font-size:13px;"
                "box-shadow:0 2px 8px rgba(0,0,0,0.15);"
            ),
        )

        mapa = folium.Map(
            location=ATLIXCO_CENTRO, zoom_start=ATLIXCO_ZOOM,
            tiles="CartoDB positron",
        )

        folium.GeoJson(
            geojson_enriq, style_function=style_sec,
            highlight_function=lambda f: {"fillOpacity": 0.95, "weight": 2.5, "color": AZUL},
            tooltip=tooltip_html, name="Secciones electorales",
        ).add_to(mapa)

        # ── Puntos georreferenciados ────────────────────────────────────────────
        df_puntos = df_mapa if zoom_sel == "Todas" \
            else df_mapa[df_mapa["seccion_electoral"] == zoom_sel]
        tiene_coords = df_puntos["latitud"].notna() & df_puntos["longitud"].notna()
        df_geo_ok    = df_puntos[tiene_coords]

        capa_puntos = folium.FeatureGroup(name="Encuestas georreferenciadas", show=True)
        for _, r in df_geo_ok.iterrows():
            nivel  = r.get("flag_georef_nivel")
            color  = "#C0392B" if nivel == "rojo" else \
                     ("#E07B39" if nivel == "amarillo" else "#2E7D5E")
            folium.CircleMarker(
                location=[r["latitud"], r["longitud"]], radius=4,
                color=color, fill=True, fill_opacity=0.85, weight=1,
                tooltip=f"{r.get('encuestador_nombre','—')} · folio {r['folio']}",
                popup=(f"<b>{r.get('encuestador_nombre','—')}</b><br>"
                       f"Folio {r['folio']}<br>"
                       f"Sección declarada: {r['seccion_electoral']}<br>"
                       f"Sección por coords: {r.get('seccion_georef')}"),
            ).add_to(capa_puntos)
        capa_puntos.add_to(mapa)
        folium.LayerControl().add_to(mapa)

        if bounds_zoom:
            mapa.fit_bounds(bounds_zoom)

        st_folium(mapa, width="100%", height=560,
                  returned_objects=[], key="mapa_cobertura")

        st.caption(
            "🟢 ≥100% · 🟡 60–99% · 🔴 <60% · ⬜ Fuera de muestra. "
            "Puntos: 🟢 coincide con sección declarada · "
            "🟠 cae en otra sección de Atlixco · 🔴 fuera de Atlixco."
        )

        # ── Encuestadores con puntos fuera de zona ─────────────────────────────
        df_fuera = df_geo_ok[df_geo_ok["flag_georef_nivel"].isin(["amarillo", "rojo"])]
        if not df_fuera.empty:
            st.markdown('<div class="sec-title">Encuestadores con puntos fuera de zona</div>',
                        unsafe_allow_html=True)
            resumen_enc = (
                df_fuera.groupby("encuestador_nombre")
                .agg(
                    rojo=("flag_georef_nivel",    lambda s: (s == "rojo").sum()),
                    amarillo=("flag_georef_nivel", lambda s: (s == "amarillo").sum()),
                    folios=("folio",              lambda s: ", ".join(map(str, s))),
                )
                .reset_index()
                .sort_values(["rojo", "amarillo"], ascending=False)
            )
            resumen_enc.columns = ["Encuestador", "🔴 Fuera de Atlixco",
                                    "🟠 Otra sección", "Folios"]
            st.dataframe(resumen_enc, use_container_width=True, hide_index=True,
                         height=min(80 + len(resumen_enc) * 35, 320))

        # ── Diagnóstico de coordenadas ──────────────────────────────────────────
        st.markdown('<div class="sec-title">Diagnóstico de georreferenciación</div>',
                    unsafe_allow_html=True)
        n_total      = len(df_puntos)
        n_con        = int(tiene_coords.sum())
        n_sin        = n_total - n_con
        n_rojo_geo   = int((df_geo_ok.get("flag_georef_nivel") == "rojo").sum())   if n_con else 0
        n_am_geo     = int((df_geo_ok.get("flag_georef_nivel") == "amarillo").sum()) if n_con else 0

        dc1, dc2, dc3, dc4 = st.columns(4)
        kpi(dc1, f"{n_con:,}", "Con coordenadas",
            f"{round(100*n_con/max(n_total,1),1)}% de {n_total:,}")
        kpi(dc2, f"{n_sin:,}", "Sin coordenadas",
            f"{round(100*n_sin/max(n_total,1),1)}%", "amarillo" if n_sin else "")
        kpi(dc3, f"{n_am_geo:,}", "Otra sección de Atlixco",
            "flag amarillo", "amarillo" if n_am_geo else "")
        kpi(dc4, f"{n_rojo_geo:,}", "Fuera de Atlixco",
            "flag rojo", "rojo" if n_rojo_geo else "")

        # ── Secciones sin avance ────────────────────────────────────────────────
        sin_avance = av_sec_all[av_sec_all["avance"] == 0]
        if not sin_avance.empty:
            st.markdown('<div class="sec-title">Secciones sin encuestas registradas</div>',
                        unsafe_allow_html=True)
            st.write(", ".join(
                f"**{int(r['seccion'])}** (Z{r['zona']}, {r['tipo']})"
                for _, r in sin_avance.iterrows()
            ))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FLAGS DE CALIDAD Y SESGO
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if df.empty:
        st.info("Sin registros para los filtros seleccionados.")
    else:
        st.markdown('<div class="sec-title">Resumen de flags</div>', unsafe_allow_html=True)

        flag_cols_nivel = [c for c in df.columns
                           if c.startswith("flag_") and c.endswith("_nivel")]

        resumen_flags = []
        for col in flag_cols_nivel:
            nombre = col.replace("flag_", "").replace("_nivel", "")\
                        .replace("_", " ").title()
            n_rojo     = int((df[col] == "rojo").sum())
            n_amarillo = int((df[col] == "amarillo").sum())
            n_total    = len(df)
            resumen_flags.append({
                "flag":         nombre,
                "rojo":         n_rojo,
                "amarillo":     n_amarillo,
                "sin_flag":     max(n_total - n_rojo - n_amarillo, 0),
                "pct_afectado": round(100 * (n_rojo + n_amarillo) / n_total, 1) if n_total else 0,
            })

        rf = pd.DataFrame(resumen_flags)

        n_con_flag = int((df["flags_rojo_n"] + df["flags_amarillo_n"] > 0).sum())
        n_rojo_tot = int((df["flags_rojo_n"] > 0).sum())

        kc1, kc2, kc3 = st.columns(3)
        kpi(kc1, f"{n_con_flag:,}", "Registros con ≥1 flag",
            f"{round(100*n_con_flag/max(len(df),1),1)}% del total en vista",
            "amarillo" if n_con_flag else "")
        kpi(kc2, f"{n_rojo_tot:,}", "Con flag rojo",
            f"{round(100*n_rojo_tot/max(len(df),1),1)}% del total en vista",
            "rojo" if n_rojo_tot else "")
        kpi(kc3, f"{len(df):,}", "Total registros en vista", "")

        st.markdown("<br>", unsafe_allow_html=True)

        # Barra apilada por tipo de flag
        rf_plot = rf.sort_values("pct_afectado", ascending=True)
        fig_flags = px.bar(
            rf_plot, y="flag", x=["rojo", "amarillo", "sin_flag"], orientation="h",
            color_discrete_map={"rojo": ROJO, "amarillo": AMARILLO, "sin_flag": "#E3E7EC"},
            labels={"value": "Registros", "flag": "", "variable": ""},
            title="Registros marcados por tipo de flag",
            height=max(220, 70 * len(rf_plot)),
        )
        fig_flags.update_layout(
            barmode="stack", plot_bgcolor="white", paper_bgcolor="white",
            font_family="IBM Plex Sans", margin=dict(t=45, b=10, l=10),
            legend_title_text="",
            legend=dict(orientation="h", y=-0.15),
        )
        fig_flags.for_each_trace(lambda t: t.update(
            name={"rojo": "Rojo", "amarillo": "Amarillo", "sin_flag": "Sin flag"}.get(t.name, t.name)
        ))
        st.plotly_chart(fig_flags, use_container_width=True)

        with st.expander("Ver tabla de conteos por flag"):
            tbl_rf = rf[["flag", "rojo", "amarillo", "pct_afectado"]].copy()
            tbl_rf.columns = ["Flag", "🔴 Rojo", "🟡 Amarillo", "% afectado"]
            st.dataframe(
                tbl_rf.style.format({"% afectado": "{:.1f}%"})
                .set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
                use_container_width=True, hide_index=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Tabla de registros con flags ────────────────────────────────────────
        st.markdown('<div class="sec-title">Registros con flags activos</div>',
                    unsafe_allow_html=True)

        tipo_flag_opts = ["Todos"] + [
            c.replace("flag_", "").replace("_nivel", "").replace("_", " ").title()
            for c in flag_cols_nivel
        ]
        fc1, fc2 = st.columns(2)
        with fc1:
            tipo_flag_sel = st.selectbox("Tipo de flag", tipo_flag_opts)
        with fc2:
            nivel_sel = st.selectbox("Nivel", ["Todos", "rojo", "amarillo"])

        df_flags = df[df["flags_rojo_n"] + df["flags_amarillo_n"] > 0].copy()

        if tipo_flag_sel != "Todos":
            col_target = "flag_" + tipo_flag_sel.lower().replace(" ", "_") + "_nivel"
            df_flags   = df_flags[df_flags[col_target].notna()]
            if nivel_sel != "Todos":
                df_flags = df_flags[df_flags[col_target] == nivel_sel]
        elif nivel_sel != "Todos":
            mask = pd.Series(False, index=df_flags.index)
            for col in flag_cols_nivel:
                mask |= (df_flags[col] == nivel_sel)
            df_flags = df_flags[mask]

        cols_mostrar = [
            "folio", "seccion_electoral", "zona_nombre", "encuestador_nombre",
            "duracion_min", "flags_rojo_n", "flags_amarillo_n",
        ] + flag_cols_nivel
        cols_mostrar = [c for c in cols_mostrar if c in df_flags.columns]

        st.dataframe(
            df_flags[cols_mostrar].sort_values(
                ["flags_rojo_n", "flags_amarillo_n"], ascending=False
            ),
            use_container_width=True, hide_index=True,
            height=min(80 + len(df_flags) * 35, 480),
        )
        st.caption(f"{len(df_flags):,} de {len(df):,} registros tienen al menos un flag activo.")

        # ── Cobertura geográfica desbalanceada ──────────────────────────────────
        st.markdown('<div class="sec-title">Cobertura geográfica desbalanceada (por sección)</div>',
                    unsafe_allow_html=True)
        cob      = flags.resumen_cobertura_desbalanceada(df_raw)
        cob_flag = cob[cob["flag_cobertura"]]
        if cob_flag.empty:
            st.success("Sin secciones con cobertura desbalanceada detectada.")
        else:
            tbl_cob = cob_flag[[
                "seccion", "tipo", "zona_nombre", "meta", "avance",
                "pct", "flag_cobertura_nivel"
            ]].copy()
            tbl_cob.columns = ["Sección", "Tipo", "Zona", "Meta",
                                "Avance", "% Avance", "Nivel"]
            st.dataframe(
                tbl_cob.style
                .map(color_semaforo, subset=["Nivel"])
                .format({"% Avance": "{:.1f}%"})
                .set_properties(**{"font-family": "IBM Plex Sans", "font-size": "13px"}),
                use_container_width=True, hide_index=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RESULTADOS DEL INSTRUMENTO (solo rol estatal)
# ══════════════════════════════════════════════════════════════════════════════
if tab4 is not None:
    with tab4:
        if df.empty:
            st.info("Sin registros para los filtros seleccionados.")
        else:
            # ── Perfil sociodemográfico ─────────────────────────────────────────
            st.markdown('<div class="sec-title">Perfil sociodemográfico</div>',
                        unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                show_chart(pct_bar(df, "sexo", "Sexo"))
            with c2:
                show_chart(pct_bar(df, "rango_edad", "Rango de edad",
                                    orden=["18-29", "30-44", "45-59", "60+"]))
            with c3:
                show_chart(pct_bar(df, "ine", "¿Cuenta con INE?",
                                    orden=["Sí", "No"], colors=[VERDE, "#ccc"]))

            # Bloque 12: Variables sociodemográficas adicionales (nuevo en Atlixco)
            st.markdown('<div class="sec-title">Bloque 12 — Perfil socioeconómico</div>',
                        unsafe_allow_html=True)
            d1, d2, d3 = st.columns(3)
            with d1:
                show_chart(pct_bar(df, "ocupacion", "D1. Ocupación"))
            with d2:
                show_chart(pct_bar(df, "estado_civil", "D2. Estado civil"))
            with d3:
                show_chart(pct_bar(df, "nivel_escolaridad", "D3. Nivel de escolaridad"))

            st.markdown("---")

            # ── Bloque 4 — Principal problema del estado (ampliado) ─────────────
            st.markdown('<div class="sec-title">Bloque 4 — Contexto y problemas del estado</div>',
                        unsafe_allow_html=True)
            b4c1, b4c2, b4c3 = st.columns(3)
            with b4c1:
                show_chart(pct_bar(df, "direccion_estado",
                                    "P1. ¿El estado va por buen camino?", height=220))
            with b4c2:
                show_chart(pct_bar(df, "principal_problema_estado_opciones",
                                    "P2.1 Principal problema del estado", height=220))
            with b4c3:
                show_chart(pct_bar(df, "servicios_publicos_opciones",
                                    "P3. Servicios públicos prioritarios", height=220))

            st.markdown("---")

            # ── Bloque 5 — Identificación partidista e intención de voto ────────
            st.markdown('<div class="sec-title">Bloque 5 — Afinidad e intención de voto</div>',
                        unsafe_allow_html=True)
            b5c1, b5c2 = st.columns(2)
            with b5c1:
                show_chart(pct_bar(df, "identificacion_partidaria",
                                    "P4. Identificación partidista"))
            with b5c2:
                show_chart(pct_bar(df, "intencion_voto_principal",
                                    "P5. Intención de voto principal"))

            st.markdown("---")

            # ── Bloques 6 y 7 — Aspirantes ──────────────────────────────────────
            st.markdown('<div class="sec-title">Bloques 6 y 7 — Conocimiento, opinión y atributos</div>',
                        unsafe_allow_html=True)

            # Comparativo de conocimiento entre aspirantes
            conoce_rows = []
            for cand, nombre in CANDIDATOS.items():
                col_conoce = f"conocimiento_{cand}"
                if col_conoce in df.columns:
                    sub = df[col_conoce].dropna()
                    if len(sub):
                        pct_conoce = round(
                            sub.astype(str).str.lower()
                            .str.contains("sí|si", regex=True).mean() * 100, 1
                        )
                        conoce_rows.append({"Aspirante": nombre, "% Lo conoce": pct_conoce})

            cc1, cc2 = st.columns(2)
            with cc1:
                if conoce_rows:
                    df_conoce = pd.DataFrame(conoce_rows).sort_values("% Lo conoce", ascending=True)
                    fig_c = px.bar(
                        df_conoce, x="% Lo conoce", y="Aspirante", orientation="h",
                        text=df_conoce["% Lo conoce"].apply(lambda v: f"{v}%"),
                        color_discrete_sequence=[VERDE_L],
                        title="Bloque 6 — % que conoce a cada aspirante", height=300,
                    )
                    fig_c.update_traces(textposition="outside")
                    fig_c.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white",
                        showlegend=False, font_family="IBM Plex Sans",
                        margin=dict(t=45, b=5, l=160), xaxis_range=[0, 105],
                    )
                    st.plotly_chart(fig_c, use_container_width=True)
                else:
                    st.info("Sin datos de conocimiento de aspirantes.")

            with cc2:
                cand_sel = st.selectbox(
                    "Seleccionar aspirante — detalle Bloque 6 / 7",
                    list(CANDIDATOS.items()),
                    format_func=lambda kv: kv[1],
                    key="cand_sel",
                )
                cand_key, cand_nombre = cand_sel
                show_chart(pct_bar(df, f"opinion_{cand_key}",
                                    f"P9. Opinión sobre {cand_nombre}"))

            st.markdown(f"**Bloque 7 — Evaluación de atributos: {cand_nombre}**")
            atrib_cols = st.columns(4)
            for i, atrib in enumerate(ATRIBUTOS_BLOQUE7):
                campo = f"{atrib}_{cand_key}"
                with atrib_cols[i % 4]:
                    show_chart(pct_bar(df, campo,
                                        atrib.replace("_", " ").title(), height=200))

            st.markdown("---")

            # ── Bloque 8 — Preferencia MORENA ────────────────────────────────────
            st.markdown('<div class="sec-title">Bloque 8 — Preferencia de candidato(a) MORENA</div>',
                        unsafe_allow_html=True)
            show_chart(pct_bar(df, "preferencia_total_morena",
                                "P19. Preferencia total MORENA", height=280))

            st.markdown("---")

            # ── Bloque 10 — Evaluación de autoridades ────────────────────────────
            st.markdown('<div class="sec-title">Bloque 10 — Evaluación de autoridades</div>',
                        unsafe_allow_html=True)
            cc5, cc6, cc7 = st.columns(3)
            with cc5:
                show_chart(pct_bar(df, "aprobacion_atlixco",
                                    "P22.1 Aprobación — Ariadna Ayala Camarillo"))
            with cc6:
                show_chart(pct_bar(df, "aprobacion_gobernador",
                                    "P22.2 Aprobación — Alejandro Armenta Mier"))
            with cc7:
                show_chart(pct_bar(df, "aprobacion_presidenta",
                                    "P22.3 Aprobación — Claudia Sheinbaum Pardo"))