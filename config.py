"""
Atlixco PIE · config.py (Encuesta L2)
Parámetros centralizados para el visualizador de monitoreo y auditoría.
Editar aquí — no tocar app.py / kpis.py / flags.py para cambiar umbrales o mapeos.

Fuentes:
  - Diccionario_Referencia_Atlixco_version_lite.csv (162 campos confirmados)
  - E2_Subconjunto_Cuotas_Atlixco.xlsx (n=840, 42 secciones, 6 zonas)
  - SECCION.shp (catálogo seccional Puebla, IEE/INE) — municipio=19 → Atlixco
  - Registro real Bubble validado 2026-06-25
"""

# ── API Bubble ─────────────────────────────────────────────────────────────────
# Thing type confirmado: "Encuesta" (HTTP 200 validado)
BUBBLE_BASE_URL  = "https://encuesta-aspirante-atlixco-vl.bubbleapps.io/api/1.1"
BUBBLE_ENDPOINT  = f"{BUBBLE_BASE_URL}/obj/Encuesta"
BUBBLE_PAGE_SIZE = 100
CACHE_TTL_SEC    = 3600

# ── Calendario de operativo ────────────────────────────────────────────────────
# TODO: confirmar fechas exactas de jornadas con el PO.
INICIO_OPERATIVO = "2026-06-26"

# ── Umbrales de calidad (flags) ────────────────────────────────────────────────
# TODO CONFIRMAR con stakeholder antes de activar en producción.
DUR_MIN_MIN = 5
DUR_MAX_MIN = 40

UMBRAL_STRAIGHTLINING_BLOQUE7 = 7
UMBRAL_STRAIGHTLINING_BLOQUE6 = 5

HORA_INICIO_OPERATIVO = 8
HORA_FIN_OPERATIVO    = 19

AUTO_REFRESH_SEC = 300

# ── Identidad visual ───────────────────────────────────────────────────────────
VERDE    = "#2E7D5E"
VERDE_L  = "#52B788"
AZUL     = "#1A3A5C"
AZUL_L   = "#2C6E9E"
NARANJA  = "#E07B39"
ROJO     = "#C0392B"
AMARILLO = "#F5A623"
GRIS_BG  = "#F2F4F7"

ZONA_COLORES = {
    1: "#1A2744",
    2: "#1B5E20",
    3: "#0D47A1",
    4: "#B71C1C",
    5: "#E65100",
    6: "#6A1B9A",
}

ZONA_NOMBRES = {
    1: "Z1 · Noreste Norte",
    2: "Z2 · Norte/Poniente",
    3: "Z3 · Centro Oriente",
    4: "Z4 · Centro",
    5: "Z5 · Oriente Rural",
    6: "Z6 · Sur",
}

# ── Candidatos / Aspirantes ────────────────────────────────────────────────────
# Confirmados desde Diccionario_Referencia_Atlixco_version_lite.csv
CANDIDATOS = {
    "arturo":    "Arturo Solano Escobedo",
    "ana":       "Ana Laura Altamirano",
    "modesta":   "Modesta Delgado",
    "francisco": "Francisco García",
    "jesus":     "Jesús Luévano",
}

ATRIBUTOS_BLOQUE7 = [
    "honestidad", "cercania", "derecho_mujeres", "conocimiento_estado",
    "cumplimiento", "buena_candidatura", "votar_o_no",
]

# ── Mapeo campos Bubble → app ──────────────────────────────────────────────────
# Validado contra registro real de Bubble (2026-06-25).
# ⚠️  P9_5_text (sin "o") y P23_96_text, P23_98_text, P23_99_text confirmados en diccionario.
# ⚠️  P2_2_text (sin "o") confirmado en diccionario y en registro real.
FIELD_MAP = {
    # Bloque 1: Datos de captura
    '_id'                                          : 'id_unico',
    'Created Date'                                 : 'fecha_creacion',
    'Modified Date'                                : 'fecha_modificacion',
    'Created By'                                   : 'user_creador',
    'nombre_encuestador'                           : 'nombre_encuestador',
    # Bloque 2: Identificación de la vivienda
    'seccion_electoral'                            : 'seccion_electoral',
    'municipio_texto'                              : 'municipio_texto',
    'google_address'                               : 'google_address',
    'latitud'                                      : 'latitud',
    'longitud'                                     : 'longitud',
    # Bloque 3: Sexo, Edad, INE
    'A'                                            : 'codigo_sexo',
    'A_texto'                                      : 'sexo',
    'B'                                            : 'edad',
    'B_98'                                         : 'codigo_rango_edad',
    'B_98_texto'                                   : 'rango_edad',
    'C'                                            : 'codigo_ine',
    'C_texto'                                      : 'ine',
    # Bloque 4: Principal problema del estado
    'P1'                                           : 'codigo_direccion_estado',
    'P1_texto'                                     : 'direccion_estado',
    'P2_1'                                         : 'codigo_principal_problema',
    'P2_1_otro'                                    : 'principal_problema_estado_otro',
    'P2_1_texto'                                   : 'principal_problema_estado_opciones',
    'P2_2'                                         : 'codigo_tipo_inseguridad',
    'P2_2_otro'                                    : 'tipo_inseguridad_otro',
    'P2_2_text'                                    : 'tipo_inseguridad_opciones',   # ⚠️ sin 'o'
    'P3'                                           : 'codigo_servicios_publicos',
    'P3_otro'                                      : 'servicios_publicos_otro',
    'P3_texto'                                     : 'servicios_publicos_opciones',
    # Bloque 5: Intención de voto y afinidad partidista
    'P4'                                           : 'codigo_identificacion_partidaria',
    'P4_texto'                                     : 'identificacion_partidaria',
    'P5'                                           : 'codigo_intencion_voto_principal',
    'P5_texto'                                     : 'intencion_voto_principal',
    # Bloque 6: Conocimiento y opinión de aspirantes
    'P8_1'                                         : 'codigo_conocimiento_arturo',
    'P8_1_texto'                                   : 'conocimiento_arturo',
    'P8_2'                                         : 'codigo_conocimiento_ana',
    'P8_2_texto'                                   : 'conocimiento_ana',
    'P8_3'                                         : 'codigo_conocimiento_modesta',
    'P8_3_texto'                                   : 'conocimiento_modesta',
    'P8_4'                                         : 'codigo_conocimiento_francisco',
    'P8_4_texto'                                   : 'conocimiento_francisco',
    'P8_5'                                         : 'codigo_conocimiento_jesus',
    'P8_5_texto'                                   : 'conocimiento_jesus',
    'P9_1'                                         : 'codigo_opinion_arturo',
    'P9_1_texto'                                   : 'opinion_arturo',
    'P9_2'                                         : 'codigo_opinion_ana',
    'P9_2_texto'                                   : 'opinion_ana',
    'P9_3'                                         : 'codigo_opinion_modesta',
    'P9_3_texto'                                   : 'opinion_modesta',
    'P9_4'                                         : 'codigo_opinion_francisco',
    'P9_4_texto'                                   : 'opinion_francisco',
    'P9_5'                                         : 'codigo_opinion_jesus',
    'P9_5_text'                                    : 'opinion_jesus',              # ⚠️ sin 'o'
    # Bloque 7: Evaluación de atributos de aspirantes
    'P10_1'                                        : 'codigo_honestidad_arturo',
    'P10_1_texto'                                  : 'honestidad_arturo',
    'P10_2'                                        : 'codigo_honestidad_ana',
    'P10_2_texto'                                  : 'honestidad_ana',
    'P10_3'                                        : 'codigo_honestidad_modesta',
    'P10_3_texto'                                  : 'honestidad_modesta',
    'P10_4'                                        : 'codigo_honestidad_francisco',
    'P10_4_texto'                                  : 'honestidad_francisco',
    'P10_5'                                        : 'codigo_honestidad_jesus',
    'P10_5_texto'                                  : 'honestidad_jesus',
    'P11_1'                                        : 'codigo_cercania_arturo',
    'P11_1_texto'                                  : 'cercania_arturo',
    'P11_2'                                        : 'codigo_cercania_ana',
    'P11_2_texto'                                  : 'cercania_ana',
    'P11_3'                                        : 'codigo_cercania_modesta',
    'P11_3_texto'                                  : 'cercania_modesta',
    'P11_4'                                        : 'codigo_cercania_francisco',
    'P11_4_texto'                                  : 'cercania_francisco',
    'P11_5'                                        : 'codigo_cercania_jesus',
    'P11_5_texto'                                  : 'cercania_jesus',
    'P12_1'                                        : 'codigo_derecho_mujeres_arturo',
    'P12_1_texto'                                  : 'derecho_mujeres_arturo',
    'P12_2'                                        : 'codigo_derecho_mujeres_ana',
    'P12_2_texto'                                  : 'derecho_mujeres_ana',
    'P12_3'                                        : 'codigo_derecho_mujeres_modesta',
    'P12_3_texto'                                  : 'derecho_mujeres_modesta',
    'P12_4'                                        : 'codigo_derecho_mujeres_francisco',
    'P12_4_texto'                                  : 'derecho_mujeres_francisco',
    'P12_5'                                        : 'codigo_derecho_mujeres_jesus',
    'P12_5_texto'                                  : 'derecho_mujeres_jesus',
    'P13_1'                                        : 'codigo_conocimiento_estado_arturo',
    'P13_1_texto'                                  : 'conocimiento_estado_arturo',
    'P13_2'                                        : 'codigo_conocimiento_estado_ana',
    'P13_2_texto'                                  : 'conocimiento_estado_ana',
    'P13_3'                                        : 'codigo_conocimiento_estado_modesta',
    'P13_3_texto'                                  : 'conocimiento_estado_modesta',
    'P13_4'                                        : 'codigo_conocimiento_estado_francisco',
    'P13_4_texto'                                  : 'conocimiento_estado_francisco',
    'P13_5'                                        : 'codigo_conocimiento_estado_jesus',
    'P13_5_texto'                                  : 'conocimiento_estado_jesus',
    'P14_1'                                        : 'codigo_cumplimiento_arturo',
    'P14_1_texto'                                  : 'cumplimiento_arturo',
    'P14_2'                                        : 'codigo_cumplimiento_ana',
    'P14_2_texto'                                  : 'cumplimiento_ana',
    'P14_3'                                        : 'codigo_cumplimiento_modesta',
    'P14_3_texto'                                  : 'cumplimiento_modesta',
    'P14_4'                                        : 'codigo_cumplimiento_francisco',
    'P14_4_texto'                                  : 'cumplimiento_francisco',
    'P14_5'                                        : 'codigo_cumplimiento_jesus',
    'P14_5_texto'                                  : 'cumplimiento_jesus',
    'P15_1'                                        : 'codigo_buena_candidatura_arturo',
    'P15_1_texto'                                  : 'buena_candidatura_arturo',
    'P15_2'                                        : 'codigo_buena_candidatura_ana',
    'P15_2_texto'                                  : 'buena_candidatura_ana',
    'P15_3'                                        : 'codigo_buena_candidatura_modesta',
    'P15_3_texto'                                  : 'buena_candidatura_modesta',
    'P15_4'                                        : 'codigo_buena_candidatura_francisco',
    'P15_4_texto'                                  : 'buena_candidatura_francisco',
    'P15_5'                                        : 'codigo_buena_candidatura_jesus',
    'P15_5_texto'                                  : 'buena_candidatura_jesus',
    'P16_1'                                        : 'codigo_votar_o_no_arturo',
    'P16_1_texto'                                  : 'votar_o_no_arturo',
    'P16_2'                                        : 'codigo_votar_o_no_ana',
    'P16_2_texto'                                  : 'votar_o_no_ana',
    'P16_3'                                        : 'codigo_votar_o_no_modesta',
    'P16_3_texto'                                  : 'votar_o_no_modesta',
    'P16_4'                                        : 'codigo_votar_o_no_francisco',
    'P16_4_texto'                                  : 'votar_o_no_francisco',
    'P16_5'                                        : 'codigo_votar_o_no_jesus',
    'P16_5_texto'                                  : 'votar_o_no_jesus',
    # Bloque 8: Preferencia de candidato(a) de MORENA
    'P19_1'                                        : 'codigo_preferencia_total_morena',
    'P19_1_texto'                                  : 'preferencia_total_morena',
    # Bloque 10: Evaluación de autoridades
    'P22_1'                                        : 'codigo_aprobacion_atlixco',
    'P22_1_texto'                                  : 'aprobacion_atlixco',
    'P22_2'                                        : 'codigo_aprobacion_gobernador',
    'P22_2_texto'                                  : 'aprobacion_gobernador',
    'P22_3'                                        : 'codigo_aprobacion_presidenta',
    'P22_3_texto'                                  : 'aprobacion_presidenta',
    # Bloque 11: Programas sociales y uso de medios
    'P23_1'                                        : 'codigo_medio_television',
    'P23_1_texto'                                  : 'medio_television',
    'P23_2'                                        : 'codigo_medio_radio',
    'P23_2_texto'                                  : 'medio_radio',
    'P23_3'                                        : 'codigo_medio_periodico',
    'P23_3_texto'                                  : 'medio_periodico',
    'P23_4'                                        : 'codigo_medio_facebook',
    'P23_4_texto'                                  : 'medio_facebook',
    'P23_5'                                        : 'codigo_medio_x',
    'P23_5_texto'                                  : 'medio_x',
    'P23_6'                                        : 'codigo_medio_instagram',
    'P23_6_texto'                                  : 'medio_instagram',
    'P23_7'                                        : 'codigo_medio_youtube',
    'P23_7_texto'                                  : 'medio_youtube',
    'P23_8'                                        : 'codigo_medio_whatsapp',
    'P23_8_texto'                                  : 'medio_whatsapp',
    'P23_9'                                        : 'codigo_medio_tiktok',
    'P23_9_texto'                                  : 'medio_tiktok',
    'P23_96'                                       : 'codigo_medio_otro',
    'P23_96_text'                                  : 'medio_otro',                 # ⚠️ sin 'o'
    'P23_otro'                                     : 'medio_nombrar_otro',
    'P23_98'                                       : 'codigo_medio_no_sabe',
    'P23_98_text'                                  : 'medio_no_sabe',              # ⚠️ sin 'o'
    'P23_99'                                       : 'codigo_medio_no_respondio',
    'P23_99_text'                                  : 'medio_no_respondio',         # ⚠️ sin 'o'
    # Bloque 12: Información sociodemográfica
    'D1'                                           : 'codigo_ocupacion',
    'D1_text'                                      : 'ocupacion',                  # ⚠️ sin 'o'
    'D2'                                           : 'codigo_estado_civil',
    'D2_text'                                      : 'estado_civil',               # ⚠️ sin 'o'
    'D3'                                           : 'codigo_nivel_escolaridad',
    'D3_text'                                      : 'nivel_escolaridad',          # ⚠️ sin 'o'
    # Bloque 13: Afectación por inseguridad
    'E1'                                           : 'codigo_afectacion_inseguridad',
    'E1_texto'                                     : 'afectacion_inseguridad',
    'E2'                                           : 'costo_economico_inseguridad',
}

CAMPOS_OCULTAR_DISPLAY = {
    "google_address", "latitud", "longitud", "user_creador",
}
CAMPOS_EXCLUIR = set()

# ── Baterías de straightlining ─────────────────────────────────────────────────
BATERIAS_STRAIGHTLINING = {
    **{
        f"bloque7_{cand}": [f"codigo_{atributo}_{cand}" for atributo in ATRIBUTOS_BLOQUE7]
        for cand in CANDIDATOS
    },
    "bloque6_conocimiento": [f"codigo_conocimiento_{cand}" for cand in CANDIDATOS],
    "bloque6_opinion":      [f"codigo_opinion_{cand}"      for cand in CANDIDATOS],
}

# ── Geografía ──────────────────────────────────────────────────────────────────
ENTIDAD           = 21
CLAVE_MUNICIPIO   = 19
GEOJSON_SECCIONES = "secciones_atlixco.geojson"
ATLIXCO_CENTRO    = [18.9010, -98.4506]
ATLIXCO_ZOOM      = 12

SECCIONES_MUESTRA = {
    160,208,174,201,164,212,169,186,216,215,159,202,154,170,207,
    185,173,213,209,165,2876,2874,2875,196,168,219,214,217,177,
    158,197,203,204,166,193,187,175,206,162,194,176,198,
}
SECCIONES_FUERA_MUESTRA = {
    155,156,157,161,163,167,171,172,178,179,180,181,182,183,184,
    188,189,190,191,192,195,199,200,205,210,211,218,220,221,2873,
}

# ── Metas por sección electoral ────────────────────────────────────────────────
METAS_POR_SECCION = {
    # Z1 · Noreste Norte
    160: {'tipo': 'Urbana', 'zona': 1, 'ln_total': 7388, 'meta_encuestas': 67, 'cuotas': {'H': 31, 'M': 36}},
    208: {'tipo': 'Rural',  'zona': 1, 'ln_total': 4834, 'meta_encuestas': 44, 'cuotas': {'H': 20, 'M': 24}},
    2874:{'tipo': 'Urbana', 'zona': 1, 'ln_total': 2000, 'meta_encuestas': 18, 'cuotas': {'H': 8,  'M': 10}},
    162: {'tipo': 'Urbana', 'zona': 1, 'ln_total': 1383, 'meta_encuestas': 13, 'cuotas': {'H': 6,  'M': 7}},
    # Z2 · Norte/Poniente
    174: {'tipo': 'Mixta',  'zona': 2, 'ln_total': 3618, 'meta_encuestas': 33, 'cuotas': {'H': 15, 'M': 18}},
    207: {'tipo': 'Mixta',  'zona': 2, 'ln_total': 2145, 'meta_encuestas': 20, 'cuotas': {'H': 9,  'M': 11}},
    170: {'tipo': 'Urbana', 'zona': 2, 'ln_total': 2155, 'meta_encuestas': 20, 'cuotas': {'H': 9,  'M': 11}},
    173: {'tipo': 'Urbana', 'zona': 2, 'ln_total': 2074, 'meta_encuestas': 19, 'cuotas': {'H': 9,  'M': 10}},
    158: {'tipo': 'Mixta',  'zona': 2, 'ln_total': 1699, 'meta_encuestas': 15, 'cuotas': {'H': 7,  'M': 8}},
    154: {'tipo': 'Urbana', 'zona': 2, 'ln_total': 2272, 'meta_encuestas': 21, 'cuotas': {'H': 10, 'M': 11}},
    206: {'tipo': 'Urbana', 'zona': 2, 'ln_total': 1387, 'meta_encuestas': 13, 'cuotas': {'H': 6,  'M': 7}},
    # Z3 · Centro Oriente
    164: {'tipo': 'Urbana', 'zona': 3, 'ln_total': 2926, 'meta_encuestas': 27, 'cuotas': {'H': 13, 'M': 14}},
    186: {'tipo': 'Urbana', 'zona': 3, 'ln_total': 2463, 'meta_encuestas': 22, 'cuotas': {'H': 10, 'M': 12}},
    185: {'tipo': 'Urbana', 'zona': 3, 'ln_total': 2130, 'meta_encuestas': 19, 'cuotas': {'H': 9,  'M': 10}},
    2876:{'tipo': 'Urbana', 'zona': 3, 'ln_total': 2013, 'meta_encuestas': 18, 'cuotas': {'H': 8,  'M': 10}},
    165: {'tipo': 'Urbana', 'zona': 3, 'ln_total': 2021, 'meta_encuestas': 18, 'cuotas': {'H': 8,  'M': 10}},
    2875:{'tipo': 'Urbana', 'zona': 3, 'ln_total': 1980, 'meta_encuestas': 18, 'cuotas': {'H': 8,  'M': 10}},
    166: {'tipo': 'Urbana', 'zona': 3, 'ln_total': 1529, 'meta_encuestas': 14, 'cuotas': {'H': 7,  'M': 7}},
    187: {'tipo': 'Urbana', 'zona': 3, 'ln_total': 1451, 'meta_encuestas': 13, 'cuotas': {'H': 6,  'M': 7}},
    194: {'tipo': 'Urbana', 'zona': 3, 'ln_total': 1354, 'meta_encuestas': 12, 'cuotas': {'H': 6,  'M': 6}},
    # Z4 · Centro
    169: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 2737, 'meta_encuestas': 25, 'cuotas': {'H': 12, 'M': 13}},
    159: {'tipo': 'Mixta',  'zona': 4, 'ln_total': 2339, 'meta_encuestas': 21, 'cuotas': {'H': 10, 'M': 11}},
    168: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 1858, 'meta_encuestas': 17, 'cuotas': {'H': 8,  'M': 9}},
    177: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 1748, 'meta_encuestas': 16, 'cuotas': {'H': 7,  'M': 9}},
    175: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 1449, 'meta_encuestas': 13, 'cuotas': {'H': 6,  'M': 7}},
    193: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 1489, 'meta_encuestas': 14, 'cuotas': {'H': 6,  'M': 8}},
    197: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 1666, 'meta_encuestas': 15, 'cuotas': {'H': 7,  'M': 8}},
    176: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 1347, 'meta_encuestas': 12, 'cuotas': {'H': 6,  'M': 6}},
    198: {'tipo': 'Urbana', 'zona': 4, 'ln_total': 1324, 'meta_encuestas': 12, 'cuotas': {'H': 6,  'M': 6}},
    # Z5 · Oriente Rural
    215: {'tipo': 'Rural',  'zona': 5, 'ln_total': 2376, 'meta_encuestas': 22, 'cuotas': {'H': 10, 'M': 12}},
    216: {'tipo': 'Rural',  'zona': 5, 'ln_total': 2384, 'meta_encuestas': 22, 'cuotas': {'H': 10, 'M': 12}},
    209: {'tipo': 'Rural',  'zona': 5, 'ln_total': 2041, 'meta_encuestas': 19, 'cuotas': {'H': 9,  'M': 10}},
    219: {'tipo': 'Rural',  'zona': 5, 'ln_total': 1845, 'meta_encuestas': 17, 'cuotas': {'H': 8,  'M': 9}},
    214: {'tipo': 'Rural',  'zona': 5, 'ln_total': 1787, 'meta_encuestas': 16, 'cuotas': {'H': 7,  'M': 9}},
    217: {'tipo': 'Rural',  'zona': 5, 'ln_total': 1780, 'meta_encuestas': 16, 'cuotas': {'H': 7,  'M': 9}},
    # Z6 · Sur
    201: {'tipo': 'Urbana', 'zona': 6, 'ln_total': 3011, 'meta_encuestas': 27, 'cuotas': {'H': 13, 'M': 14}},
    212: {'tipo': 'Mixta',  'zona': 6, 'ln_total': 2739, 'meta_encuestas': 25, 'cuotas': {'H': 12, 'M': 13}},
    202: {'tipo': 'Mixta',  'zona': 6, 'ln_total': 2284, 'meta_encuestas': 21, 'cuotas': {'H': 10, 'M': 11}},
    213: {'tipo': 'Urbana', 'zona': 6, 'ln_total': 2052, 'meta_encuestas': 19, 'cuotas': {'H': 9,  'M': 10}},
    196: {'tipo': 'Urbana', 'zona': 6, 'ln_total': 1901, 'meta_encuestas': 17, 'cuotas': {'H': 8,  'M': 9}},
    204: {'tipo': 'Mixta',  'zona': 6, 'ln_total': 1614, 'meta_encuestas': 15, 'cuotas': {'H': 6,  'M': 9}},
    203: {'tipo': 'Mixta',  'zona': 6, 'ln_total': 1664, 'meta_encuestas': 15, 'cuotas': {'H': 7,  'M': 8}},
}

META_GLOBAL = sum(v["meta_encuestas"] for v in METAS_POR_SECCION.values())
assert META_GLOBAL == 840, f"Meta global incorrecta: {META_GLOBAL}"

META_POR_ZONA = {}
for sec, v in METAS_POR_SECCION.items():
    z = v["zona"]
    META_POR_ZONA[z] = META_POR_ZONA.get(z, 0) + v["meta_encuestas"]

SECCIONES_POR_ZONA: dict[int, list[int]] = {}
for sec, v in METAS_POR_SECCION.items():
    SECCIONES_POR_ZONA.setdefault(v["zona"], []).append(sec)
for z in SECCIONES_POR_ZONA:
    SECCIONES_POR_ZONA[z].sort()

# ── Roles ──────────────────────────────────────────────────────────────────────
ROLES = {
    "omar": {
        "rol":       "estatal",
        "zonas":     list(ZONA_NOMBRES.keys()),
        "secciones": list(METAS_POR_SECCION.keys()),
    },
    "arturo": {
        "rol":       "estatal",
        "zonas":     list(ZONA_NOMBRES.keys()),
        "secciones": list(METAS_POR_SECCION.keys()),
    },
    "yarith": {
        "rol":       "estatal",
        "zonas":     list(ZONA_NOMBRES.keys()),
        "secciones": list(METAS_POR_SECCION.keys()),
    },

    "victor": {
        "rol":       "estatal",
        "zonas":     list(ZONA_NOMBRES.keys()),
        "secciones": list(METAS_POR_SECCION.keys()),
    },
   
    "dai": {
        "rol":       "estatal",
        "zonas":     list(ZONA_NOMBRES.keys()),
        "secciones": list(METAS_POR_SECCION.keys()),
    },


}