"""
ui/tab_vlan.py — Pestaña ③: VLANs y Puertos
=============================================
Permite definir VLANs con:
  - ID y nombre de la VLAN
  - Pool DHCP vinculado (para asignar IP a la SVI en switches L3)
  - Puertos físicos asignados (modo access o trunk)
  - ACL de seguridad opcional (bloqueo de redes sociales + reglas personalizadas)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import tkinter as tk
from tkinter import ttk, messagebox

from constants import BG2, SUCCESS, TEXT2, UPLINK_IFACE
from ui.widgets import (
    make_frame, make_label, make_entry, make_button,
    make_listbox, make_labelframe, make_title, make_scrolled_frame,
    make_scrolled_text,
)
from ui.tabs_sw_dhcp import get_dhcp_options
from ui.validators import validate_vlan_id, validate_port_range
from ui.preview_window import show_preview


def build_tab_vlan(app, parent):
    """
    Construye la pestaña de VLANs y Puertos.

    Widgets creados en 'app':
      - app.v_id, v_name            : ID y nombre de la VLAN
      - app.chk_dhcp_var            : checkbox "Asignar pool DHCP"
      - app.v_dhcp_combo            : combo de selección de pool
      - app.chk_port_var            : checkbox "Asignar puertos"
      - app.v_ports                 : campo de rangos de puertos
      - app.port_mode               : combo access/trunk
      - app.chk_social_var          : checkbox "Bloquear redes sociales"
      - app.v_acl_custom            : área de texto con ACL extra
      - app.vlan_listbox            : lista de VLANs definidas
    """
    make_title(parent, "⚙  VLANs y Puertos")
    sf = make_scrolled_frame(parent)   # frame scrolleable para contenido largo

    # ── Datos básicos de la VLAN ──────────────────────────────────────────────
    fb = make_labelframe(sf, "Datos de la VLAN")
    fb.pack(fill="x", padx=12, pady=4)
    r  = make_frame(fb); r.pack(fill="x")
    make_label(r, "ID VLAN:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    app.v_id = make_entry(r, width=8); app.v_id.grid(row=0, column=1, padx=4)
    make_label(r, "Nombre:").grid(row=0, column=2, sticky="e", padx=6)
    app.v_name = make_entry(r, width=18); app.v_name.grid(row=0, column=3, padx=4)

    # ── DHCP vinculado ────────────────────────────────────────────────────────
    # Asocia un pool DHCP a esta VLAN para que el switch L3 configure la SVI
    # con la IP del gateway del pool.
    fd = make_labelframe(sf, "DHCP para esta VLAN  (define la IP de la SVI en switches L3)")
    fd.pack(fill="x", padx=12, pady=4)
    dr = make_frame(fd); dr.pack(fill="x")

    app.chk_dhcp_var = tk.BooleanVar()
    ttk.Checkbutton(dr, text="Asignar pool DHCP",
                    variable=app.chk_dhcp_var,
                    command=lambda: _toggle_dhcp_select(app)).grid(row=0, column=0, sticky="w", padx=6)
    make_label(dr, "Pool:").grid(row=0, column=1, padx=(14, 4))
    app.v_dhcp_combo = ttk.Combobox(dr, state="disabled", width=28)
    app.v_dhcp_combo['values'] = get_dhcp_options(app)
    app.v_dhcp_combo.grid(row=0, column=2, pady=4)
    # Botón para refrescar la lista de pools si se agregaron después de abrir esta pestaña
    make_button(dr, "↻", lambda: _refresh_dhcp_combo(app), color="#21262d").grid(row=0, column=3, padx=6)
    make_label(fd,
               "En switches L2: el DHCP debe estar en R1 (router-on-a-stick).\n"
               "En switches L3: la SVI recibe la IP del gateway del pool.",
               fg=TEXT2).pack(anchor="w")

    # ── Asignación de puertos ─────────────────────────────────────────────────
    # Gi0/0 (UPLINK_IFACE) está protegida; la app rechaza asignarla a una VLAN.
    fp = make_labelframe(sf, f"Puertos  (Gi0/0 = uplink protegido, no usar aquí)")
    fp.pack(fill="x", padx=12, pady=4)
    pr = make_frame(fp); pr.pack(fill="x")

    app.chk_port_var = tk.BooleanVar()
    ttk.Checkbutton(pr, text="Asignar puertos a esta VLAN",
                    variable=app.chk_port_var,
                    command=lambda: _toggle_ports(app)).grid(row=0, column=0, sticky="w", padx=6)
    app.lbl_port = make_label(pr, "Rangos Gi0/1-3 o Gi0/1,Gi0/3:", state="disabled")
    app.lbl_port.grid(row=0, column=1, padx=6)
    app.v_ports = make_entry(pr, width=24, state="disabled")
    app.v_ports.grid(row=0, column=2, padx=4)

    pr2 = make_frame(fp); pr2.pack(fill="x", pady=4)
    make_label(pr2, "Modo:").grid(row=0, column=0, sticky="e", padx=6)
    app.port_mode = ttk.Combobox(pr2, values=["access", "trunk"], state="readonly", width=10)
    app.port_mode.set("access")
    app.port_mode.grid(row=0, column=1, padx=4)
    make_label(pr2,
               "access = un solo VLAN por puerto  |  trunk = múltiples VLANs (uplink entre switches)",
               fg=TEXT2).grid(row=0, column=2, sticky="w", padx=6)

    # ── ACL de seguridad ──────────────────────────────────────────────────────
    fs = make_labelframe(sf, "ACL de Seguridad  (opcional)")
    fs.pack(fill="x", padx=12, pady=4)
    app.chk_social_var = tk.BooleanVar()
    ttk.Checkbutton(fs, text="Bloquear Redes Sociales (Facebook / Twitter)",
                    variable=app.chk_social_var).pack(anchor="w")
    make_label(fs, "Reglas ACL extra. Ej: deny ip host 10.0.0.5 any",
               fg=TEXT2).pack(anchor="w", pady=(4, 0))
    app.v_acl_custom = make_scrolled_text(fs, width=70, height=3)
    app.v_acl_custom.pack(pady=4)

    # ── Botones y listbox de VLANs ────────────────────────────────────────────
    btn_r = make_frame(sf); btn_r.pack(pady=6)
    make_button(btn_r, "✚  Guardar VLAN",
                lambda: _add_vlan(app),
                color=SUCCESS, fg=BG2).pack(side="left", padx=6)
    make_button(btn_r, "✕  Eliminar VLAN",
                lambda: _remove_vlan(app),
                color="#6e2020").pack(side="left", padx=6)
    make_button(btn_r, "👁  Ver comandos IOS",
                lambda: _preview_vlans(app),
                color=BG2).pack(side="left", padx=6)

    app.vlan_listbox = make_listbox(sf, width=92, height=6)
    app.vlan_listbox.pack(padx=12, pady=4)


# ── Handlers internos ──────────────────────────────────────────────────────────

def _toggle_ports(app):
    """Habilita/deshabilita el campo de puertos según el checkbox."""
    s = "normal" if app.chk_port_var.get() else "disabled"
    app.lbl_port.config(state=s)
    app.v_ports.config(state=s)


def _toggle_dhcp_select(app):
    """Habilita/deshabilita el combo de pools DHCP según el checkbox."""
    app.v_dhcp_combo.config(
        state="readonly" if app.chk_dhcp_var.get() else "disabled"
    )


def _refresh_dhcp_combo(app):
    """Recarga las opciones del combo DHCP con los pools actuales."""
    opts = get_dhcp_options(app)
    app.v_dhcp_combo['values'] = opts
    if app.dhcp_pools:
        app.v_dhcp_combo.current(0)


def _add_vlan(app):
    """
    Valida el formulario y agrega la VLAN a la lista en memoria.
    Rechaza el uplink en el campo de puertos.
    """
    vid = app.v_id.get().strip()
    if not vid:
        messagebox.showwarning("Error", "El ID de VLAN es obligatorio.")
        return

    # Validar rango 1–4094
    ok, err = validate_vlan_id(vid)
    if not ok:
        messagebox.showerror("ID de VLAN inválido", err)
        return

    # Evitar VLANs duplicadas
    if any(v['id'] == vid for v in app.vlans_data):
        messagebox.showwarning("Duplicado",
            f"Ya existe una VLAN con el ID {vid}.")
        return

    # Resolver el pool DHCP seleccionado (si aplica)
    dhcp_idx = None
    if app.chk_dhcp_var.get():
        sel = app.v_dhcp_combo.get()
        if sel and sel != "(sin pools)":
            try:
                dhcp_idx = int(sel.split(":")[0])
            except ValueError:
                pass
        if dhcp_idx is None:
            messagebox.showwarning("DHCP", "Selecciona un pool válido.")
            return

    # Validar formato de puertos
    ports_raw = app.v_ports.get().strip() if app.chk_port_var.get() else ""
    if app.chk_port_var.get():
        if not ports_raw:
            messagebox.showwarning("Puertos vacíos",
                "Marcaste 'Asignar puertos' pero el campo está vacío.")
            return
        ok, err = validate_port_range(ports_raw)
        if not ok:
            messagebox.showerror("Puerto inválido", err)
            return

    # Proteger el uplink
    if ports_raw and UPLINK_IFACE.lower() in ports_raw.lower():
        messagebox.showwarning("Uplink protegido",
            f"{UPLINK_IFACE} es el uplink y no se puede asignar a una VLAN.")
        return

    v = {
        'id':           vid,
        'name':         app.v_name.get().strip(),
        'dhcp_idx':     dhcp_idx,
        'assign_ports': app.chk_port_var.get(),
        'ports':        ports_raw if app.chk_port_var.get() else None,
        'port_mode':    app.port_mode.get(),
        'block_social': app.chk_social_var.get(),
        'custom_acl':   app.v_acl_custom.get("1.0", tk.END).strip(),
    }
    app.vlans_data.append(v)

    pool_str = (f"Pool:{app.dhcp_pools[dhcp_idx]['name']}"
                if dhcp_idx is not None else "sin DHCP")
    app.vlan_listbox.insert(
        tk.END,
        f"  VLAN {vid:5} [{v['name']:14}]  {pool_str:22}  "
        f"Puertos:{v['ports'] or '—':16}  [{v['port_mode'].upper()}]"
    )

    # Resetear formulario
    app.v_id.delete(0, tk.END); app.v_name.delete(0, tk.END)
    app.chk_dhcp_var.set(False); _toggle_dhcp_select(app)
    app.chk_port_var.set(False); _toggle_ports(app)
    app.port_mode.set("access")
    app.chk_social_var.set(False)
    app.v_acl_custom.delete("1.0", tk.END)


def _remove_vlan(app):
    """Elimina la VLAN seleccionada de la lista."""
    sel = app.vlan_listbox.curselection()
    if sel:
        app.vlan_listbox.delete(sel[0])
        app.vlans_data.pop(sel[0])


def _preview_vlans(app):
    """Muestra la vista previa de los comandos de VLANs, puertos, ACLs y SVIs."""
    from core.command_builder import build_commands
    cmds = build_commands(
        is_l3=True, chk_intervlan=False,
        dhcp_pools=app.dhcp_pools,
        vlans_data=app.vlans_data,
        static_routes=[], chk_ospf=False, ospf_pid="1", ospf_networks=[],
        qos_classes=[], pol_entries=[], pol_name="", service_policies=[],
    )
    show_preview(
        app.root, "VLANs, Puertos, ACLs y SVIs", cmds,
        note="Los comandos de SVI (ip address) solo se aplican en switches L3.",
    )
