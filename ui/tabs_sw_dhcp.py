"""
ui/tabs_sw_dhcp.py — Pestañas: ① Sucursales  y  ② DHCP
=========================================================
Pestaña ①: Alta, prueba y eliminación de sucursales (switches).
Pestaña ②: Definición de pools DHCP que se asignarán a las VLANs.

Ambas pestañas solo manejan datos en memoria (listas de dicts).
La conexión real al switch ocurre en core/connector.py.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import tkinter as tk
from tkinter import ttk, messagebox

from constants import BG2, SUCCESS, WARN, ACCENT2, TEXT2, BG3, UPLINK_IFACE
from ui.widgets import (
    make_frame, make_label, make_entry, make_button,
    make_listbox, make_labelframe, make_title,
)
from core.connector import test_connection
from ui.validators import is_valid_ip, is_valid_mask, ip_in_network


# ═══════════════════════════════════════════════════════════════════════════════
#  PESTAÑA ① — SUCURSALES
# ═══════════════════════════════════════════════════════════════════════════════

def build_tab_sw(app, parent):
    """
    Construye la pestaña de Sucursales en el frame 'parent'.

    Widgets creados (guardados en 'app'):
      - app.sw_name, sw_ip, sw_user, sw_pass, sw_secret : campos del formulario
      - app.sw_listbox    : lista de sucursales agregadas
      - app.detection_lbl : etiqueta de estado de la detección L2/L3
    """
    make_title(parent, "⚙  Sucursales / Switches")

    top = make_frame(parent)
    top.pack(fill="x", padx=16, pady=6)

    # ── Información de política de conexión ───────────────────────────────────
    info = make_labelframe(top, "Política de conexión")
    info.pack(fill="x", pady=4)
    make_label(info, (
        f"✔  Interfaz de gestión/uplink protegida: {UPLINK_IFACE}  (nunca se modifica)\n"
        "✔  SSH, usuarios, VTY y crypto key NUNCA se tocan.\n"
        "✔  Al conectar se auto-detecta si el switch es Layer 2 o Layer 3.\n"
        "✔  La misma config DHCP/VLANs/QoS se aplica a cada sucursal seleccionada."
    ), fg=SUCCESS).pack(anchor="w")

    # ── Formulario de nueva sucursal ──────────────────────────────────────────
    fadd = make_labelframe(top, "Agregar sucursal")
    fadd.pack(fill="x", pady=6)

    r = make_frame(fadd)
    r.pack(fill="x", pady=4)

    # Fila 0: Nombre, IP, Usuario
    row0_fields = [
        ("Nombre/ID:",     "sw_name",   16, ""),
        ("IP de gestión:", "sw_ip",     18, ""),
        ("Usuario SSH:",   "sw_user",   14, "admin"),
    ]
    for col, (lbl_txt, attr, w, default) in enumerate(row0_fields):
        make_label(r, lbl_txt).grid(row=0, column=col*2, sticky="e", padx=6, pady=4)
        e = make_entry(r, width=w)
        if default:
            e.insert(0, default)
        e.grid(row=0, column=col*2+1, padx=4, pady=4)
        setattr(app, attr, e)

    # Fila 1: Contraseña, Enable Secret (ocultas con '*')
    row1_fields = [
        ("Contraseña:",    "sw_pass",   18, ""),
        ("Enable Secret:", "sw_secret", 18, ""),
    ]
    for col, (lbl_txt, attr, w, default) in enumerate(row1_fields):
        make_label(r, lbl_txt).grid(row=1, column=col*2, sticky="e", padx=6, pady=4)
        e = make_entry(r, width=w, show="*")
        if default:
            e.insert(0, default)
        e.grid(row=1, column=col*2+1, padx=4, pady=4)
        setattr(app, attr, e)

    # ── Botones de acción ─────────────────────────────────────────────────────
    btn_row = make_frame(fadd)
    btn_row.pack(anchor="w", pady=4)
    make_button(btn_row, "＋  Agregar sucursal",
                lambda: _add_sucursal(app),
                color=SUCCESS, fg=BG2).pack(side="left", padx=4)
    make_button(btn_row, "🔌  Probar conexión",
                lambda: _test_selected(app),
                color=BG3).pack(side="left", padx=4)
    make_button(btn_row, "✕  Eliminar seleccionada",
                lambda: _remove_sucursal(app),
                color="#6e2020").pack(side="left", padx=4)

    # ── Lista de sucursales ───────────────────────────────────────────────────
    flist = make_labelframe(top, "Sucursales configuradas  (selecciona las que quieres aplicar)")
    flist.pack(fill="x", pady=4)
    app.sw_listbox = make_listbox(flist, width=90, height=6)
    app.sw_listbox.pack(pady=4)
    make_label(flist,
               "Ctrl+clic para seleccionar múltiples. 'Aplicar config' se envía a todas las seleccionadas.",
               fg=TEXT2).pack(anchor="w")

    # ── Etiqueta de estado de detección L2/L3 ────────────────────────────────
    app.detection_lbl = make_label(
        top,
        "Capa detectada: — (usa 'Probar conexión' para detectar)",
        fg=TEXT2,
    )
    app.detection_lbl.pack(anchor="w", padx=4, pady=4)


def _add_sucursal(app):
    """Valida el formulario y agrega la sucursal a la lista en memoria."""
    sw = {k: getattr(app, f"sw_{k}").get().strip()
          for k in ('name', 'ip', 'user', 'pass', 'secret')}
    if not all([sw['name'], sw['ip'], sw['user'], sw['pass'], sw['secret']]):
        messagebox.showwarning("Incompleto", "Completa todos los campos.")
        return
    if not is_valid_ip(sw['ip']):
        messagebox.showerror("IP inválida",
            f"'{sw['ip']}' no es una dirección IPv4 válida.\nEjemplo: 192.168.1.10")
        return
    # Evitar duplicados por IP
    if any(s['ip'] == sw['ip'] for s in app.sucursales):
        messagebox.showwarning("Duplicado",
            f"Ya existe una sucursal con la IP {sw['ip']}.")
        return
    app.sucursales.append(sw)
    app.sw_listbox.insert(
        tk.END,
        f"  [{len(app.sucursales)-1}]  {sw['name']:18}  {sw['ip']:18}  user:{sw['user']}"
    )
    # Limpiar formulario (excepto usuario, que suele ser siempre el mismo)
    for k in ('name', 'ip', 'pass', 'secret'):
        getattr(app, f"sw_{k}").delete(0, tk.END)


def _remove_sucursal(app):
    """Elimina la sucursal seleccionada de la lista."""
    sel = app.sw_listbox.curselection()
    if sel:
        app.sw_listbox.delete(sel[0])
        app.sucursales.pop(sel[0])


def _test_selected(app):
    """
    Prueba la conexión SSH a la sucursal seleccionada y detecta Layer 2/3.
    Actualiza la etiqueta de estado con el resultado.
    """
    sel = app.sw_listbox.curselection()
    if not sel:
        messagebox.showwarning("Selección", "Selecciona una sucursal de la lista.")
        return
    sw = app.sucursales[sel[0]]
    app.detection_lbl.config(text=f"Conectando a {sw['ip']}...", fg=WARN)
    app.root.update()   # forzar redibujado antes del bloqueo de red
    try:
        result = test_connection(sw)
        layer  = ("Layer 3 ✔ (ip routing activo)"
                  if result['is_l3'] else "Layer 2 (sin ip routing)")
        app.detection_lbl.config(
            text=f"✔  '{result['hostname']}'  |  {layer}  |  {result['ver_out']}",
            fg=SUCCESS,
        )
        app.detected_l3 = result['is_l3']
    except Exception as e:
        app.detection_lbl.config(text=f"✘  Error: {str(e)[:90]}", fg=ACCENT2)


# ═══════════════════════════════════════════════════════════════════════════════
#  PESTAÑA ② — DHCP
# ═══════════════════════════════════════════════════════════════════════════════

def build_tab_dhcp(app, parent):
    """
    Construye la pestaña de DHCP en el frame 'parent'.

    Cada pool DHCP define:
      - Red y máscara → rango de IPs a asignar
      - Gateway → IP de la SVI en el switch L3 (se excluye del pool)

    Widgets creados en 'app':
      - app.dhcp_name, dhcp_net, dhcp_mask, dhcp_gw : campos del formulario
      - app.dhcp_listbox : lista de pools definidos
    """
    make_title(parent, "⚙  Pools DHCP")
    f = make_frame(parent)
    f.pack(pady=6)

    # Formulario de nuevo pool
    form_fields = [
        ("Nombre del Pool:",       "dhcp_name"),
        ("Red (ej.192.168.10.0):", "dhcp_net"),
        ("Máscara:",               "dhcp_mask"),
        ("Gateway / IP SVI:",      "dhcp_gw"),
    ]
    for row, (lbl_txt, attr) in enumerate(form_fields):
        make_label(f, lbl_txt).grid(row=row, column=0, sticky="e", pady=3, padx=6)
        e = make_entry(f)
        e.grid(row=row, column=1, padx=6, pady=3)
        setattr(app, attr, e)

    make_label(f, "* El gateway se excluye automáticamente del pool DHCP",
               fg=TEXT2).grid(row=4, columnspan=2, pady=2)
    make_button(f, "＋  Agregar Pool",
                lambda: _add_dhcp(app),
                color=SUCCESS, fg=BG2).grid(row=5, columnspan=2, pady=8)

    # Lista de pools
    app.dhcp_listbox = make_listbox(parent, width=76, height=8)
    app.dhcp_listbox.pack(padx=16, pady=4)
    make_button(parent, "✕  Eliminar seleccionado",
                lambda: _remove_dhcp(app),
                color="#6e2020").pack(pady=2)


def _add_dhcp(app):
    """Valida y agrega un nuevo pool DHCP a la lista en memoria."""
    pool = {k: getattr(app, f"dhcp_{k}").get().strip()
            for k in ('name', 'net', 'mask', 'gw')}
    if not all(pool.values()):
        messagebox.showwarning("Faltan datos", "Completa todos los campos DHCP.")
        return
    if not is_valid_ip(pool['net']):
        messagebox.showerror("Red inválida",
            f"'{pool['net']}' no es una dirección IPv4 válida.\nEjemplo: 192.168.10.0")
        return
    if not is_valid_mask(pool['mask']):
        messagebox.showerror("Máscara inválida",
            f"'{pool['mask']}' no es una máscara de subred válida.\nEjemplo: 255.255.255.0")
        return
    if not is_valid_ip(pool['gw']):
        messagebox.showerror("Gateway inválido",
            f"'{pool['gw']}' no es una dirección IPv4 válida.\nEjemplo: 192.168.10.1")
        return
    if not ip_in_network(pool['gw'], pool['net'], pool['mask']):
        messagebox.showerror("Gateway fuera de red",
            f"El gateway {pool['gw']} no pertenece a la red "
            f"{pool['net']} / {pool['mask']}.")
        return
    if any(p['name'] == pool['name'] for p in app.dhcp_pools):
        messagebox.showwarning("Duplicado",
            f"Ya existe un pool DHCP con el nombre '{pool['name']}'.")
        return
    app.dhcp_pools.append(pool)
    app.dhcp_listbox.insert(
        tk.END,
        f"  {pool['name']:18} {pool['net']:18} {pool['mask']:18} GW:{pool['gw']}"
    )
    for k in ('name', 'net', 'mask', 'gw'):
        getattr(app, f"dhcp_{k}").delete(0, tk.END)


def _remove_dhcp(app):
    """Elimina el pool DHCP seleccionado de la lista."""
    sel = app.dhcp_listbox.curselection()
    if sel:
        app.dhcp_listbox.delete(sel[0])
        app.dhcp_pools.pop(sel[0])


def get_dhcp_options(app) -> list:
    """
    Retorna las opciones del combo de pools DHCP en formato 'índice: nombre'.
    Usado por la pestaña de VLANs para vincular un pool a una VLAN.
    """
    return [f"{i}: {p['name']}" for i, p in enumerate(app.dhcp_pools)] or ["(sin pools)"]
