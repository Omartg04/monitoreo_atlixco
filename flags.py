"""
CEOP · flags.py — Atlixco
Sistema de flags de calidad y sesgo. Prácticamente idéntico a Zacatlán;
diferencias clave:
  - CANDIDATOS usa claves `aspirante1`..`aspirante5`
  - Cobertura desbalanceada agrega por ZONA en lugar de equipo
  - GEOJSON_SECCIONES apunta a secciones_atlixco.geojson

Reglas implementadas:
  1. flag_duracion              — tiempos de entrevista anómalos
  2. flag_straightlining        — patrones de respuesta sospechosos
  3. flag_georef_fuera_zona     — georreferenciación fuera de Atlixco
  4. flag_horario_atipico       — horarios atípicos
  5. flag_inconsistencia_conocimiento — Bloque 6 vs Bloque 7 por aspirante
  6. resumen_cobertura_desbalanceada  — cobertura por sección/zona
"""
from __future__ import annotations

import json
import re

import pandas as pd
from shapely.geometry import Point, shape

from config import (
    DUR_MIN_MIN, DUR_MAX_MIN,
    UMBRAL_STRAIGHTLINING_BLOQUE7, UMBRAL_STRAIGHTLINING_BLOQUE6,
    BATERIAS_STRAIGHTLINING, GEOJSON_SECCIONES, CLAVE_MUNICIPIO,
    HORA_INICIO_OPERATIVO, HORA_FIN_OPERATIVO,
    CANDIDATOS, ATRIBUTOS_BLOQUE7,
)
import kpis


# ── 1. Duración de entrevista ─────────────────────────────────────────────────

def flag_duracion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evalúa duración SOLO en encuestas terminadas.
    Rojo: < DUR_MIN_MIN o > DUR_MAX_MIN.
    Amarillo: entre DUR_MIN_MIN y DUR_MIN_MIN × 1.2.
    """
    d = df.copy()
    dur       = d["duracion_min"]
    confiable = d.get("duracion_confiable", pd.Series(True, index=d.index))
    terminada = d.get("terminada", pd.Series(False, index=d.index))
    evaluable = terminada & confiable

    muy_corta = dur < DUR_MIN_MIN
    muy_larga  = dur > DUR_MAX_MIN
    cerca_min  = dur.between(DUR_MIN_MIN, DUR_MIN_MIN * 1.2)
    rojo       = muy_corta | muy_larga
    amarillo   = cerca_min & ~rojo

    d["flag_duracion"] = evaluable & (rojo | amarillo)
    d["flag_duracion_nivel"] = None
    d.loc[evaluable & amarillo, "flag_duracion_nivel"] = "amarillo"
    d.loc[evaluable & rojo,     "flag_duracion_nivel"] = "rojo"
    return d


# ── 2. Straightlining ─────────────────────────────────────────────────────────

def _es_straightline(row: pd.Series, columnas: list[str]) -> bool:
    valores = row[columnas].dropna()
    if len(valores) < len(columnas):
        return False
    return valores.nunique() == 1


def flag_straightlining(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rojo: todas las respuestas de una batería bloque7_* son idénticas.
    Amarillo: ídem para una batería bloque6_*.
    Solo encuestas terminadas.
    """
    d = df.copy()
    terminada = d.get("terminada", pd.Series(False, index=d.index))

    detalle = pd.DataFrame(index=d.index)
    for nombre, columnas in BATERIAS_STRAIGHTLINING.items():
        cols_ok = [c for c in columnas if c in d.columns]
        if len(cols_ok) != len(columnas):
            continue
        detalle[nombre] = d.apply(_es_straightline, axis=1, columnas=columnas)

    cols_b7 = [c for c in detalle.columns if c.startswith("bloque7_")]
    cols_b6 = [c for c in detalle.columns if c.startswith("bloque6_")]
    n_b7 = detalle[cols_b7].sum(axis=1) if cols_b7 else pd.Series(0, index=d.index)
    n_b6 = detalle[cols_b6].sum(axis=1) if cols_b6 else pd.Series(0, index=d.index)

    d["flag_straightlining_detalle"] = (
        detalle.apply(lambda r: [c for c in detalle.columns if r[c]], axis=1)
        if not detalle.empty else [[] for _ in range(len(d))]
    )
    d["flag_straightlining_n_baterias"] = n_b7 + n_b6

    rojo     = terminada & (n_b7 >= 1)
    amarillo = terminada & (~rojo) & (n_b6 >= 1)

    d["flag_straightlining"] = rojo | amarillo
    d["flag_straightlining_nivel"] = None
    d.loc[amarillo, "flag_straightlining_nivel"] = "amarillo"
    d.loc[rojo,     "flag_straightlining_nivel"] = "rojo"
    return d


# ── 3. Georreferenciación fuera de zona ────────────────────────────────────────

_POLIGONOS_CACHE: dict[int, object] | None = None


def _cargar_poligonos(path: str = GEOJSON_SECCIONES) -> dict[int, object]:
    global _POLIGONOS_CACHE
    if _POLIGONOS_CACHE is not None:
        return _POLIGONOS_CACHE
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    poligonos: dict[int, object] = {}
    for feat in gj["features"]:
        seccion = feat["properties"]["seccion"]
        poligonos[seccion] = shape(feat["geometry"])
    _POLIGONOS_CACHE = poligonos
    return poligonos


def _ubicar_punto(lat, lon, poligonos: dict[int, object]) -> int | None:
    if pd.isna(lat) or pd.isna(lon):
        return None
    pt = Point(lon, lat)
    for seccion, geom in poligonos.items():
        if geom.contains(pt):
            return seccion
    return None


def flag_georef_fuera_zona(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compara sección declarada vs sección georeferenciada (coordenadas).
    Amarillo: punto en otra sección de Atlixco.
    Rojo: punto fuera de Atlixco.
    """
    d = df.copy()
    poligonos = _cargar_poligonos()

    d["seccion_georef"] = d.apply(
        lambda r: _ubicar_punto(r.get("latitud"), r.get("longitud"), poligonos), axis=1
    )

    tiene_coords    = d["latitud"].notna() & d["longitud"].notna()
    fuera_municipio = tiene_coords & d["seccion_georef"].isna()
    otra_seccion    = (
        tiene_coords
        & d["seccion_georef"].notna()
        & (d["seccion_georef"] != d["seccion_electoral"])
    )

    d["flag_georef"] = fuera_municipio | otra_seccion
    d["flag_georef_nivel"] = None
    d.loc[otra_seccion,    "flag_georef_nivel"] = "amarillo"
    d.loc[fuera_municipio, "flag_georef_nivel"] = "rojo"
    return d


# ── 4. Horario atípico ─────────────────────────────────────────────────────────

def flag_horario_atipico(df: pd.DataFrame) -> pd.DataFrame:
    """Amarillo: entrevista iniciada fuera de horario operativo declarado."""
    d = df.copy()
    fecha_col = pd.to_datetime(d["fecha_creacion"], utc=True, errors="coerce")
    hora_local = fecha_col.dt.tz_convert("America/Mexico_City").dt.hour
    fuera = ~hora_local.between(HORA_INICIO_OPERATIVO, HORA_FIN_OPERATIVO - 1)
    d["flag_horario"] = fuera
    d["flag_horario_nivel"] = None
    d.loc[fuera, "flag_horario_nivel"] = "amarillo"
    return d


# ── 5. Inconsistencia conocimiento / atributos ─────────────────────────────────

# TODO: confirmar patrones contra catálogo real de Bubble para Atlixco.
_PATRON_NO_CONOCE = re.compile(r"no\s*(?:lo|la)?\s*conoc", re.IGNORECASE)
_PATRON_NO_SABE   = re.compile(r"no\s*sabe|no\s*contesta|n\/?d", re.IGNORECASE)


def flag_inconsistencia_conocimiento(df: pd.DataFrame) -> pd.DataFrame:
    """
    Solo encuestas terminadas. Para cada aspirante: si Bloque 6 indica
    "no lo conoce" pero Bloque 7 tiene opiniones sustantivas → inconsistencia.
    Amarillo si ocurre con 1 aspirante, rojo si con 2+.
    """
    d = df.copy()
    terminada = d.get("terminada", pd.Series(False, index=d.index))
    n_incons  = pd.Series(0, index=d.index)
    detalle: list[list[str]] = [[] for _ in range(len(d))]

    for cand in CANDIDATOS:
        col_conoce = f"conocimiento_{cand}"
        if col_conoce not in d.columns:
            continue

        no_conoce = d[col_conoce].astype(str).str.contains(_PATRON_NO_CONOCE, na=False)

        cols_atrib = [
            f"{atrib}_{cand}" for atrib in ATRIBUTOS_BLOQUE7
            if f"{atrib}_{cand}" in d.columns
        ]
        if not cols_atrib:
            continue

        opina = pd.DataFrame({
            c: d[c].notna() & ~d[c].astype(str).str.contains(_PATRON_NO_SABE, na=False)
            for c in cols_atrib
        }).any(axis=1)

        incons_cand = terminada & no_conoce & opina
        n_incons += incons_cand.astype(int)
        for i, flagged in enumerate(incons_cand):
            if flagged:
                detalle[i].append(cand)

    d["flag_inconsistencia_conocimiento_detalle"] = detalle
    d["flag_inconsistencia_conocimiento_n"]        = n_incons
    d["flag_inconsistencia_conocimiento"]          = n_incons > 0
    d["flag_inconsistencia_conocimiento_nivel"]    = None
    d.loc[n_incons == 1, "flag_inconsistencia_conocimiento_nivel"] = "amarillo"
    d.loc[n_incons >= 2, "flag_inconsistencia_conocimiento_nivel"] = "rojo"
    return d


# ── 6. Cobertura geográfica desbalanceada ──────────────────────────────────────

def resumen_cobertura_desbalanceada(df: pd.DataFrame) -> pd.DataFrame:
    """
    Marca secciones con cobertura muy baja relativa al promedio de su zona.
    Rojo:     pct == 0 y hay otra sección en la misma zona con avance > 0.
    Amarillo: pct < 50% del promedio de la zona.
    """
    av = kpis.avance_por_seccion(df)

    prom_zona        = av.groupby("zona")["pct"].transform("mean")
    avance_zona_max  = av.groupby("zona")["avance"].transform("max")

    rojo     = (av["avance"] == 0) & (avance_zona_max > 0)
    amarillo = (~rojo) & (av["pct"] < 0.5 * prom_zona) & (prom_zona > 0)

    av["flag_cobertura"] = rojo | amarillo
    av["flag_cobertura_nivel"] = None
    av.loc[amarillo, "flag_cobertura_nivel"] = "amarillo"
    av.loc[rojo,     "flag_cobertura_nivel"] = "rojo"
    return av


# ── Orquestador ────────────────────────────────────────────────────────────────

def aplicar_todos_los_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todos los flags de nivel-registro en cadena."""
    d = flag_duracion(df)
    d = flag_straightlining(d)
    d = flag_georef_fuera_zona(d)
    d = flag_horario_atipico(d)
    d = flag_inconsistencia_conocimiento(d)

    cols_nivel = [c for c in d.columns if c.endswith("_nivel") and c.startswith("flag_")]
    d["flags_rojo_n"]     = (d[cols_nivel] == "rojo").sum(axis=1)
    d["flags_amarillo_n"] = (d[cols_nivel] == "amarillo").sum(axis=1)
    return d
