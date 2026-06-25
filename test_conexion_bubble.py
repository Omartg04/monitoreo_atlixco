"""
CEOP · test_conexion_bubble.py — Atlixco
Script de diagnóstico para validar la conexión a Bubble y los field names
antes de activar el dashboard.

Ejecutar desde la carpeta del proyecto:
    python test_conexion_bubble.py

Qué verifica:
  1. Conectividad básica al endpoint configurado en config.py
  2. Nombre correcto del Thing type (si da 404, ajustar BUBBLE_ENDPOINT)
  3. Campos reales del primer registro vs FIELD_MAP en config.py
     - Campos en FIELD_MAP que NO existen en Bubble → revisar nombre
     - Campos en Bubble que NO están en FIELD_MAP → evaluar si agregar
  4. Valor exacto de municipio_texto → actualizar transform_atlixco.py
  5. Valores de estatus → confirmar que "Terminada" es el valor correcto
  6. Volumen total de registros disponibles
"""
import json
import os
import sys

import requests

# ── Configuración ──────────────────────────────────────────────────────────────
API_KEY  = os.getenv("BUBBLE_API_KEY", "cdfa58720f2673840e1ba0a42c06068a")
BASE_URL = "https://encuesta-aspirante-atlixco-vl.bubbleapps.io/api/1.1/obj"

# Thing types a probar en orden — el primero que responda 200 es el correcto
THING_TYPES = ["Encuesta", "encuesta", "Survey", "survey", "Respuesta", "respuesta"]

from config import FIELD_MAP

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

SEP = "─" * 60


# ── 1. Detectar Thing type correcto ───────────────────────────────────────────
def detectar_thing_type() -> str | None:
    print(f"\n{SEP}")
    print("1. Detectando Thing type")
    print(SEP)
    for thing in THING_TYPES:
        url  = f"{BASE_URL}/{thing}"
        resp = requests.get(url, headers=HEADERS, params={"limit": 1}, timeout=10)
        status = resp.status_code
        print(f"  {thing:20s} → HTTP {status}", end="")
        if status == 200:
            n = resp.json().get("response", {}).get("count", "?")
            print(f"  ✅  ({n} registros totales)")
            return thing
        else:
            print(f"  ✗")
    return None


# ── 2. Obtener un registro de muestra ─────────────────────────────────────────
def obtener_muestra(thing_type: str, n: int = 3) -> list[dict]:
    url  = f"{BASE_URL}/{thing_type}"
    resp = requests.get(url, headers=HEADERS,
                        params={"limit": n, "cursor": 0}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("response", {}).get("results", [])


# ── 3. Comparar FIELD_MAP vs campos reales ─────────────────────────────────────
def comparar_field_map(registro: dict) -> None:
    print(f"\n{SEP}")
    print("3. Comparación FIELD_MAP vs campos reales de Bubble")
    print(SEP)

    campos_bubble  = set(registro.keys())
    campos_map     = set(FIELD_MAP.keys())

    faltantes = campos_map - campos_bubble    # en FIELD_MAP pero no en Bubble
    extras    = campos_bubble - campos_map    # en Bubble pero no en FIELD_MAP
    presentes = campos_map & campos_bubble   # coinciden

    print(f"\n  ✅  Campos presentes en ambos ({len(presentes)}):")
    for c in sorted(presentes):
        val = registro.get(c)
        preview = str(val)[:60] if val is not None else "None"
        print(f"       {c:40s} → {preview}")

    print(f"\n  ⚠️   En FIELD_MAP pero NO en Bubble ({len(faltantes)}) — revisar nombre:")
    for c in sorted(faltantes):
        print(f"       {c}")

    print(f"\n  ℹ️   En Bubble pero NO en FIELD_MAP ({len(extras)}) — evaluar si agregar:")
    for c in sorted(extras):
        val = registro.get(c)
        preview = str(val)[:50] if val is not None else "None"
        print(f"       {c:40s} → {preview}")


# ── 4. Verificar municipio_texto ───────────────────────────────────────────────
def verificar_municipio(registros: list[dict]) -> None:
    print(f"\n{SEP}")
    print("4. Valores de municipio_texto")
    print(SEP)
    valores = set()
    for r in registros:
        v = r.get("municipio_texto")
        if v:
            valores.add(str(v).strip())
    if valores:
        print(f"  Valores encontrados: {valores}")
        print(f"  → Usar exactamente este valor en transform_atlixco.py")
    else:
        print("  municipio_texto no encontrado o vacío en la muestra")


# ── 5. Verificar valores de estatus ───────────────────────────────────────────
def verificar_estatus(registros: list[dict]) -> None:
    print(f"\n{SEP}")
    print("5. Valores de estatus (para derivar `terminada`)")
    print(SEP)
    for campo in ["estatus", "Estatus", "status", "Status"]:
        valores = {str(r.get(campo, "")).strip() for r in registros if r.get(campo)}
        if valores:
            print(f"  Campo '{campo}': {valores}")
            print(f"  → bubble_connector._transform() usa: == 'Terminada'")
            return
    print("  Campo estatus no encontrado en la muestra — ampliar muestra o revisar nombre")


# ── 6. Volumen total ───────────────────────────────────────────────────────────
def verificar_volumen(thing_type: str) -> None:
    print(f"\n{SEP}")
    print("6. Volumen total de registros")
    print(SEP)
    url  = f"{BASE_URL}/{thing_type}"
    resp = requests.get(url, headers=HEADERS, params={"limit": 1}, timeout=10)
    body = resp.json().get("response", {})
    count     = body.get("count", "?")
    remaining = body.get("remaining", "?")
    print(f"  count (total tabla)  : {count}")
    print(f"  remaining (pág 0)    : {remaining}")
    print(f"  → Con BUBBLE_PAGE_SIZE=100, se necesitan ~{int(count)//100 + 1} páginas"
          if isinstance(count, int) else "  → count no disponible")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍 Test de conexión Bubble — Atlixco PIE 2026")
    print(f"   Base URL : {BASE_URL}")
    print(f"   API Key  : {API_KEY[:8]}{'*' * (len(API_KEY)-8)}")

    # 1. Thing type
    thing_type = detectar_thing_type()
    if not thing_type:
        print("\n❌ No se encontró ningún Thing type válido.")
        print("   Verifica en Bubble: Data → App data → nombre exacto del tipo.")
        sys.exit(1)

    print(f"\n  ✅ Thing type confirmado: '{thing_type}'")
    print(f"  → Actualizar config.py: BUBBLE_ENDPOINT = BASE_URL + '/obj/{thing_type}'")

    # 2. Muestra
    print(f"\n{SEP}")
    print("2. Obteniendo muestra de registros")
    print(SEP)
    try:
        registros = obtener_muestra(thing_type, n=5)
        print(f"  Registros obtenidos: {len(registros)}")
    except Exception as e:
        print(f"  ❌ Error obteniendo muestra: {e}")
        sys.exit(1)

    if not registros:
        print("  ⚠️  Sin registros — la tabla puede estar vacía todavía.")
        sys.exit(0)

    # 3-6. Validaciones
    comparar_field_map(registros[0])
    verificar_municipio(registros)
    verificar_estatus(registros)
    verificar_volumen(thing_type)

    print(f"\n{SEP}")
    print("✅ Diagnóstico completado.")
    print("   Revisa los ⚠️  y ajusta FIELD_MAP en config.py antes de activar el dashboard.")
    print(SEP)
