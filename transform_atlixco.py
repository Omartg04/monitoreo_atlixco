"""
CEOP · transform_atlixco.py — Atlixco
Capa de transformación específica para Atlixco.

Diferencia clave vs Zacatlán:
  - No existe campo `estatus` en el cuestionario de Atlixco (confirmado en
    diccionario y registro real de Bubble 2026-06-25).
  - `terminada` se deriva de que el registro exista Y tenga fecha_fin válida
    (Modified Date > Created Date en más de 1 minuto), lo que indica que el
    formulario fue completado y no solo iniciado.
  - municipio_texto confirmado: "ATLIXCO" (mayúsculas, sin acento).
"""
from __future__ import annotations

import pandas as pd

from bubble_connector import get_encuestas as _get_raw
from config import (
    METAS_POR_SECCION, SECCIONES_FUERA_MUESTRA,
    ZONA_NOMBRES, INICIO_OPERATIVO,
)

_INICIO = pd.Timestamp(INICIO_OPERATIVO).date()
_MUNICIPIO_BUBBLE = "ATLIXCO"   # confirmado en registro real Bubble 2026-06-25


def get_encuestas(
    api_key: str,
    secciones: list[int] | None = None,
    force_refresh: bool = False,
) -> tuple[pd.DataFrame, object]:
    """
    Descarga y transforma datos de Bubble para Atlixco.
    Retorna (df, ultima_actualizacion).
    """
    df, ultima_act = _get_raw(
        api_key=api_key,
        municipios=[_MUNICIPIO_BUBBLE],
        force_refresh=force_refresh,
    )

    # Columnas defensivas para estado pre-conexión
    if df.empty:
        for col, dtype in [
            ("folio", "str"), ("zona", "Int64"), ("zona_nombre", "str"), ("equipo", "str"),
            ("terminada", "bool"), ("seccion_electoral", "Int64"),
        ]:
            if col not in df.columns:
                df[col] = pd.Series(dtype=dtype)
        return df, ultima_act

    # ── folio ─────────────────────────────────────────────────────────────────
    if "id_unico" in df.columns and "folio" not in df.columns:
        df = df.rename(columns={"id_unico": "folio"})
    elif "folio" not in df.columns:
        df["folio"] = df.index.astype(str)

    # ── seccion_electoral → int ────────────────────────────────────────────────
    df["seccion_electoral"] = pd.to_numeric(
        df["seccion_electoral"], errors="coerce"
    ).astype("Int64")

    # ── terminada — derivado de duración (no hay campo estatus en Atlixco) ────
    # bubble_connector._transform() ya calcula duracion_min.
    # Se considera terminada si duracion_min >= 1 (formulario efectivamente
    # completado). Ajustar umbral si se identifica mejor indicador en campo.
    if "terminada" not in df.columns or df["terminada"].eq(False).all():
        if "duracion_min" in df.columns:
            df["terminada"] = df["duracion_min"].fillna(0) >= 1
        else:
            df["terminada"] = True   # fallback: asumir todos completos

    # ── filtrar secciones fuera de muestra ────────────────────────────────────
    df = df[~df["seccion_electoral"].isin(SECCIONES_FUERA_MUESTRA)].copy()

    # ── filtro opcional por lista de secciones ─────────────────────────────────
    if secciones:
        df = df[df["seccion_electoral"].isin(secciones)].copy()

    # ── zona ──────────────────────────────────────────────────────────────────
    _sec_zona = {sec: v["zona"] for sec, v in METAS_POR_SECCION.items()}
    df["zona"]       = df["seccion_electoral"].map(_sec_zona)
    df["zona_nombre"] = df["zona"].map(ZONA_NOMBRES)
    df["equipo"]     = df["zona_nombre"].fillna("Sin zona")

    return df, ultima_act 