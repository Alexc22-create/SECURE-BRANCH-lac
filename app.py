"""
app.py — Clase principal de la aplicación
==========================================
Orquesta todas las pestañas y mantiene el estado global de la aplicación.

CÓMO EJECUTAR:
  Desde la carpeta switch_configurator/:
    source env/bin/activate
    python app.py

Estructura de módulos:
  app.py                      ← Este archivo: clase principal + punto de entrada
  constants.py                ← Colores, versión, UPLINK_IFACE, DSCP_PRESETS, THEMES
  core/
    command_builder.py        ← Generación de comandos IOS (sin GUI)
    connector.py              ← Conexión SSH, detección L2/L3, envío de comandos
  ui/
    widgets.py                ← Fábrica de widgets Tkinter estilizados
    tabs_sw_dhcp.py           ← Pestañas ① Sucursales y ② DHCP
    tab_vlan.py               ← Pestaña ③ VLANs y Puertos
    tab_routing.py            ← Pestaña ④ Enrutamiento (rutas + OSPF)
    tab_qos.py                ← Pestaña ⑤ QoS MQC
    tab_exec_backup.py        ← Pestañas ⑥ Ejecución y ⑦ Backup (incluye AWS S3)
    tab_security_gre.py       ← Pestañas ⑧ Seguridad y ⑨ GRE over IPsec
    tab_config.py             ← Pestaña ⑩ Configuración de Empresa y Estilos
"""

import sys
import os

# Asegura que Python encuentre ui/, core/ y constants.py
# sin importar desde qué directorio se ejecute el script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk

from constants import APP_VERSION
from ui.widgets import apply_style, switch_theme
from ui.tabs_sw_dhcp    import build_tab_sw, build_tab_dhcp
from ui.tab_vlan        import build_tab_vlan
from ui.tab_routing     import build_tab_routing
from ui.tab_qos         import build_tab_qos
from ui.tab_exec_backup import build_tab_exec, build_tab_backup
from ui.tab_security_gre import build_tab_security, build_tab_gre
from ui.tab_config      import build_tab_config, load_config, _apply_defaults_to_tabs


class SwitchConfiguratorV2:
    """
    Clase principal que agrupa el estado global y construye la ventana.

    Estado global (listas de dicts en memoria):
      sucursales      : switches que la app puede configurar
      dhcp_pools      : pools DHCP definidos
      vlans_data      : VLANs con sus puertos, DHCP y ACLs
      static_routes   : rutas estáticas
      ospf_networks   : redes a anunciar por OSPF
      qos_classes     : class-maps de QoS
      pol_entries     : entradas de la policy-map
      service_policies: aplicaciones de service-policy a interfaces
      gre_tunnels     : configuraciones de túneles GRE over IPsec (v2.2)
      detected_l3     : último resultado de detección L2/L3 (puede ser None)
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Configurador IOSvL2 — {APP_VERSION}")
        self.root.geometry("980x800")
        self.root.configure(bg="#0d1117")
        self.root.resizable(True, True)

        # Cargar configuración persistente antes de construir los widgets
        self.app_config = load_config()

        # Aplicar tema visual global (colores, fuentes, bordes)
        apply_style(root)

        # ── Estado global ──────────────────────────────────────────────────────
        self.sucursales       = []
        self.dhcp_pools       = []
        self.vlans_data       = []
        self.static_routes    = []
        self.ospf_networks    = []
        self.qos_classes      = []
        self.pol_entries      = []
        self.service_policies = []
        self.gre_tunnels      = []   # túneles GRE over IPsec (v2.2)
        self.detected_l3      = None  # True=L3 / False=L2 / None=no detectado aún

        # ── Crear notebook de pestañas ─────────────────────────────────────────
        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True, padx=8, pady=8)
        self.notebook = nb

        # Definir pestañas: (nombre del atributo, etiqueta visible)
        tabs = [
            ("tab_sw",       "① Sucursales"),
            ("tab_dhcp",     "② DHCP"),
            ("tab_vlan",     "③ VLANs y Puertos"),
            ("tab_routing",  "④ Enrutamiento"),
            ("tab_qos",      "⑤ QoS MQC"),
            ("tab_exec",     "⑥ Ejecución"),
            ("tab_backup",   "⑦ Backup"),
            ("tab_security", "⑧ Seguridad"),
            ("tab_gre",      "⑨ GRE/IPsec"),
            ("tab_config",   "⚙ Configuración"),
        ]
        for attr, label in tabs:
            frame = ttk.Frame(nb)
            nb.add(frame, text=label)
            setattr(self, attr, frame)

        # ── Construir contenido de cada pestaña ────────────────────────────────
        # Cada función recibe 'self' (app) y el frame de la pestaña.
        # Los widgets se guardan como atributos de 'self' (ej: self.sw_listbox).
        build_tab_sw(self,       self.tab_sw)
        build_tab_dhcp(self,     self.tab_dhcp)
        build_tab_vlan(self,     self.tab_vlan)
        build_tab_routing(self,  self.tab_routing)
        build_tab_qos(self,      self.tab_qos)
        build_tab_exec(self,     self.tab_exec)
        build_tab_backup(self,   self.tab_backup)
        build_tab_security(self, self.tab_security)
        build_tab_gre(self,      self.tab_gre)
        build_tab_config(self,   self.tab_config)

        # ── Aplicar configuración guardada al arranque ─────────────────────────
        # 1. Pre-rellenar campos vacíos de otras pestañas con defaults guardados.
        _apply_defaults_to_tabs(self, silent=True)

        # 2. Aplicar el tema guardado (si no es el default ya aplicado).
        saved_theme = self.app_config.get('theme', 'github_dark')
        if saved_theme != 'github_dark':
            switch_theme(root, saved_theme, self)

        # 3. Actualizar título con nombre de empresa (si hay uno guardado).
        empresa = self.app_config.get('empresa', '')
        if empresa:
            self.root.title(f"Configurador IOSvL2 — {APP_VERSION}  |  {empresa}")


# ── Punto de entrada ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = SwitchConfiguratorV2(root)
    root.mainloop()
