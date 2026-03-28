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
from ui.preview_window import show_preview


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
      - IPs adicionales a excluir (lista, opcional)

    Widgets creados en 'app':
      - app.dhcp_name, dhcp_net, dhcp_mask, dhcp_gw : campos del formulario
      - app.dhcp_excl_entry    : campo para ingresar IPs a excluir
      - app.dhcp_excl_listbox  : lista temporal de IPs a excluir del pool actual
      - app.dhcp_excl_pending  : lista en memoria de IPs pendientes para el pool actual
      - app.dhcp_listbox       : lista de pools definidos
    """
    make_title(parent, "⚙  Pools DHCP")

    # ── Contenedor principal en dos columnas ──────────────────────────────────
    main = make_frame(parent)
    main.pack(pady=6, padx=16, fill="x")

    # Columna izquierda: campos base del pool
    f = make_frame(main)
    f.grid(row=0, column=0, sticky="n", padx=(0, 20))

    form_fields = [
        ("Nombre del Pool:",          "dhcp_name"),
        ("Red (ej.192.168.10.0):",    "dhcp_net"),
        ("Máscara:",                  "dhcp_mask"),
        ("Gateway / IP SVI:",         "dhcp_gw"),
    ]
    for row, (lbl_txt, attr) in enumerate(form_fields):
        make_label(f, lbl_txt).grid(row=row, column=0, sticky="e", pady=3, padx=6)
        e = make_entry(f)
        e.grid(row=row, column=1, padx=6, pady=3)
        setattr(app, attr, e)

    make_label(f, "* El gateway se excluye automáticamente",
               fg=TEXT2).grid(row=4, columnspan=2, pady=2)
    make_button(f, "＋  Agregar Pool",
                lambda: _add_dhcp(app),
                color=SUCCESS, fg=BG2).grid(row=5, columnspan=2, pady=8)

    # Columna derecha: IPs adicionales a excluir
    fexcl = make_labelframe(main, "IPs adicionales a excluir  (opcional)")
    fexcl.grid(row=0, column=1, sticky="n")

    app.dhcp_excl_pending = []

    excl_row = make_frame(fexcl)
    excl_row.pack(fill="x", pady=4)
    app.dhcp_excl_entry = make_entry(excl_row, width=18)
    app.dhcp_excl_entry.pack(side="left", padx=4)
    make_button(excl_row, "＋ Agregar IP",
                lambda: _add_excl_ip(app),
                color=BG3).pack(side="left", padx=4)

    app.dhcp_excl_listbox = make_listbox(fexcl, width=24, height=5)
    app.dhcp_excl_listbox.pack(padx=4, pady=2)
    make_button(fexcl, "✕ Quitar seleccionada",
                lambda: _remove_excl_ip(app),
                color="#6e2020").pack(pady=2)

    # Lista de pools definidos
    app.dhcp_listbox = make_listbox(parent, width=76, height=8)
    app.dhcp_listbox.pack(padx=16, pady=4)

    btn_row = make_frame(parent)
    btn_row.pack(pady=2)
    make_button(btn_row, "✕  Eliminar seleccionado",
                lambda: _remove_dhcp(app),
                color="#6e2020").pack(side="left", padx=6)
    make_button(btn_row, "👁  Ver comandos IOS",
                lambda: _preview_dhcp(app),
                color=BG3).pack(side="left", padx=6)


def _add_excl_ip(app):
    """Agrega una IP a la lista temporal de exclusiones del pool en construcción."""
    ip = app.dhcp_excl_entry.get().strip()
    if not ip:
        return
    if not is_valid_ip(ip):
        messagebox.showerror("IP inválida",
            f"'{ip}' no es una dirección IPv4 válida.\nEjemplo: 192.168.10.100")
        return
    if ip in app.dhcp_excl_pending:
        messagebox.showwarning("Duplicado", f"La IP {ip} ya está en la lista.")
        return
    app.dhcp_excl_pending.append(ip)
    app.dhcp_excl_listbox.insert(tk.END, f"  {ip}")
    app.dhcp_excl_entry.delete(0, tk.END)


def _remove_excl_ip(app):
    """Quita la IP seleccionada de la lista temporal de exclusiones."""
    sel = app.dhcp_excl_listbox.curselection()
    if sel:
        app.dhcp_excl_listbox.delete(sel[0])
        app.dhcp_excl_pending.pop(sel[0])


def _add_dhcp(app):
    """Valida y agrega un nuevo pool DHCP a la lista en memoria."""
    pool = {k: getattr(app, f"dhcp_{k}").get().strip()
            for k in ('name', 'net', 'mask', 'gw')}
    # ── 1. Campos obligatorios ────────────────────────────────────────────────
    if not all(pool.values()):
        messagebox.showwarning("Faltan datos", "Completa todos los campos DHCP.")
        return
    # ── 2. Validaciones de formato ────────────────────────────────────────────
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
    # ── 3. Agregar a memoria y UI ─────────────────────────────────────────────
    pool['excludes'] = list(app.dhcp_excl_pending)
    app.dhcp_pools.append(pool)
    excl_info = (f"  [{len(pool['excludes'])} excluidas]" if pool['excludes'] else "")
    app.dhcp_listbox.insert(
        tk.END,
        f"  {pool['name']:18} {pool['net']:18} {pool['mask']:18} GW:{pool['gw']}{excl_info}"
    )
    for k in ('name', 'net', 'mask', 'gw'):
        getattr(app, f"dhcp_{k}").delete(0, tk.END)
    app.dhcp_excl_pending.clear()
    app.dhcp_excl_listbox.delete(0, tk.END)


def _remove_dhcp(app):
    """Elimina el pool DHCP seleccionado de la lista."""
    sel = app.dhcp_listbox.curselection()
    if sel:
        app.dhcp_listbox.delete(sel[0])
        app.dhcp_pools.pop(sel[0])


def _preview_dhcp(app):
    """Muestra la vista previa de los comandos DHCP que se generarán."""
    from core.command_builder import build_commands
    cmds = build_commands(
        is_l3=True, chk_intervlan=True,
        dhcp_pools=app.dhcp_pools,
        vlans_data=[], static_routes=[],
        chk_ospf=False, ospf_pid="1", ospf_networks=[],
        qos_classes=[], pol_entries=[], pol_name="", service_policies=[],
        dns1=app.app_config.get('dhcp_dns1', ''),
        dns2=app.app_config.get('dhcp_dns2', ''),
    )
    show_preview(
        app.root, "DHCP — Pools y exclusiones", cmds,
        note="Solo aplica en switches L3 (ip routing activo).",
    )


def get_dhcp_options(app) -> list:
    """
    Retorna las opciones del combo de pools DHCP en formato 'índice: nombre'.
    Usado por la pestaña de VLANs para vincular un pool a una VLAN.
    """
    return [f"{i}: {p['name']}" for i, p in enumerate(app.dhcp_pools)] or ["(sin pools)"]
