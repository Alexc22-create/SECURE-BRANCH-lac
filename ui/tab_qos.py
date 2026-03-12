"""
ui/tab_qos.py — Pestaña ⑤: QoS MQC (Modular QoS CLI)
=======================================================
Implementa el modelo MQC de IOS en 3 pasos:
  1. class-map  → clasifica tráfico por DSCP, IP o ACL
  2. policy-map → define la acción: police, shape, priority, bandwidth, set dscp
  3. service-policy → aplica la política a la interfaz deseada (input/output)

El uplink (Gi0/0) está protegido y no se puede seleccionar para service-policy.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import tkinter as tk
from tkinter import ttk, messagebox

from constants import BG2, BG3, SUCCESS, TEXT, TEXT2, UPLINK_IFACE, DSCP_PRESETS
from ui.widgets import (
    make_frame, make_label, make_entry, make_button,
    make_listbox, make_labelframe, make_title, make_scrolled_frame,
)


def build_tab_qos(app, parent):
    """
    Construye la pestaña de QoS MQC.

    Widgets creados en 'app':
      - app.cls_name, cls_match_type, cls_criteria, cls_value : form class-map
      - app.cls_listbox     : lista de class-maps definidas
      - app.pol_name        : nombre de la policy-map
      - app.pol_class_sel   : combo de selección de clase para la política
      - app.pol_action      : combo de acción (priority, police, etc.)
      - app.pol_value       : valor numérico/dscp de la acción
      - app.pol_listbox     : lista de entradas de la policy-map
      - app.sp_iface        : interfaz para service-policy
      - app.sp_dir          : dirección (input/output/both)
      - app.sp_listbox      : lista de service-policies aplicadas
    """
    make_title(parent, "⚙  QoS Avanzado — MQC (IOS 15.x)")
    sf = make_scrolled_frame(parent)

    # ── Explicación del flujo MQC ──────────────────────────────────────────────
    finfo = make_labelframe(sf, "Flujo MQC")
    finfo.pack(fill="x", padx=12, pady=6)
    make_label(finfo, (
        "  1. class-map  → clasifica tráfico por DSCP, IP o ACL\n"
        "  2. policy-map → define la acción: police (limitar), shape (moldear), priority (priorizar)\n"
        "  3. service-policy → aplica la política a la interfaz deseada (input / output)"
    ), fg=TEXT).pack(anchor="w")

    # ── Presets DSCP rápidos ──────────────────────────────────────────────────
    # Botones para pre-cargar valores DSCP comunes en el formulario de class-map.
    fpreset = make_labelframe(sf, "Presets DSCP rápidos")
    fpreset.pack(fill="x", padx=12, pady=4)
    make_label(fpreset, "Clic para pre-cargar el valor DSCP en el formulario de clase:",
               fg=TEXT2).pack(anchor="w")
    pr = make_frame(fpreset); pr.pack(fill="x", pady=4)
    for col, (label, val) in enumerate(DSCP_PRESETS):
        make_button(pr, label,
                    lambda v=val: _preset_dscp(app, v),
                    color=BG3, fg="#58a6ff"   # ACCENT
                    ).grid(row=col // 4, column=col % 4, padx=4, pady=3, sticky="w")

    # ── class-map ─────────────────────────────────────────────────────────────
    fcls = make_labelframe(sf, "class-map — Clasificar tráfico")
    fcls.pack(fill="x", padx=12, pady=6)

    r1 = make_frame(fcls); r1.pack(fill="x", pady=4)
    make_label(r1, "Nombre:").grid(row=0, column=0, sticky="e", padx=6)
    app.cls_name = make_entry(r1, width=18); app.cls_name.grid(row=0, column=1, padx=4)
    make_label(r1, "Tipo:").grid(row=0, column=2, sticky="e", padx=6)
    app.cls_match_type = ttk.Combobox(r1,
                                      values=["match-any", "match-all"],
                                      state="readonly", width=12)
    # match-any = OR (el paquete cumple cualquiera de los criterios)
    # match-all = AND (el paquete cumple todos los criterios)
    app.cls_match_type.set("match-any")
    app.cls_match_type.grid(row=0, column=3, padx=4)

    r2 = make_frame(fcls); r2.pack(fill="x", pady=4)
    make_label(r2, "Criterio:").grid(row=0, column=0, sticky="e", padx=6)
    app.cls_criteria = ttk.Combobox(r2,
                                    values=["dscp", "ip dscp", "ip precedence",
                                            "access-group name", "protocol"],
                                    state="readonly", width=18)
    app.cls_criteria.set("dscp")
    app.cls_criteria.grid(row=0, column=1, padx=4)
    make_label(r2, "Valor:").grid(row=0, column=2, sticky="e", padx=6)
    app.cls_value = make_entry(r2, width=16)
    app.cls_value.insert(0, "ef")   # EF es el DSCP más común para voz
    app.cls_value.grid(row=0, column=3, padx=4)

    make_button(fcls, "＋  Agregar clase",
                lambda: _add_qos_class(app),
                color=SUCCESS, fg=BG2).pack(anchor="w", pady=4)
    app.cls_listbox = make_listbox(fcls, width=80, height=4)
    app.cls_listbox.pack(pady=4)
    make_button(fcls, "✕  Eliminar",
                lambda: _remove_qos_class(app),
                color="#6e2020").pack(anchor="w")

    # ── policy-map ────────────────────────────────────────────────────────────
    fpol = make_labelframe(sf, "policy-map — Asignar acciones a clases")
    fpol.pack(fill="x", padx=12, pady=6)

    pn_row = make_frame(fpol); pn_row.pack(fill="x", pady=4)
    make_label(pn_row, "Nombre política:").pack(side="left", padx=6)
    app.pol_name = make_entry(pn_row, width=22)
    app.pol_name.insert(0, "POLITICA_QOS")   # nombre por defecto
    app.pol_name.pack(side="left", padx=4)

    pa_row = make_frame(fpol); pa_row.pack(fill="x", pady=4)
    make_label(pa_row, "Clase:").grid(row=0, column=0, sticky="e", padx=6)
    app.pol_class_sel = ttk.Combobox(pa_row, values=["(↻ actualizar)"],
                                     state="readonly", width=20)
    app.pol_class_sel.grid(row=0, column=1, padx=4)
    make_button(pa_row, "↻",
                lambda: _refresh_pol_classes(app),
                color=BG3).grid(row=0, column=2, padx=4)

    make_label(pa_row, "Acción:").grid(row=0, column=3, sticky="e", padx=6)
    app.pol_action = ttk.Combobox(pa_row,
                                  values=["priority", "bandwidth",
                                          "police rate", "shape average", "set dscp"],
                                  state="readonly", width=16)
    app.pol_action.set("priority")
    app.pol_action.grid(row=0, column=4, padx=4)

    make_label(pa_row, "Valor (bps/dscp):").grid(row=0, column=5, sticky="e", padx=6)
    app.pol_value = make_entry(pa_row, width=14)
    app.pol_value.insert(0, "1000000")   # 1 Mbps por defecto
    app.pol_value.grid(row=0, column=6, padx=4)

    make_button(fpol, "＋  Agregar clase→acción",
                lambda: _add_pol_entry(app),
                color=SUCCESS, fg=BG2).pack(anchor="w", pady=4)
    app.pol_listbox = make_listbox(fpol, width=80, height=4)
    app.pol_listbox.pack(pady=4)
    make_button(fpol, "✕  Eliminar",
                lambda: _remove_pol_entry(app),
                color="#6e2020").pack(anchor="w")

    # ── service-policy ────────────────────────────────────────────────────────
    fapp = make_labelframe(sf, "service-policy — Aplicar a interfaz")
    fapp.pack(fill="x", padx=12, pady=6)
    make_label(fapp,
               "Aplica la política QoS a una interfaz específica del switch (no usar Gi0/0 uplink).",
               fg=TEXT2).pack(anchor="w")

    ap_row = make_frame(fapp); ap_row.pack(fill="x", pady=4)
    make_label(ap_row, "Interfaz:").grid(row=0, column=0, sticky="e", padx=6)
    app.sp_iface = make_entry(ap_row, width=22)
    app.sp_iface.insert(0, "GigabitEthernet0/1")
    app.sp_iface.grid(row=0, column=1, padx=4)

    make_label(ap_row, "Dirección:").grid(row=0, column=2, sticky="e", padx=6)
    app.sp_dir = ttk.Combobox(ap_row,
                               values=["input", "output", "both"],
                               state="readonly", width=10)
    app.sp_dir.set("output")   # output es lo más común en QoS de egreso
    app.sp_dir.grid(row=0, column=3, padx=4)

    make_button(fapp, "＋  Agregar aplicación",
                lambda: _add_service_policy(app),
                color=SUCCESS, fg=BG2).pack(anchor="w", pady=4)
    app.sp_listbox = make_listbox(fapp, width=80, height=3)
    app.sp_listbox.pack(pady=4)
    make_button(fapp, "✕  Eliminar",
                lambda: _remove_service_policy(app),
                color="#6e2020").pack(anchor="w")


# ── Handlers internos ──────────────────────────────────────────────────────────

def _preset_dscp(app, val: str):
    """Carga un valor DSCP predefinido en el campo de valor del class-map."""
    app.cls_value.delete(0, tk.END)
    app.cls_value.insert(0, val)


def _refresh_pol_classes(app):
    """Actualiza el combo de clases de la policy-map con los class-maps definidos."""
    names = [c['name'] for c in app.qos_classes] or ["(sin clases)"]
    app.pol_class_sel['values'] = names
    if names:
        app.pol_class_sel.set(names[0])


def _add_qos_class(app):
    """Agrega un nuevo class-map a la lista."""
    name  = app.cls_name.get().strip()
    mtype = app.cls_match_type.get()
    crit  = app.cls_criteria.get()
    val   = app.cls_value.get().strip()
    if not all([name, crit, val]):
        messagebox.showwarning("Incompleto", "Completa nombre, criterio y valor.")
        return
    app.qos_classes.append({'name': name, 'match_type': mtype, 'criteria': crit, 'value': val})
    app.cls_listbox.insert(tk.END, f"  class-map {mtype} {name:20}  match {crit} {val}")
    app.cls_name.delete(0, tk.END)


def _remove_qos_class(app):
    """Elimina el class-map seleccionado."""
    sel = app.cls_listbox.curselection()
    if sel:
        app.cls_listbox.delete(sel[0])
        app.qos_classes.pop(sel[0])


def _add_pol_entry(app):
    """Agrega una entrada clase→acción a la policy-map."""
    cls    = app.pol_class_sel.get()
    action = app.pol_action.get()
    val    = app.pol_value.get().strip()
    if cls in ("(↻ actualizar)", "(sin clases)") or not val:
        messagebox.showwarning("Incompleto", "Selecciona clase y valor.")
        return
    app.pol_entries.append({'class': cls, 'action': action, 'value': val})
    app.pol_listbox.insert(tk.END, f"  class {cls:22}  →  {action} {val}")


def _remove_pol_entry(app):
    """Elimina la entrada de policy-map seleccionada."""
    sel = app.pol_listbox.curselection()
    if sel:
        app.pol_listbox.delete(sel[0])
        app.pol_entries.pop(sel[0])


def _add_service_policy(app):
    """
    Agrega una aplicación de service-policy a una interfaz.
    Si la dirección es 'both', crea dos entradas (input + output).
    """
    iface     = app.sp_iface.get().strip()
    direction = app.sp_dir.get()
    pol       = app.pol_name.get().strip()
    if not iface:
        messagebox.showwarning("Incompleto", "Indica la interfaz.")
        return
    if UPLINK_IFACE.lower() in iface.lower():
        messagebox.showwarning("Uplink protegido",
                               f"No apliques QoS directamente en {UPLINK_IFACE}.\n"
                               "Usa una interfaz de acceso.")
        return
    # 'both' genera dos service-policy: una de input y una de output
    dirs = ["input", "output"] if direction == "both" else [direction]
    for d in dirs:
        app.service_policies.append({'iface': iface, 'dir': d, 'policy': pol})
        app.sp_listbox.insert(tk.END, f"  {iface:26}  service-policy {d:8} {pol}")


def _remove_service_policy(app):
    """Elimina la service-policy seleccionada."""
    sel = app.sp_listbox.curselection()
    if sel:
        app.sp_listbox.delete(sel[0])
        app.service_policies.pop(sel[0])
