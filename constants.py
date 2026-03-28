"""
constants.py — Constantes globales de la aplicación
=====================================================
Centraliza colores, versión, interfaces protegidas y presets de QoS.
Modifica aquí si quieres cambiar el tema visual o los valores por defecto.
"""

# ── Versión y metadatos ────────────────────────────────────────────────────────
APP_VERSION  = "v2.2  |  IOSvL2 15.2 / GRE-IPsec / S3 Backup"

# Interfaz de uplink/gestión que NUNCA se debe modificar desde la app.
# Esta interfaz conecta el switch al router/core; tocarlo puede dejar sin acceso.
UPLINK_IFACE = "GigabitEthernet0/0"

# ── Presets DSCP para QoS ──────────────────────────────────────────────────────
# Tuplas (etiqueta_visual, valor_IOS) para los botones rápidos de QoS.
# DSCP (Differentiated Services Code Point) define la prioridad del tráfico.
#   EF  = Expedited Forwarding → voz/video de baja latencia
#   AFxx = Assured Forwarding  → tráfico garantizado por clase
#   CSx  = Class Selector      → compatibilidad con IP Precedence legado
#   Default = Best Effort      → tráfico sin prioridad
DSCP_PRESETS = [
    ("EF  — Voz/Video (46)",          "ef"),
    ("AF41 — Video conferencia (34)", "af41"),
    ("AF31 — Llamadas (26)",          "af31"),
    ("AF21 — Datos críticos (18)",    "af21"),
    ("AF11 — Datos normales (10)",    "af11"),
    ("CS3  — Señalización (24)",      "cs3"),
    ("CS1  — Scavenger (8)",          "cs1"),
    ("Default — Best effort (0)",     "default"),
]

# ── Paleta de colores (tema oscuro estilo GitHub Dark) ─────────────────────────
# BG  = fondo principal       BG2 = fondo de paneles     BG3 = fondo de inputs
# ACCENT  = azul para énfasis ACCENT2 = naranja/rojo para botones de acción
# SUCCESS = verde para éxito  WARN = amarillo para advertencias
# TEXT  = texto principal     TEXT2 = texto secundario/gris
# BORDER = color del borde de los widgets
BG      = "#0d1117"
BG2     = "#161b22"
BG3     = "#21262d"
ACCENT  = "#58a6ff"
ACCENT2 = "#f78166"
SUCCESS = "#3fb950"
WARN    = "#d29922"
TEXT    = "#c9d1d9"
TEXT2   = "#8b949e"
BORDER  = "#30363d"

# ── Temas visuales disponibles ─────────────────────────────────────────────────
# Cada tema define la paleta completa.  LOG_BG/LOG_FG son para el área de consola.
THEMES = {
    "github_dark": {
        "name":    "GitHub Dark",
        "BG":      "#0d1117",
        "BG2":     "#161b22",
        "BG3":     "#21262d",
        "ACCENT":  "#58a6ff",
        "ACCENT2": "#f78166",
        "SUCCESS": "#3fb950",
        "WARN":    "#d29922",
        "TEXT":    "#c9d1d9",
        "TEXT2":   "#8b949e",
        "BORDER":  "#30363d",
        "LOG_BG":  "#010409",
        "LOG_FG":  "#00ff41",
    },
    "monokai": {
        "name":    "Monokai Pro",
        "BG":      "#1e1e2e",
        "BG2":     "#252538",
        "BG3":     "#2d2d48",
        "ACCENT":  "#ae81ff",
        "ACCENT2": "#fd971f",
        "SUCCESS": "#a6e22e",
        "WARN":    "#e6db74",
        "TEXT":    "#f8f8f2",
        "TEXT2":   "#75715e",
        "BORDER":  "#3e3d54",
        "LOG_BG":  "#141420",
        "LOG_FG":  "#a6e22e",
    },
    "nord_light": {
        "name":    "Nord Light",
        "BG":      "#eceff4",
        "BG2":     "#e5e9f0",
        "BG3":     "#d8dee9",
        "ACCENT":  "#5e81ac",
        "ACCENT2": "#bf616a",
        "SUCCESS": "#a3be8c",
        "WARN":    "#d08770",
        "TEXT":    "#2e3440",
        "TEXT2":   "#4c566a",
        "BORDER":  "#b0bec5",
        "LOG_BG":  "#2e3440",
        "LOG_FG":  "#a3be8c",
    },
}
