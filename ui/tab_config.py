"""
ui/tab_config.py — Pestaña ⑩ Configuración de Empresa y Estilos
================================================================
Centraliza los parámetros que normalmente son iguales en toda la empresa
(usuario SSH, interfaz uplink, DNS, OSPF, S3, etc.) y permite cambiar
el tema visual de la app en tiempo real.

Widgets creados en 'app':
  app.cfg_empresa        : Entry  — nombre de la empresa
  app.cfg_ssh_user       : Entry  — usuario SSH por defecto
  app.cfg_ssh_port       : Entry  — puerto SSH por defecto
  app.cfg_ssh_timeout    : Entry  — timeout de conexión (seg)
  app.cfg_uplink         : Entry  — interfaz de uplink protegida
  app.cfg_dns1           : Entry  — DNS primario por defecto
  app.cfg_dns2           : Entry  — DNS secundario por defecto
  app.cfg_dhcp_mask      : Entry  — máscara DHCP por defecto
  app.cfg_ospf_pid       : Entry  — PID OSPF por defecto
  app.cfg_ospf_area      : Entry  — área OSPF por defecto
  app.cfg_login_attempts : Entry  — intentos máx. antes de bloqueo
  app.cfg_login_window   : Entry  — ventana de tiempo (seg)
  app.cfg_login_block    : Entry  — duración del bloqueo (seg)
  app.cfg_banner         : Text   — texto del banner MOTD por defecto
  app.cfg_s3_region      : Entry  — región AWS S3 por defecto
  app.cfg_s3_bucket      : Entry  — bucket S3 por defecto
  app.cfg_s3_prefix      : Entry  — prefijo/carpeta S3 por defecto
  app.cfg_theme_status   : Label  — estado del tema activo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import tkinter as tk
from tkinter import messagebox

import constants
from constants import (BG, BG2, BG3, ACCENT, ACCENT2, SUCCESS, WARN,
                       TEXT, TEXT2, BORDER, THEMES)
from ui.widgets import (make_frame, make_label, make_entry, make_button,
                        make_labelframe, make_title, make_scrolled_text,
                        make_scrolled_frame, switch_theme)

# Ruta al archivo de configuración persistente (junto a app.py)
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app_config.json"
)

# Valores de fábrica
DEFAULT_CONFIG = {
    "empresa":          "",
    "ssh_user":         "admin",
    "ssh_port":         "22",
    "ssh_timeout":      "20",
    "uplink_iface":     "GigabitEthernet0/0",
    "dhcp_dns1":        "8.8.8.8",
    "dhcp_dns2":        "8.8.4.4",
    "dhcp_mask":        "255.255.255.0",
    "ospf_pid":         "1",
    "ospf_area":        "0",
    "login_attempts":   "3",
    "login_window":     "60",
    "login_block":      "300",
    "banner_motd":      ("ACCESO RESTRINGIDO\n"
                         "Solo personal autorizado. El acceso no autorizado\n"
                         "está prohibido y será sancionado conforme a la ley."),
    "s3_region":        "us-east-1",
    "s3_bucket":        "",
    "s3_prefix":        "backups/switches/",
    "theme":            "github_dark",
}


# ── I/O de configuración ───────────────────────────────────────────────────────

def load_config() -> dict:
    """Carga la config desde JSON; si no existe devuelve los valores de fábrica."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULT_CONFIG, **data}
        except Exception as e:
            print(f"[tab_config] Error cargando app_config.json: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    """Persiste la config en app_config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── Constructor de la pestaña ──────────────────────────────────────────────────

def build_tab_config(app, parent):
    """Construye la pestaña ⑩ Configuración."""
    inner = make_scrolled_frame(parent)

    make_title(inner, "⚙  Configuración de Empresa y Estilos")

    # ── 1. Información de la empresa ──────────────────────────────────────────
    frm_emp = make_labelframe(inner, "🏢  Información de la Empresa")
    frm_emp.pack(fill="x", padx=20, pady=6)
    make_label(frm_emp,
               "El nombre de la empresa aparece en el título de la ventana.",
               fg=TEXT2).pack(anchor="w")
    row_emp = make_frame(frm_emp); row_emp.pack(fill="x", pady=4)
    make_label(row_emp, "Nombre empresa:", width=22).grid(row=0, column=0, sticky="w")
    app.cfg_empresa = make_entry(row_emp, width=40)
    app.cfg_empresa.grid(row=0, column=1, padx=6)

    # ── 2. Defaults SSH ───────────────────────────────────────────────────────
    frm_ssh = make_labelframe(inner, "🔌  Valores por Defecto — SSH")
    frm_ssh.pack(fill="x", padx=20, pady=6)
    make_label(frm_ssh,
               "Se pre-rellenan al agregar sucursales y al aplicar defaults.",
               fg=TEXT2).pack(anchor="w")
    ssh_g = make_frame(frm_ssh); ssh_g.pack(fill="x", pady=4)
    make_label(ssh_g, "Usuario SSH:",    width=22).grid(row=0, column=0, sticky="w", pady=2)
    app.cfg_ssh_user = make_entry(ssh_g, width=22)
    app.cfg_ssh_user.grid(row=0, column=1, padx=6)
    make_label(ssh_g, "Puerto SSH:",     width=16).grid(row=0, column=2, sticky="w")
    app.cfg_ssh_port = make_entry(ssh_g, width=8)
    app.cfg_ssh_port.grid(row=0, column=3, padx=6)
    make_label(ssh_g, "Timeout (seg):",  width=22).grid(row=1, column=0, sticky="w", pady=2)
    app.cfg_ssh_timeout = make_entry(ssh_g, width=8)
    app.cfg_ssh_timeout.grid(row=1, column=1, padx=6, sticky="w")

    # ── 3. Interfaz de Uplink ─────────────────────────────────────────────────
    frm_iface = make_labelframe(inner, "🔗  Interfaz de Uplink Protegida")
    frm_iface.pack(fill="x", padx=20, pady=6)
    make_label(frm_iface,
               "Esta interfaz NUNCA es modificada por la app (conecta al router/core).",
               fg=TEXT2).pack(anchor="w")
    make_label(frm_iface,
               "⚠  Cambiarla aquí actualiza la protección para la sesión actual.",
               fg=WARN).pack(anchor="w")
    iface_r = make_frame(frm_iface); iface_r.pack(fill="x", pady=4)
    make_label(iface_r, "UPLINK_IFACE:",  width=22).grid(row=0, column=0, sticky="w")
    app.cfg_uplink = make_entry(iface_r, width=30)
    app.cfg_uplink.grid(row=0, column=1, padx=6)
    make_label(iface_r, "ej: GigabitEthernet0/0,  Gi0/0", fg=TEXT2).grid(row=0, column=2, padx=4)

    # ── 4. Defaults DHCP ──────────────────────────────────────────────────────
    frm_dhcp = make_labelframe(inner, "📋  Valores por Defecto — DHCP")
    frm_dhcp.pack(fill="x", padx=20, pady=6)
    dhcp_g = make_frame(frm_dhcp); dhcp_g.pack(fill="x", pady=4)
    make_label(dhcp_g, "DNS primario:",    width=22).grid(row=0, column=0, sticky="w", pady=2)
    app.cfg_dns1 = make_entry(dhcp_g, width=18)
    app.cfg_dns1.grid(row=0, column=1, padx=6)
    make_label(dhcp_g, "DNS secundario:", width=18).grid(row=0, column=2, sticky="w")
    app.cfg_dns2 = make_entry(dhcp_g, width=18)
    app.cfg_dns2.grid(row=0, column=3, padx=6)
    make_label(dhcp_g, "Máscara defecto:", width=22).grid(row=1, column=0, sticky="w", pady=2)
    app.cfg_dhcp_mask = make_entry(dhcp_g, width=18)
    app.cfg_dhcp_mask.grid(row=1, column=1, padx=6)

    # ── 5. Defaults OSPF ──────────────────────────────────────────────────────
    frm_ospf = make_labelframe(inner, "🗺  Valores por Defecto — OSPF")
    frm_ospf.pack(fill="x", padx=20, pady=6)
    ospf_g = make_frame(frm_ospf); ospf_g.pack(fill="x", pady=4)
    make_label(ospf_g, "PID OSPF:",   width=22).grid(row=0, column=0, sticky="w")
    app.cfg_ospf_pid = make_entry(ospf_g, width=8)
    app.cfg_ospf_pid.grid(row=0, column=1, padx=6)
    make_label(ospf_g, "Área OSPF:",  width=16).grid(row=0, column=2, sticky="w")
    app.cfg_ospf_area = make_entry(ospf_g, width=8)
    app.cfg_ospf_area.grid(row=0, column=3, padx=6)

    # ── 6. Defaults Seguridad ─────────────────────────────────────────────────
    frm_sec = make_labelframe(inner, "🔐  Valores por Defecto — Seguridad")
    frm_sec.pack(fill="x", padx=20, pady=6)
    sec_g = make_frame(frm_sec); sec_g.pack(fill="x", pady=4)
    make_label(sec_g, "Intentos máx login:",  width=22).grid(row=0, column=0, sticky="w", pady=2)
    app.cfg_login_attempts = make_entry(sec_g, width=8)
    app.cfg_login_attempts.grid(row=0, column=1, padx=6)
    make_label(sec_g, "Ventana (seg):",       width=16).grid(row=0, column=2, sticky="w")
    app.cfg_login_window = make_entry(sec_g, width=8)
    app.cfg_login_window.grid(row=0, column=3, padx=6)
    make_label(sec_g, "Duración bloqueo (seg):", width=22).grid(row=1, column=0, sticky="w", pady=2)
    app.cfg_login_block = make_entry(sec_g, width=8)
    app.cfg_login_block.grid(row=1, column=1, padx=6)
    make_label(frm_sec, "Banner MOTD por defecto:", fg=TEXT2).pack(anchor="w", pady=(6, 2))
    app.cfg_banner = make_scrolled_text(frm_sec, width=90, height=3, fg=TEXT)
    app.cfg_banner.pack(fill="x", padx=4, pady=2)

    # ── 7. Defaults S3 ────────────────────────────────────────────────────────
    frm_s3 = make_labelframe(inner, "☁  Valores por Defecto — AWS S3")
    frm_s3.pack(fill="x", padx=20, pady=6)
    s3_g = make_frame(frm_s3); s3_g.pack(fill="x", pady=4)
    make_label(s3_g, "Región AWS:",      width=22).grid(row=0, column=0, sticky="w", pady=2)
    app.cfg_s3_region = make_entry(s3_g, width=18)
    app.cfg_s3_region.grid(row=0, column=1, padx=6)
    make_label(s3_g, "Bucket S3:",       width=16).grid(row=0, column=2, sticky="w")
    app.cfg_s3_bucket = make_entry(s3_g, width=26)
    app.cfg_s3_bucket.grid(row=0, column=3, padx=6)
    make_label(s3_g, "Prefijo/carpeta:", width=22).grid(row=1, column=0, sticky="w", pady=2)
    app.cfg_s3_prefix = make_entry(s3_g, width=30)
    app.cfg_s3_prefix.grid(row=1, column=1, padx=6, sticky="w")

    # ── Botones de acción ─────────────────────────────────────────────────────
    btn_row = make_frame(inner); btn_row.pack(fill="x", padx=20, pady=10)
    make_button(btn_row, "💾  Guardar configuración",
                lambda: _save_config(app),
                color=SUCCESS, fg="#000").pack(side="left", padx=4)
    make_button(btn_row, "🔄  Aplicar defaults a todas las pestañas",
                lambda: _apply_defaults_to_tabs(app, silent=False),
                color=ACCENT, fg="#fff").pack(side="left", padx=4)
    make_button(btn_row, "↩  Restaurar valores de fábrica",
                lambda: _reset_to_defaults(app),
                color=WARN, fg="#000").pack(side="left", padx=4)

    # ── Separador visual ──────────────────────────────────────────────────────
    tk.Frame(inner, bg=BORDER, height=2).pack(fill="x", padx=20, pady=12)

    # ── 8. Estilos de la app ──────────────────────────────────────────────────
    make_title(inner, "🎨  Estilos de la Aplicación")

    frm_themes = make_labelframe(inner, "Seleccionar Tema Visual")
    frm_themes.pack(fill="x", padx=20, pady=8)
    make_label(frm_themes,
               "El tema se aplica en tiempo real y se guarda para la próxima sesión.",
               fg=TEXT2).pack(anchor="w", pady=(0, 6))

    cards_row = make_frame(frm_themes)
    cards_row.pack(anchor="w", pady=4)

    for key, theme in THEMES.items():
        _make_theme_card(cards_row, app, key, theme)

    app.cfg_theme_status = make_label(frm_themes, "", fg=SUCCESS)
    app.cfg_theme_status.pack(anchor="w", pady=(8, 2))

    # ── Cargar valores guardados en los widgets ───────────────────────────────
    _load_config_into_widgets(app)


# ── Tarjeta visual de tema ─────────────────────────────────────────────────────

def _make_theme_card(parent, app, theme_key: str, theme: dict):
    """Crea una tarjeta visual interactiva para un tema."""
    is_active = (theme_key == app.app_config.get('theme', 'github_dark'))
    border_color = theme['ACCENT'] if is_active else theme['BORDER']
    border_width = 3 if is_active else 1

    card = tk.Frame(parent, bg=theme['BG2'], relief="flat",
                    highlightthickness=border_width,
                    highlightbackground=border_color,
                    cursor="hand2")
    card.pack(side="left", padx=8, pady=4)

    # Barra de fondo (preview color principal)
    tk.Frame(card, bg=theme['BG'], height=6).pack(fill="x")

    # Muestras de color (swatches)
    sw_row = tk.Frame(card, bg=theme['BG2'])
    sw_row.pack(fill="x", padx=6, pady=3)
    for color in [theme['ACCENT'], theme['ACCENT2'], theme['SUCCESS'], theme['WARN']]:
        swatch = tk.Frame(sw_row, bg=color, width=16, height=16,
                          highlightthickness=0)
        swatch.pack(side="left", padx=1)
        swatch.pack_propagate(False)

    # Nombre del tema
    tk.Label(card, text=theme['name'], bg=theme['BG2'], fg=theme['TEXT'],
             font=("Consolas", 9, "bold"), padx=12, pady=2).pack()

    # Muestra de texto tipo IOS
    tk.Label(card, text=" 192.168.1.0/24 ", bg=theme['BG3'], fg=theme['ACCENT'],
             font=("Consolas", 8), padx=8, pady=2).pack(fill="x", padx=6, pady=(0, 4))

    # Muestra de log
    tk.Label(card, text=" ✔ SSH OK ", bg=theme['LOG_BG'], fg=theme['LOG_FG'],
             font=("Consolas", 8), padx=8, pady=2).pack(fill="x", padx=6, pady=(0, 4))

    # Botón aplicar
    tk.Button(
        card, text="Aplicar tema",
        bg=theme['ACCENT'], fg=theme['BG'],
        font=("Consolas", 8, "bold"),
        relief="flat", cursor="hand2", padx=8, pady=3,
        activebackground=theme['ACCENT2'], activeforeground=theme['BG'],
        command=lambda k=theme_key: _apply_theme(app, k),
    ).pack(fill="x", padx=6, pady=4)


# ── Lógica de configuración ────────────────────────────────────────────────────

def _apply_theme(app, theme_key: str):
    """Aplica el tema seleccionado y actualiza el estado."""
    switch_theme(app.root, theme_key, app)
    theme_name = THEMES[theme_key]['name']
    if hasattr(app, 'cfg_theme_status'):
        app.cfg_theme_status.configure(
            text=f"✔  Tema '{theme_name}' aplicado correctamente."
        )


def _load_config_into_widgets(app):
    """Rellena los widgets de la pestaña con los valores de app.app_config."""
    cfg = app.app_config

    def _set(widget, key):
        widget.delete(0, tk.END)
        widget.insert(0, cfg.get(key, ""))

    _set(app.cfg_empresa,        "empresa")
    _set(app.cfg_ssh_user,       "ssh_user")
    _set(app.cfg_ssh_port,       "ssh_port")
    _set(app.cfg_ssh_timeout,    "ssh_timeout")
    _set(app.cfg_uplink,         "uplink_iface")
    _set(app.cfg_dns1,           "dhcp_dns1")
    _set(app.cfg_dns2,           "dhcp_dns2")
    _set(app.cfg_dhcp_mask,      "dhcp_mask")
    _set(app.cfg_ospf_pid,       "ospf_pid")
    _set(app.cfg_ospf_area,      "ospf_area")
    _set(app.cfg_login_attempts, "login_attempts")
    _set(app.cfg_login_window,   "login_window")
    _set(app.cfg_login_block,    "login_block")
    _set(app.cfg_s3_region,      "s3_region")
    _set(app.cfg_s3_bucket,      "s3_bucket")
    _set(app.cfg_s3_prefix,      "s3_prefix")

    # ScrolledText para banner
    app.cfg_banner.delete("1.0", tk.END)
    app.cfg_banner.insert("1.0", cfg.get("banner_motd", ""))


def _save_config(app):
    """Lee los widgets, actualiza app.app_config y persiste en JSON."""
    cfg = app.app_config

    cfg["empresa"]        = app.cfg_empresa.get().strip()
    cfg["ssh_user"]       = app.cfg_ssh_user.get().strip()
    cfg["ssh_port"]       = app.cfg_ssh_port.get().strip()
    cfg["ssh_timeout"]    = app.cfg_ssh_timeout.get().strip()
    cfg["uplink_iface"]   = app.cfg_uplink.get().strip()
    cfg["dhcp_dns1"]      = app.cfg_dns1.get().strip()
    cfg["dhcp_dns2"]      = app.cfg_dns2.get().strip()
    cfg["dhcp_mask"]      = app.cfg_dhcp_mask.get().strip()
    cfg["ospf_pid"]       = app.cfg_ospf_pid.get().strip()
    cfg["ospf_area"]      = app.cfg_ospf_area.get().strip()
    cfg["login_attempts"] = app.cfg_login_attempts.get().strip()
    cfg["login_window"]   = app.cfg_login_window.get().strip()
    cfg["login_block"]    = app.cfg_login_block.get().strip()
    cfg["banner_motd"]    = app.cfg_banner.get("1.0", tk.END).strip()
    cfg["s3_region"]      = app.cfg_s3_region.get().strip()
    cfg["s3_bucket"]      = app.cfg_s3_bucket.get().strip()
    cfg["s3_prefix"]      = app.cfg_s3_prefix.get().strip()

    # Actualizar UPLINK_IFACE en el módulo constants (sesión actual)
    if cfg["uplink_iface"]:
        constants.UPLINK_IFACE = cfg["uplink_iface"]

    # Actualizar título con nombre de empresa
    if cfg["empresa"]:
        from constants import APP_VERSION
        app.root.title(f"Configurador IOSvL2 — {APP_VERSION}  |  {cfg['empresa']}")
    else:
        from constants import APP_VERSION
        app.root.title(f"Configurador IOSvL2 — {APP_VERSION}")

    save_config(cfg)
    messagebox.showinfo("Guardado", "✔  Configuración guardada.\n"
                        "Usa '🔄 Aplicar defaults' para rellenar las demás pestañas.")


def _apply_defaults_to_tabs(app, silent: bool = False):
    """
    Pre-rellena los campos vacíos de las otras pestañas con los defaults guardados.

    silent=True  → no pide confirmación (usado al inicio de la app).
    silent=False → pregunta antes de sobrescribir.
    """
    cfg = app.app_config

    if not silent:
        if not messagebox.askyesno(
            "Aplicar defaults",
            "¿Rellenar los campos de las demás pestañas\n"
            "con los valores por defecto configurados?\n\n"
            "(Solo se sobreescriben los campos indicados)"
        ):
            return

    def _fill(widget, value, only_if_empty=not silent):
        """Rellena un Entry, opcionalmente solo si está vacío."""
        if value:
            if only_if_empty and widget.get().strip():
                return
            widget.delete(0, tk.END)
            widget.insert(0, value)

    def _fill_text(widget, value, only_if_empty=not silent):
        """Rellena un Text/ScrolledText."""
        if value:
            if only_if_empty and widget.get("1.0", tk.END).strip():
                return
            widget.delete("1.0", tk.END)
            widget.insert("1.0", value)

    # Tab ① — usuario SSH
    if hasattr(app, 'sw_user'):
        _fill(app.sw_user, cfg.get("ssh_user"))

    # Tab ② — máscara DHCP
    if hasattr(app, 'dhcp_mask'):
        _fill(app.dhcp_mask, cfg.get("dhcp_mask"))

    # Tab ④ — OSPF PID y área
    if hasattr(app, 'ospf_pid'):
        _fill(app.ospf_pid, cfg.get("ospf_pid"))
    if hasattr(app, 'ospf_area'):
        _fill(app.ospf_area, cfg.get("ospf_area"))

    # Tab ⑦ — S3
    if hasattr(app, 's3_region'):
        _fill(app.s3_region, cfg.get("s3_region"))
    if hasattr(app, 's3_bucket'):
        _fill(app.s3_bucket, cfg.get("s3_bucket"))
    if hasattr(app, 's3_prefix'):
        _fill(app.s3_prefix, cfg.get("s3_prefix"))

    # Tab ⑧ — Login block-for
    if hasattr(app, 'sec_login_attempts'):
        _fill(app.sec_login_attempts, cfg.get("login_attempts"))
    if hasattr(app, 'sec_login_window'):
        _fill(app.sec_login_window,   cfg.get("login_window"))
    if hasattr(app, 'sec_login_block'):
        _fill(app.sec_login_block,    cfg.get("login_block"))

    # Tab ⑧ — Banner MOTD
    if hasattr(app, 'sec_banner_text'):
        _fill_text(app.sec_banner_text, cfg.get("banner_motd"))

    if not silent:
        messagebox.showinfo("Defaults aplicados",
                            "✔  Valores por defecto aplicados a las pestañas.")


def _reset_to_defaults(app):
    """Restaura los valores de fábrica en los widgets (no guarda hasta confirmar)."""
    if not messagebox.askyesno("Restaurar valores de fábrica",
                               "¿Restaurar TODOS los valores de configuración\n"
                               "a los valores de fábrica?"):
        return
    app.app_config = dict(DEFAULT_CONFIG)
    _load_config_into_widgets(app)
    messagebox.showinfo("Restaurado",
                        "Valores de fábrica restaurados.\nPresiona 'Guardar' para persistirlos.")
