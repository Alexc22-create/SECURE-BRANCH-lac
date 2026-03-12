"""
ui/tab_routing.py — Pestaña ④: Enrutamiento
=============================================
Permite configurar:
  - Inter-VLAN routing (ip routing en switches L3)
  - Rutas estáticas (incluyendo ruta por defecto hacia R1)
  - OSPF para anunciar las subredes de VLANs a R1 (necesario para NAT/internet)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import tkinter as tk
from tkinter import ttk, messagebox

from constants import BG3, SUCCESS, TEXT2
from ui.widgets import (
    make_frame, make_label, make_entry, make_button,
    make_listbox, make_labelframe, make_title, make_scrolled_frame,
)


def build_tab_routing(app, parent):
    """
    Construye la pestaña de Enrutamiento.

    Widgets creados en 'app':
      - app.chk_intervlan            : checkbox "Activar ip routing"
      - app.rt_dest, rt_mask, rt_nh  : campos de rutas estáticas
      - app.default_nh               : campo de IP next-hop para ruta por defecto
      - app.rt_listbox               : lista de rutas estáticas
      - app.chk_ospf                 : checkbox "Habilitar OSPF"
      - app.ospf_net, ospf_wild, ospf_area, ospf_pid : campos OSPF
      - app.ospf_listbox             : lista de redes OSPF
    """
    make_title(parent, "⚙  Enrutamiento")
    sf = make_scrolled_frame(parent)

    # ── Inter-VLAN Routing ────────────────────────────────────────────────────
    # "ip routing" convierte el switch en un router L3.
    # En switches L2 detectados automáticamente, este bloque se omite.
    fiv = make_labelframe(sf, "Inter-VLAN Routing (solo switches L3)")
    fiv.pack(fill="x", padx=12, pady=6)
    app.chk_intervlan = tk.BooleanVar(value=True)
    ttk.Checkbutton(fiv,
                    text="Activar 'ip routing' — permite comunicación entre VLANs vía SVI",
                    variable=app.chk_intervlan).pack(anchor="w")
    make_label(fiv,
               "En switches L2 (detectados sin ip routing), este comando se omite automáticamente.",
               fg=TEXT2).pack(anchor="w")

    # ── Rutas Estáticas ───────────────────────────────────────────────────────
    fst = make_labelframe(sf, "Rutas Estáticas")
    fst.pack(fill="x", padx=12, pady=6)
    make_label(fst,
               "Ruta por defecto → R1 para salir a internet. O rutas entre sucursales.",
               fg=TEXT2).pack(anchor="w")

    frm = make_frame(fst); frm.pack(fill="x", pady=4)
    for col, (lbl_txt, attr, w) in enumerate([
        ("Destino:", "rt_dest", 16),
        ("Máscara:", "rt_mask", 16),
        ("Next-hop:", "rt_nh",  16),
    ]):
        make_label(frm, lbl_txt).grid(row=0, column=col*2, sticky="e", padx=4)
        e = make_entry(frm, width=w)
        e.grid(row=0, column=col*2+1, padx=4)
        setattr(app, attr, e)

    bf = make_frame(fst); bf.pack(anchor="w", pady=4)
    make_button(bf, "＋  Agregar ruta",
                lambda: _add_static_route(app)).pack(side="left", padx=4)

    # Atajo para agregar ruta por defecto (0.0.0.0/0) con next-hop configurable
    defr = make_frame(fst); defr.pack(anchor="w", pady=(2, 4))
    make_label(defr, "⚡  Ruta por defecto (0.0.0.0/0) → Next-hop:").pack(side="left", padx=4)
    app.default_nh = make_entry(defr, width=16)
    app.default_nh.insert(0, "10.255.255.1")   # IP común del gateway R1
    app.default_nh.pack(side="left", padx=4)
    make_button(defr, "Agregar ruta por defecto",
                lambda: _add_default_route(app),
                color=BG3).pack(side="left", padx=4)
    make_label(defr, "← IP del gateway de R1 hacia este switch",
               fg=TEXT2).pack(side="left", padx=4)

    app.rt_listbox = make_listbox(fst, width=76, height=4)
    app.rt_listbox.pack(pady=4)
    make_button(fst, "✕  Eliminar",
                lambda: _remove_static_route(app),
                color="#6e2020").pack(anchor="w")

    # ── OSPF ──────────────────────────────────────────────────────────────────
    # OSPF permite que R1 aprenda las rutas de las nuevas VLANs automáticamente.
    # Sin esto, R1 no sabe hacia dónde hacer NAT para las subredes del switch.
    fosp = make_labelframe(sf, "OSPF — Anunciar subredes a R1")
    fosp.pack(fill="x", padx=12, pady=6)
    make_label(fosp,
               "Necesario para que R1 haga NAT a las nuevas VLANs. Sin esto no hay internet.",
               fg=TEXT2).pack(anchor="w")

    app.chk_ospf = tk.BooleanVar()
    ttk.Checkbutton(fosp, text="Habilitar OSPF",
                    variable=app.chk_ospf,
                    command=lambda: _toggle_ospf(app)).pack(anchor="w")

    app.ospf_frame = make_frame(fosp)
    app.ospf_frame.pack(fill="x")

    ofrm = make_frame(app.ospf_frame); ofrm.pack(fill="x", pady=4)
    for col, (lbl_txt, attr, w, default) in enumerate([
        ("Red:",       "ospf_net",  16, ""),
        ("Wildcard:",  "ospf_wild", 16, ""),
        ("Área:",      "ospf_area",  6, "0"),
        ("PID:",       "ospf_pid",   5, "1"),
    ]):
        make_label(ofrm, lbl_txt).grid(row=0, column=col*2, sticky="e", padx=4)
        e = make_entry(ofrm, width=w, state="disabled")   # deshabilitado hasta activar OSPF
        if default:
            e.insert(0, default)
        e.grid(row=0, column=col*2+1, padx=4)
        setattr(app, attr, e)

    obf = make_frame(app.ospf_frame); obf.pack(anchor="w", pady=4)
    make_button(obf, "＋  Agregar red",
                lambda: _add_ospf_network(app)).pack(side="left", padx=4)
    make_button(obf, "⚡  Auto desde pools DHCP",
                lambda: _auto_ospf_from_pools(app),
                color=BG3).pack(side="left", padx=4)

    app.ospf_listbox = make_listbox(app.ospf_frame, width=76, height=4)
    app.ospf_listbox.pack(pady=4)
    make_button(app.ospf_frame, "✕  Eliminar",
                lambda: _remove_ospf_network(app),
                color="#6e2020").pack(anchor="w")


# ── Handlers internos ──────────────────────────────────────────────────────────

def _toggle_ospf(app):
    """Habilita/deshabilita los campos OSPF según el checkbox."""
    s = "normal" if app.chk_ospf.get() else "disabled"
    for a in ('ospf_net', 'ospf_wild', 'ospf_area', 'ospf_pid'):
        getattr(app, a).config(state=s)


def _add_static_route(app):
    """Agrega una ruta estática manual a la lista."""
    d = app.rt_dest.get().strip()
    m = app.rt_mask.get().strip()
    n = app.rt_nh.get().strip()
    if not all([d, m, n]):
        messagebox.showwarning("Incompleto", "Completa los 3 campos.")
        return
    app.static_routes.append({'dest': d, 'mask': m, 'nexthop': n})
    app.rt_listbox.insert(tk.END, f"  ip route {d} {m} {n}")
    app.rt_dest.delete(0, tk.END)
    app.rt_mask.delete(0, tk.END)
    app.rt_nh.delete(0, tk.END)


def _add_default_route(app):
    """
    Agrega la ruta por defecto (0.0.0.0/0) con el next-hop indicado.
    Si ya existe una ruta por defecto, pregunta si reemplazarla.
    """
    nh = app.default_nh.get().strip()
    if not nh:
        messagebox.showwarning("Incompleto", "Escribe el next-hop (IP de R1).")
        return
    # Buscar si ya hay una ruta por defecto y preguntar si reemplazarla
    for rt in app.static_routes:
        if rt['dest'] == "0.0.0.0" and rt['mask'] == "0.0.0.0":
            msg = f"Ya existe una ruta por defecto -> {rt['nexthop']}.\n¿Reemplazarla por -> {nh}?"
            if messagebox.askyesno("Ruta existente", msg):
                idx = app.static_routes.index(rt)
                app.static_routes.pop(idx)
                app.rt_listbox.delete(idx)
            else:
                return
            break
    app.static_routes.append({'dest': '0.0.0.0', 'mask': '0.0.0.0', 'nexthop': nh})
    app.rt_listbox.insert(tk.END, f"  ip route 0.0.0.0 0.0.0.0 {nh}  ← ruta por defecto")


def _remove_static_route(app):
    """Elimina la ruta estática seleccionada."""
    sel = app.rt_listbox.curselection()
    if sel:
        app.rt_listbox.delete(sel[0])
        app.static_routes.pop(sel[0])


def _add_ospf_network(app):
    """Agrega una red OSPF manualmente."""
    if not app.chk_ospf.get():
        messagebox.showwarning("OSPF", "Activa el checkbox primero.")
        return
    net  = app.ospf_net.get().strip()
    wild = app.ospf_wild.get().strip()
    area = app.ospf_area.get().strip()
    if not all([net, wild, area]):
        messagebox.showwarning("Incompleto", "Completa todos los campos.")
        return
    app.ospf_networks.append({'network': net, 'wildcard': wild, 'area': area})
    app.ospf_listbox.insert(tk.END, f"  network {net} {wild} area {area}")
    app.ospf_net.delete(0, tk.END)
    app.ospf_wild.delete(0, tk.END)


def _auto_ospf_from_pools(app):
    """
    Genera automáticamente las redes OSPF a partir de los pools DHCP definidos.
    La wildcard se calcula invirtiendo los octetos de la máscara de subred.
    """
    if not app.chk_ospf.get():
        messagebox.showwarning("OSPF", "Activa el checkbox primero.")
        return
    if not app.dhcp_pools:
        messagebox.showwarning("Sin pools", "No hay pools DHCP definidos.")
        return
    for p in app.dhcp_pools:
        try:
            parts = [255 - int(x) for x in p['mask'].split('.')]
            wild  = '.'.join(str(x) for x in parts)
        except Exception:
            wild  = "0.0.0.255"   # wildcard /24 por defecto si hay error
        app.ospf_networks.append({'network': p['net'], 'wildcard': wild, 'area': '0'})
        app.ospf_listbox.insert(tk.END, f"  network {p['net']} {wild} area 0  [{p['name']}]")
    messagebox.showinfo("Listo", f"{len(app.dhcp_pools)} red(es) OSPF agregadas.")


def _remove_ospf_network(app):
    """Elimina la red OSPF seleccionada."""
    sel = app.ospf_listbox.curselection()
    if sel:
        app.ospf_listbox.delete(sel[0])
        app.ospf_networks.pop(sel[0])
