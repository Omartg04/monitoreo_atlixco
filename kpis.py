"""
CEOP · kpis.py — Atlixco
Cálculo de KPIs de avance: meta global, meta por sección, por zona y por encuestador.
Cobertura de cuotas H/M (sin desglose por edad en este operativo).

Diferencias vs Zacatlán:
  - Nueva capa de agregación: ZONA (6 zonas geográficas)
  - Cuotas solo H/M — no hay grid de edad × sexo como en Zacatlán
  - SECCIONES_POR_EQUIPO reemplazado por SECCIONES_POR_ZONA

Columnas mínimas requeridas en `df` (salida de transform_atlixco):
    folio, seccion_electoral, zona, zona_nombre, encuestador_id,
    encuestador_nombre, terminada, edad, sexo, duracion_min
"""
from __future__ import annotations

import pandas as pd

from config import (
    META_GLOBAL, META_POR_ZONA, METAS_POR_SECCION,
    SECCIONES_POR_ZONA, SECCIONES_FUERA_MUESTRA,
    ZONA_NOMBRES,
)


# ── Helpers demográficos ───────────────────────────────────────────────────────

def bin_sexo_cuota(sexo: str | None) -> str | None:
    """Normaliza valor de sexo a 'H'/'M' para cruzar contra cuotas."""
    if not sexo:
        return None
    s = str(sexo).strip().upper()
    if s in ("H", "HOMBRE", "MASCULINO"):
        return "H"
    if s in ("M", "MUJER", "FEMENINO"):
        return "M"
    return None


# ── KPI 1: Meta global vs avance ──────────────────────────────────────────────

def resumen_global(df: pd.DataFrame) -> dict:
    """
    Meta global = 840 (suma de cuotas de 42 secciones).
    Avance = encuestas terminadas en el universo de muestra.
    """
    df_universo = df[~df["seccion_electoral"].isin(SECCIONES_FUERA_MUESTRA)]
    terminadas  = int(df_universo["terminada"].sum())
    levantadas  = len(df_universo)

    return {
        "meta_global":  META_GLOBAL,
        "levantadas":   levantadas,
        "terminadas":   terminadas,
        "avance_pct":   round(100 * terminadas / META_GLOBAL, 1) if META_GLOBAL else 0.0,
        "faltan":       max(META_GLOBAL - terminadas, 0),
    }


# ── KPI 2: Avance por sección ──────────────────────────────────────────────────

def avance_por_seccion(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sección con meta, avance, % y semáforo. Incluye secciones con avance=0."""
    terminadas = (
        df[df["terminada"]]
        .groupby("seccion_electoral")
        .size()
        .rename("avance")
    )

    filas = []
    for seccion, meta_info in METAS_POR_SECCION.items():
        avance = int(terminadas.get(seccion, 0))
        meta   = meta_info["meta_encuestas"]
        pct    = round(100 * avance / meta, 1) if meta else 0.0
        filas.append({
            "seccion":     seccion,
            "tipo":        meta_info["tipo"],
            "zona":        meta_info["zona"],
            "zona_nombre": ZONA_NOMBRES[meta_info["zona"]],
            "meta":        meta,
            "avance":      avance,
            "pct":         pct,
            "cubierta":    avance >= meta,
            "semaforo":    _semaforo(pct),
        })

    return pd.DataFrame(filas).sort_values(["zona", "seccion"]).reset_index(drop=True)


# ── KPI 3: Avance por zona ─────────────────────────────────────────────────────

def avance_por_zona(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega meta y avance por zona (nueva capa vs Zacatlán).
    Equivalente a avance_por_equipo en Zacatlán.
    """
    av_sec = avance_por_seccion(df).set_index("seccion")

    filas = []
    for zona_id, secciones in SECCIONES_POR_ZONA.items():
        meta_total   = sum(METAS_POR_SECCION[s]["meta_encuestas"] for s in secciones)
        avance_total = int(av_sec.loc[secciones, "avance"].sum())
        pct = round(100 * avance_total / meta_total, 1) if meta_total else 0.0
        filas.append({
            "zona":        zona_id,
            "zona_nombre": ZONA_NOMBRES[zona_id],
            "n_secciones": len(secciones),
            "secciones":   secciones,
            "meta":        meta_total,
            "avance":      avance_total,
            "pct":         pct,
            "semaforo":    _semaforo(pct),
        })

    return pd.DataFrame(filas).sort_values("zona").reset_index(drop=True)


# ── KPI 4: Avance por encuestador ─────────────────────────────────────────────

def avance_por_encuestador(df: pd.DataFrame, seccion: int | None = None) -> pd.DataFrame:
    """
    Avance por encuestador (folios levantados, terminados, duración promedio).
    Si `seccion` se especifica, filtra primero a esa sección.
    """
    d = df if seccion is None else df[df["seccion_electoral"] == seccion]

    g = d.groupby(["encuestador_id", "encuestador_nombre"], dropna=False)
    out = g.agg(
        levantadas=("folio", "count"),
        terminadas=("terminada", "sum"),
        duracion_prom_min=("duracion_min", "mean"),
        secciones_trabajadas=("seccion_electoral", "nunique"),
        zona=("zona_nombre", lambda s: sorted(s.dropna().unique().tolist())),
    ).reset_index()

    out["duracion_prom_min"] = out["duracion_prom_min"].round(1)
    out["terminadas"] = out["terminadas"].astype(int)
    return out.sort_values("levantadas", ascending=False).reset_index(drop=True)


# ── KPI 5: Cobertura de cuotas H/M por sección ────────────────────────────────

def avance_cuotas(df: pd.DataFrame, seccion: int) -> pd.DataFrame:
    """
    Para una sección dada: meta H/M vs avance H/M entre encuestas terminadas.
    Retorna 2 filas (H y M).
    """
    meta_info = METAS_POR_SECCION[seccion]
    d = df[(df["seccion_electoral"] == seccion) & df["terminada"]].copy()
    d["_sexo_q"] = d["sexo"].apply(bin_sexo_cuota)
    conteo = d["_sexo_q"].value_counts()

    filas = []
    for sexo, meta in meta_info["cuotas"].items():
        avance = int(conteo.get(sexo, 0))
        pct    = round(100 * avance / meta, 1) if meta else 0.0
        filas.append({
            "seccion":  seccion,
            "sexo":     sexo,
            "meta":     meta,
            "avance":   avance,
            "pct":      pct,
            "semaforo": _semaforo(pct),
        })
    return pd.DataFrame(filas)


def avance_cuotas_global(df: pd.DataFrame) -> pd.DataFrame:
    """
    Suma de cuotas H/M de TODAS las secciones en muestra.
    Útil para detectar sesgo de género agregado.
    """
    d = df[df["terminada"]].copy()
    d["_sexo_q"] = d["sexo"].apply(bin_sexo_cuota)
    conteo = d["_sexo_q"].value_counts()

    meta_h = sum(v["cuotas"]["H"] for v in METAS_POR_SECCION.values())
    meta_m = sum(v["cuotas"]["M"] for v in METAS_POR_SECCION.values())

    filas = []
    for sexo, meta in [("H", meta_h), ("M", meta_m)]:
        avance = int(conteo.get(sexo, 0))
        pct    = round(100 * avance / meta, 1) if meta else 0.0
        filas.append({
            "sexo": sexo, "meta": meta, "avance": avance,
            "pct": pct, "semaforo": _semaforo(pct),
        })
    return pd.DataFrame(filas)


# ── Semáforo ───────────────────────────────────────────────────────────────────

def _semaforo(pct: float) -> str:
    if pct >= 100: return "verde"
    if pct >= 60:  return "amarillo"
    return "rojo"
