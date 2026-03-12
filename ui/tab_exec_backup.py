"""
ui/tab_exec_backup.py — Pestañas ⑥ Ejecución  y  ⑦ Backup
===========================================================
Pestaña ⑥: Botones para aplicar o limpiar config en los switches seleccionados.
            Log de consola en tiempo real.
Pestaña ⑦: Exportar/importar config como JSON y descargar running-config.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import json
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime

from constants import BG2, SUCCESS, WARN, TEXT2
from ui.widgets import make_frame, make_label, make_button, make_scrolled_text, make_title
from core.connector import run_on_switch, fetch_running_config


# ═══════════════════════════════════════════════════════════════════════════════
#  PESTAÑA ⑥ — EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def build_tab_exec(app, parent):
    """
    Construye la pestaña de Ejecución.

    Widgets creados en 'app':
      - app.log_area : área de texto con el log de consola en tiempo real
    """
    # ── Botones de acción principal ───────────────────────────────────────────
    bf = make_frame(parent); bf.pack(pady=12)
    make_button(bf, "▶  APLICAR A SUCURSALES SELECCIONADAS",
                lambda: deploy_config(app),
                color=SUCCESS, fg=BG2).grid(row=0, column=0, padx=8)
    make_button(bf, "🗑  LIMPIAR SWITCH\n    (sin tocar SSH)",
                lambda: clean_switch(app),
                color="#6e2020").grid(row=0, column=1, padx=8)

    make_label(parent,
               "Selecciona las sucursales en la pestaña ① antes de aplicar.",
               fg=WARN).pack()
    make_label(parent, "Registro de Consola:").pack(anchor="w", padx=12, pady=(8, 2))

    # Área de log (fondo negro, texto verde terminal)
    app.log_area = make_scrolled_text(parent, width=104, height=28)
    app.log_area.pack(padx=12, pady=4)


def _log(app, msg: str):
    """Agrega una línea al log de consola y hace scroll automático al final."""
    app.log_area.insert(tk.END, msg + "\n")
    app.log_area.see(tk.END)
    app.root.update()   # forzar redibujado para ver el log en tiempo real


def _validate_sucursales(app) -> bool:
    """Retorna False y muestra error si no hay sucursales configuradas."""
    if not app.sucursales:
        messagebox.showerror("Error", "No hay sucursales configuradas.")
        return False
    return True


def _get_selected_sucursales(app) -> list:
    """
    Retorna la lista de sucursales seleccionadas en el listbox.
    Muestra advertencia si no hay ninguna seleccionada.
    """
    sel = app.sw_listbox.curselection()
    if not sel:
        messagebox.showwarning("Sin selección",
                               "Selecciona al menos una sucursal en la pestaña ①.")
        return []
    return [app.sucursales[i] for i in sel]


def _build_config_params(app) -> dict:
    """
    Empaqueta todos los parámetros de configuración de la app en un dict
    listo para pasarle a build_commands() en core/command_builder.py.
    """
    return {
        'chk_intervlan':   app.chk_intervlan.get(),
        'dhcp_pools':      app.dhcp_pools,
        'vlans_data':      app.vlans_data,
        'static_routes':   app.static_routes,
        'chk_ospf':        app.chk_ospf.get(),
        'ospf_pid':        app.ospf_pid.get().strip(),
        'ospf_networks':   app.ospf_networks,
        'qos_classes':     app.qos_classes,
        'pol_entries':     app.pol_entries,
        'pol_name':        app.pol_name.get().strip(),
        'service_policies':app.service_policies,
    }


def deploy_config(app):
    """
    Aplica la configuración completa a todas las sucursales seleccionadas.
    Pregunta si limpiar la config anterior antes de aplicar.
    """
    if not _validate_sucursales(app): return
    targets = _get_selected_sucursales(app)
    if not targets: return

    do_clean = messagebox.askyesno(
        "Limpiar antes de aplicar",
        f"Se aplicará la config a {len(targets)} sucursal(es).\n\n"
        "¿Eliminar configuración anterior del switch antes de aplicar?\n"
        "(Recomendado para re-configurar)"
    )

    _log(app, "═" * 58)
    _log(app, f"  INICIO DESPLIEGUE — {len(targets)} sucursal(es)")
    _log(app, f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _log(app, "═" * 58)

    config_params = _build_config_params(app)
    ok, fail = 0, 0
    for sw in targets:
        success = run_on_switch(
            sw, config_params,
            do_clean=do_clean,
            log_fn=lambda msg: _log(app, msg),
        )
        if success:
            ok += 1
        else:
            fail += 1

    _log(app, f"\n{'═'*58}")
    _log(app, f"  RESULTADO: {ok} exitosa(s)  |  {fail} fallida(s)")
    _log(app, f"{'═'*58}")

    # Ofrecer exportar si al menos una sucursal fue exitosa
    if ok > 0 and messagebox.askyesno("Exportar",
                                      "¿Exportar esta configuración a .json?"):
        export_config(app)


def clean_switch(app):
    """
    Limpia la configuración de las sucursales seleccionadas
    sin tocar SSH, usuarios ni crypto key.
    """
    if not _validate_sucursales(app): return
    targets = _get_selected_sucursales(app)
    if not targets: return
    if not messagebox.askyesno("Confirmar",
                               f"Se limpiará la config de {len(targets)} sucursal(es).\n"
                               "SSH y acceso remoto NO se tocarán.\n\n¿Continuar?"):
        return

    from netmiko import ConnectHandler
    import time
    from core.connector import make_device_params, send_cmd_by_cmd
    from core.command_builder import build_cleanup_commands

    _log(app, "═" * 58)
    for sw in targets:
        _log(app, f"\n[LIMPIEZA] {sw['name']} — {sw['ip']}")
        try:
            nc = ConnectHandler(**make_device_params(sw))
            nc.enable()
            _log(app, f"  Conectado: {nc.find_prompt()!r}")
            cleanup = build_cleanup_commands(
                nc,
                app.static_routes,
                app.ospf_networks,
                log_fn=lambda msg: _log(app, msg),
            )
            if cleanup:
                nc.config_mode()
                time.sleep(0.3)
                send_cmd_by_cmd(nc, cleanup, log_fn=lambda msg: _log(app, msg))
                nc.exit_config_mode()
            nc.save_config()
            _log(app, "  ✔ Limpieza completada")
            nc.disconnect()
        except Exception as e:
            _log(app, f"  ✘ Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PESTAÑA ⑦ — BACKUP / EXPORT / IMPORT
# ═══════════════════════════════════════════════════════════════════════════════

def build_tab_backup(app, parent):
    """
    Construye la pestaña de Backup y Restauración.

    Widgets creados en 'app':
      - app.backup_preview : área de texto con la vista previa del JSON / running-config
    """
    make_title(parent, "⚙  Backup y Restauración")

    # Tarjetas de acción
    for (icon, title, desc, color, cmd) in [
        ("💾", "Exportar configuración (.json)",
         "Guarda DHCP, VLANs, rutas y QoS. No incluye credenciales.",
         "#21262d", lambda: export_config(app)),

        ("📂", "Cargar configuración (.json)",
         "Restaura config previa a la app. No modifica el switch todavía.",
         "#4a3000", lambda: import_config(app)),

        ("⬇", "Descargar running-config del switch",
         "Descarga running-config a .txt desde la sucursal seleccionada.",
         "#0d2137", lambda: backup_running_config(app)),
    ]:
        f = make_title.__module__  # placeholder para importar make_labelframe
        from ui.widgets import make_labelframe
        card = make_labelframe(parent, f"{icon}  {title}")
        card.pack(fill="x", padx=20, pady=5)
        make_label(card, desc, fg=TEXT2).pack(anchor="w")
        make_button(card, f"{icon}  {title}", cmd, color=color, fg="#c9d1d9").pack(pady=5, anchor="w")

    make_label(parent, "Vista previa:").pack(anchor="w", padx=20, pady=(8, 2))
    app.backup_preview = make_scrolled_text(parent, width=98, height=10, fg=TEXT2)
    app.backup_preview.pack(padx=20, pady=4)


def export_config(app):
    """
    Exporta toda la configuración a un archivo JSON.
    Las contraseñas y enable secrets NO se incluyen por seguridad.
    """
    fn = filedialog.asksaveasfilename(
        title="Exportar config",
        defaultextension=".json",
        initialfile=f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        filetypes=[("JSON", "*.json"), ("All", "*.*")],
    )
    if not fn: return

    payload = {
        "meta": {
            "version": "2.1",
            "exported": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        # Sucursales sin contraseñas (solo nombre, IP y usuario)
        "sucursales":      [{k: v for k, v in s.items() if k not in ('pass', 'secret')}
                            for s in app.sucursales],
        "dhcp_pools":      app.dhcp_pools,
        "vlans":           app.vlans_data,
        "static_routes":   app.static_routes,
        "ospf_networks":   app.ospf_networks,
        "ospf_enabled":    app.chk_ospf.get(),
        "ospf_pid":        app.ospf_pid.get().strip(),
        "qos_classes":     app.qos_classes,
        "pol_entries":     app.pol_entries,
        "pol_name":        app.pol_name.get().strip(),
        "service_policies":app.service_policies,
    }
    with open(fn, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    _show_in_preview(app, json.dumps(payload, indent=2, ensure_ascii=False))
    messagebox.showinfo("Exportado", f"Guardado en:\n{fn}")


def import_config(app):
    """
    Importa una configuración desde JSON y recarga todos los listboxes de la GUI.
    No modifica ningún switch; solo actualiza el estado en memoria.
    """
    fn = filedialog.askopenfilename(
        title="Cargar config",
        filetypes=[("JSON", "*.json"), ("All", "*.*")],
    )
    if not fn: return
    try:
        with open(fn, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return

    if 'vlans' not in payload:
        messagebox.showerror("Formato inválido", "Archivo no reconocido.")
        return

    if not messagebox.askyesno("Confirmar",
                               f"Cargar {len(payload.get('dhcp_pools', []))} pool(s), "
                               f"{len(payload.get('vlans', []))} VLAN(s) y "
                               f"{len(payload.get('qos_classes', []))} clase(s) QoS?\n"
                               "Reemplaza la config actual."):
        return

    # ── Actualizar estado en memoria ──────────────────────────────────────────
    app.dhcp_pools        = payload.get('dhcp_pools', [])
    app.vlans_data        = payload.get('vlans', [])
    app.static_routes     = payload.get('static_routes', [])
    app.ospf_networks     = payload.get('ospf_networks', [])
    app.qos_classes       = payload.get('qos_classes', [])
    app.pol_entries       = payload.get('pol_entries', [])
    app.service_policies  = payload.get('service_policies', [])

    # Restaurar checkboxes y campos de texto especiales
    if payload.get('ospf_enabled'):
        app.chk_ospf.set(True)
        from ui.tab_routing import _toggle_ospf
        _toggle_ospf(app)
    if payload.get('pol_name'):
        app.pol_name.delete(0, tk.END)
        app.pol_name.insert(0, payload['pol_name'])

    # ── Refrescar todos los listboxes ─────────────────────────────────────────
    _reload_listboxes(app, payload)

    _show_in_preview(app, json.dumps(payload, indent=2, ensure_ascii=False))
    meta = payload.get('meta', {})
    messagebox.showinfo("Cargado",
                        f"Config cargada.\nExportado: {meta.get('exported', '?')}\n\n"
                        f"{len(app.dhcp_pools)} pool(s), {len(app.vlans_data)} VLAN(s), "
                        f"{len(app.qos_classes)} clase(s) QoS, "
                        f"{len(app.service_policies)} policy(s).")


def _reload_listboxes(app, payload):
    """Recarga todos los listboxes de la GUI con los datos del payload importado."""
    # DHCP
    app.dhcp_listbox.delete(0, tk.END)
    for p in app.dhcp_pools:
        app.dhcp_listbox.insert(
            tk.END, f"  {p['name']:18} {p['net']:18} {p['mask']:18} GW:{p['gw']}")

    # VLANs
    app.vlan_listbox.delete(0, tk.END)
    for v in app.vlans_data:
        ps = "sin DHCP"
        if v.get('dhcp_idx') is not None:
            try:
                pp = app.dhcp_pools[v['dhcp_idx']]
                ps = f"Pool:{pp['name']}"
            except Exception:
                ps = "Pool:??"
        app.vlan_listbox.insert(
            tk.END,
            f"  VLAN {v['id']:5} [{v.get('name', ''):14}]  {ps:22}  "
            f"Puertos:{v.get('ports') or '—'}")

    # Rutas estáticas
    app.rt_listbox.delete(0, tk.END)
    for rt in app.static_routes:
        app.rt_listbox.insert(tk.END, f"  ip route {rt['dest']} {rt['mask']} {rt['nexthop']}")

    # OSPF
    app.ospf_listbox.delete(0, tk.END)
    for n in app.ospf_networks:
        app.ospf_listbox.insert(
            tk.END, f"  network {n['network']} {n['wildcard']} area {n['area']}")

    # QoS class-maps
    app.cls_listbox.delete(0, tk.END)
    for c in app.qos_classes:
        app.cls_listbox.insert(
            tk.END,
            f"  class-map {c['match_type']} {c['name']:20}  match {c['criteria']} {c['value']}")

    # QoS policy-map entries
    app.pol_listbox.delete(0, tk.END)
    for pe in app.pol_entries:
        app.pol_listbox.insert(
            tk.END, f"  class {pe['class']:22}  →  {pe['action']} {pe['value']}")

    # service-policies
    app.sp_listbox.delete(0, tk.END)
    for sp in app.service_policies:
        app.sp_listbox.insert(
            tk.END,
            f"  {sp['iface']:26}  service-policy {sp['dir']:8} {sp['policy']}")


def backup_running_config(app):
    """
    Descarga el running-config de la primera sucursal seleccionada
    y lo guarda como archivo .txt.
    """
    if not _validate_sucursales(app): return
    targets = _get_selected_sucursales(app)
    if not targets: return
    sw = targets[0]   # solo se descarga de una sucursal a la vez

    fn = filedialog.asksaveasfilename(
        title="Guardar running-config",
        defaultextension=".txt",
        initialfile=f"running_{sw['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        filetypes=[("Text", "*.txt"), ("All", "*.*")],
    )
    if not fn: return

    try:
        raw = fetch_running_config(sw)
        header = (
            f"# Backup {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# Sucursal: {sw['name']}  IP: {sw['ip']}\n\n"
        )
        with open(fn, 'w') as f:
            f.write(header + raw)

        # Mostrar los primeros 4000 caracteres en la vista previa
        preview = raw[:4000] + ("\n...(truncado)..." if len(raw) > 4000 else "")
        _show_in_preview(app, preview)
        messagebox.showinfo("OK", f"Guardado en:\n{fn}")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def _show_in_preview(app, text: str):
    """Muestra texto en el área de vista previa de la pestaña de backup."""
    app.backup_preview.delete("1.0", tk.END)
    app.backup_preview.insert(tk.END, text)
