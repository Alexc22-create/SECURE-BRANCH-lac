"""
ui/tab_exec_backup.py — Pestañas ⑥ Ejecución  y  ⑦ Backup
===========================================================
Pestaña ⑥: Botones para aplicar o limpiar config en los switches seleccionados.
            Log de consola en tiempo real.
Pestaña ⑦: Exportar/importar config como JSON, descargar running-config
           y hacer copias de seguridad en AWS S3.

AWS S3 Backup:
  Requiere boto3 instalado: pip install boto3 --break-system-packages
  Credenciales configuradas en la pestaña ⑦ (Access Key + Secret Key + Region + Bucket).
  El running-config se sube como objeto S3 con clave:
    backups/<hostname>/<YYYY-MM-DD_HH-MM-SS>.txt
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import json
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime

from constants import BG, BG2, BG3, ACCENT, SUCCESS, WARN, TEXT, TEXT2, BORDER
from ui.widgets import (make_frame, make_label, make_entry, make_button,
                        make_scrolled_text, make_title, make_labelframe)
from core.connector import run_on_switch, fetch_running_config, restore_running_config
from ui.preview_window import show_preview


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
    make_button(bf, "👁  VER TODOS LOS\n    COMANDOS IOS",
                lambda: _preview_all_commands(app),
                color=BG3).grid(row=0, column=2, padx=8)

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
    Incluye los nuevos parámetros de seguridad y GRE over IPsec (v2.2).
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
        # ── DNS configurable ──────────────────────────────────────────────────
        'dns1':            app.app_config.get('dhcp_dns1', ''),
        'dns2':            app.app_config.get('dhcp_dns2', ''),
        # ── Seguridad (v2.2) ──────────────────────────────────────────────────
        'enable_pw':       getattr(app, 'sec_enable_pw',      None) and app.sec_enable_pw.get().strip()      or "",
        'login_attempts':  getattr(app, 'sec_login_attempts', None) and app.sec_login_attempts.get().strip() or "",
        'login_window':    getattr(app, 'sec_login_window',   None) and app.sec_login_window.get().strip()   or "",
        'login_block_for': getattr(app, 'sec_login_block',    None) and app.sec_login_block.get().strip()    or "",
        'banner_text':     getattr(app, 'sec_banner_text',    None) and app.sec_banner_text.get("1.0", tk.END).strip() or "",
        # ── GRE over IPsec (v2.2) ─────────────────────────────────────────────
        'gre_tunnels':     getattr(app, 'gre_tunnels', []),
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


def _preview_all_commands(app):
    """
    Genera y muestra en la ventana de vista previa la totalidad de comandos
    IOS que se enviarán al switch al pulsar 'Aplicar'.
    Se asume modo L3 para mostrar el conjunto completo; en switches L2
    los comandos de DHCP y SVIs se omiten automáticamente al ejecutar.
    """
    from core.command_builder import build_commands
    params = _build_config_params(app)
    cmds = build_commands(
        is_l3=True,           # asunción para mostrar el set completo
        chk_intervlan=params['chk_intervlan'],
        dhcp_pools=params['dhcp_pools'],
        vlans_data=params['vlans_data'],
        static_routes=params['static_routes'],
        chk_ospf=params['chk_ospf'],
        ospf_pid=params['ospf_pid'],
        ospf_networks=params['ospf_networks'],
        qos_classes=params['qos_classes'],
        pol_entries=params['pol_entries'],
        pol_name=params['pol_name'],
        service_policies=params['service_policies'],
        enable_pw=params['enable_pw'],
        login_attempts=params['login_attempts'],
        login_window=params['login_window'],
        login_block_for=params['login_block_for'],
        banner_text=params['banner_text'],
        gre_tunnels=params['gre_tunnels'],
    )
    show_preview(
        app.root,
        "Todos los comandos IOS — Vista completa",
        cmds,
        note="Previsualización asumiendo switch L3. "
             "En switches L2 se omiten automáticamente: "
             "ip routing, DHCP pools y SVIs con IP.",
    )


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

    Secciones:
      1. Exportar / Importar JSON (config de la app, sin credenciales)
      2. Backup/Restauración de Running-Config real del switch (.txt)
         2a. Descargar running-config del switch a archivo .txt local
         2b. Restaurar running-config desde archivo .txt al switch
      3. AWS S3 Backup — subir running-config de uno o varios switches a un bucket S3

    Widgets creados en 'app':
      app.backup_preview   : ScrolledText — vista previa del JSON / running-config
      app.s3_access_key    : Entry — AWS Access Key ID
      app.s3_secret_key    : Entry — AWS Secret Access Key
      app.s3_region        : Entry — Región AWS (ej. us-east-1)
      app.s3_bucket        : Entry — Nombre del bucket S3
      app.s3_prefix        : Entry — Prefijo/carpeta dentro del bucket (ej. backups/)
    """
    make_title(parent, "⚙  Backup y Restauración")

    # ── Sección 1: Export / Import JSON ───────────────────────────────────────
    frm_json = make_labelframe(parent, "📋  Config de la App (JSON)")
    frm_json.pack(fill="x", padx=20, pady=5)
    make_label(frm_json,
               "Guarda o carga la config de DHCP, VLANs, rutas y QoS. No incluye contraseñas.",
               fg=TEXT2).pack(anchor="w")
    bf = make_frame(frm_json); bf.pack(anchor="w", pady=4)
    make_button(bf, "💾  Exportar .json",
                lambda: export_config(app), color="#21262d", fg=TEXT).grid(row=0, column=0, padx=5)
    make_button(bf, "📂  Importar .json",
                lambda: import_config(app), color="#4a3000", fg=TEXT).grid(row=0, column=1, padx=5)

    # ── Sección 2: Backup / Restauración del Running-Config real ──────────────
    frm_run = make_labelframe(parent, "🔄  Running-Config del Switch  (backup/restauración .txt)")
    frm_run.pack(fill="x", padx=20, pady=5)
    make_label(frm_run,
               "Descarga o restaura el running-config real del switch como archivo .txt.",
               fg=TEXT2).pack(anchor="w")
    make_label(frm_run,
               "⚠  La restauración envía los comandos del archivo al switch y guarda la config.",
               fg=WARN).pack(anchor="w")
    run_bf = make_frame(frm_run); run_bf.pack(anchor="w", pady=4)
    make_button(run_bf, "⬇  Descargar running-config del SW",
                lambda: backup_running_config(app),
                color="#0d2137", fg=TEXT).grid(row=0, column=0, padx=5)
    make_button(run_bf, "⬆  Restaurar config desde archivo .txt",
                lambda: restore_running_config_from_file(app),
                color="#2a1a00", fg=TEXT).grid(row=0, column=1, padx=5)

    # ── Sección 3: AWS S3 Backup ──────────────────────────────────────────────
    # El running-config se obtiene vía SSH (Netmiko) y se sube a S3 con boto3.
    # Clave S3: <prefijo>/<hostname>/<YYYY-MM-DD_HH-MM-SS>.txt
    # Requiere: pip install boto3 --break-system-packages
    frm_s3 = make_labelframe(parent, "☁  Backup en AWS S3  (boto3)")
    frm_s3.pack(fill="x", padx=20, pady=5)
    make_label(frm_s3,
               "Sube el running-config de las sucursales seleccionadas a un bucket S3.\n"
               "Requiere: pip install boto3 --break-system-packages",
               fg=TEXT2).pack(anchor="w")

    # Campos de credenciales AWS
    cred_grid = make_frame(frm_s3)
    cred_grid.pack(fill="x", pady=4)

    # Fila 0: Access Key + Secret Key
    make_label(cred_grid, "Access Key ID:",     width=18).grid(row=0, column=0, sticky="w", pady=2)
    app.s3_access_key = make_entry(cred_grid, width=26)
    app.s3_access_key.grid(row=0, column=1, padx=4)

    make_label(cred_grid, "Secret Access Key:", width=18).grid(row=0, column=2, sticky="w")
    app.s3_secret_key = make_entry(cred_grid, width=34, show="*")
    app.s3_secret_key.grid(row=0, column=3, padx=4)

    # Fila 1: Region + Bucket + Prefijo
    make_label(cred_grid, "Región AWS:",        width=18).grid(row=1, column=0, sticky="w", pady=2)
    app.s3_region = make_entry(cred_grid, width=16)
    app.s3_region.insert(0, "us-east-1")
    app.s3_region.grid(row=1, column=1, padx=4, sticky="w")

    make_label(cred_grid, "Bucket S3:",         width=18).grid(row=1, column=2, sticky="w")
    app.s3_bucket = make_entry(cred_grid, width=24)
    app.s3_bucket.insert(0, "mi-bucket-backups")
    app.s3_bucket.grid(row=1, column=3, padx=4, sticky="w")

    make_label(cred_grid, "Prefijo/carpeta:",   width=18).grid(row=2, column=0, sticky="w", pady=2)
    app.s3_prefix = make_entry(cred_grid, width=24)
    app.s3_prefix.insert(0, "backups/switches/")
    app.s3_prefix.grid(row=2, column=1, padx=4, sticky="w")

    make_label(cred_grid,
               "→  Ruta en S3: <prefijo>/<hostname>/<fecha>.txt",
               fg=TEXT2).grid(row=2, column=2, columnspan=2, sticky="w")

    # Botones S3
    s3_bf = make_frame(frm_s3); s3_bf.pack(anchor="w", pady=6)
    make_button(s3_bf, "☁  Subir a S3 (sucursales seleccionadas)",
                lambda: backup_to_s3(app),
                color="#1a3a1a", fg=TEXT).grid(row=0, column=0, padx=5)
    make_button(s3_bf, "🔍  Verificar credenciales S3",
                lambda: verify_s3_credentials(app),
                color=BG3, fg=TEXT).grid(row=0, column=1, padx=5)

    # ── Vista previa ──────────────────────────────────────────────────────────
    make_label(parent, "Vista previa:").pack(anchor="w", padx=20, pady=(8, 2))
    app.backup_preview = make_scrolled_text(parent, width=98, height=8, fg=TEXT2)
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


def restore_running_config_from_file(app):
    """
    Abre un archivo .txt con un running-config previamente guardado y lo
    restaura en la sucursal seleccionada vía SSH.

    Flujo:
      1. Seleccionar archivo .txt con el running-config.
      2. Mostrar vista previa y pedir confirmación.
      3. Conectar al switch y enviar los comandos (filtrando cabeceras).
      4. Guardar config en el switch (write memory).
    """
    if not _validate_sucursales(app): return
    targets = _get_selected_sucursales(app)
    if not targets: return
    sw = targets[0]   # restaurar de a una sucursal a la vez

    fn = filedialog.askopenfilename(
        title="Seleccionar running-config a restaurar",
        filetypes=[("Text", "*.txt"), ("All", "*.*")],
    )
    if not fn: return

    try:
        with open(fn, 'r', encoding='utf-8', errors='replace') as f:
            config_text = f.read()
    except Exception as e:
        messagebox.showerror("Error al leer archivo", str(e))
        return

    # Contar líneas de comandos reales (excluyendo vacías y comentarios)
    cmd_count = sum(
        1 for l in config_text.splitlines()
        if l.strip() and l.strip() != '!' and not l.startswith('#')
        and not l.startswith('Building') and not l.startswith('Current')
        and not l.startswith('version ')
    )

    _show_in_preview(app, config_text[:4000] + ("\n...(truncado)..." if len(config_text) > 4000 else ""))

    if not messagebox.askyesno(
        "Confirmar restauración",
        f"Archivo: {fn}\n\n"
        f"Se enviarán ~{cmd_count} comandos al switch:\n"
        f"  {sw['name']}  ({sw['ip']})\n\n"
        "La config actual del switch será reemplazada.\n"
        "¿Continuar?"
    ):
        return

    _log(app, "═" * 58)
    _log(app, f"  RESTAURANDO config en: {sw['name']}  |  {sw['ip']}")
    _log(app, f"  Archivo: {fn}")
    _log(app, f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _log(app, "═" * 58)

    success = restore_running_config(
        sw, config_text,
        log_fn=lambda msg: _log(app, msg),
    )

    _log(app, "═" * 58)
    if success:
        messagebox.showinfo("Restauración completada",
                            f"✔ Config restaurada exitosamente en:\n{sw['name']}  ({sw['ip']})")
    else:
        messagebox.showerror("Error en restauración",
                             f"✘ Ocurrió un error al restaurar la config en:\n{sw['name']}\n\n"
                             "Revisa el log de la pestaña ⑥ para más detalles.")


def _show_in_preview(app, text: str):
    """Muestra texto en el área de vista previa de la pestaña de backup."""
    app.backup_preview.delete("1.0", tk.END)
    app.backup_preview.insert(tk.END, text)


# ═══════════════════════════════════════════════════════════════════════════════
#  AWS S3 BACKUP
# ═══════════════════════════════════════════════════════════════════════════════

def _get_s3_client(app):
    """
    Crea y retorna un cliente boto3 de S3 con las credenciales ingresadas en la GUI.

    Retorna
    -------
    boto3.client : Cliente S3 listo para usar.

    Lanza
    -----
    ImportError  : Si boto3 no está instalado.
    ValueError   : Si faltan credenciales o bucket.
    Exception    : Si las credenciales son inválidas (botocore.ClientError).
    """
    try:
        import boto3
    except ImportError:
        raise ImportError(
            "boto3 no está instalado.\n"
            "Ejecuta en la terminal:\n"
            "  pip install boto3 --break-system-packages"
        )

    access_key = app.s3_access_key.get().strip()
    secret_key = app.s3_secret_key.get().strip()
    region     = app.s3_region.get().strip()
    bucket     = app.s3_bucket.get().strip()

    if not all([access_key, secret_key, region, bucket]):
        raise ValueError(
            "Completa todos los campos de AWS S3:\n"
            "Access Key ID, Secret Access Key, Región y Bucket."
        )

    # Crear cliente con credenciales explícitas (no usa el perfil ~/.aws/credentials)
    client = boto3.client(
        "s3",
        region_name          = region,
        aws_access_key_id    = access_key,
        aws_secret_access_key = secret_key,
    )
    return client, bucket


def verify_s3_credentials(app):
    """
    Verifica las credenciales S3 haciendo un 'head_bucket' (operación de bajo costo).
    Muestra un mensaje de éxito o error con detalle.
    """
    try:
        client, bucket = _get_s3_client(app)
        # head_bucket: verifica que el bucket existe y que tenemos acceso.
        # No descarga ni sube datos; costo AWS: $0.
        client.head_bucket(Bucket=bucket)
        messagebox.showinfo(
            "S3 OK ✔",
            f"Conexión exitosa al bucket:\n  s3://{bucket}\n\n"
            "Las credenciales son válidas."
        )
    except ImportError as e:
        messagebox.showerror("boto3 no instalado", str(e))
    except ValueError as e:
        messagebox.showwarning("Campos incompletos", str(e))
    except Exception as e:
        # botocore.exceptions.ClientError con código HTTP si son inválidas
        messagebox.showerror("Error S3", f"No se pudo conectar al bucket:\n{e}")


def backup_to_s3(app):
    """
    Sube el running-config de cada sucursal seleccionada a AWS S3.

    Flujo por sucursal:
      1. Conectar por SSH y obtener running-config (fetch_running_config).
      2. Construir la clave S3: <prefijo>/<hostname>/<YYYY-MM-DD_HH-MM-SS>.txt
      3. Subir el contenido (string → bytes UTF-8) con put_object.
      4. Registrar resultado en el log de la pestaña ⑥ si está disponible,
         y en la vista previa de ⑦.

    El bucket y las credenciales se toman de los campos de la UI.
    """
    if not _validate_sucursales(app): return
    targets = _get_selected_sucursales(app)
    if not targets: return

    # Validar credenciales antes de conectar a los switches
    try:
        client, bucket = _get_s3_client(app)
    except (ImportError, ValueError) as e:
        messagebox.showerror("Error S3", str(e))
        return

    prefix    = app.s3_prefix.get().strip().rstrip("/")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results   = []

    for sw in targets:
        sw_name = sw['name']
        try:
            # ── 1. Obtener running-config vía SSH ─────────────────────────────
            raw = fetch_running_config(sw)

            # ── 2. Construir clave S3 ─────────────────────────────────────────
            # Formato: backups/switches/SW-NOMBRE/2025-01-15_10-30-00.txt
            safe_name = sw_name.replace(" ", "_")
            s3_key    = f"{prefix}/{safe_name}/{timestamp}.txt"

            # ── 3. Encabezado con metadatos ───────────────────────────────────
            header = (
                f"# Backup generado por Configurador IOSvL2\n"
                f"# Sucursal : {sw_name}  ({sw['ip']})\n"
                f"# Fecha    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"# Bucket   : s3://{bucket}/{s3_key}\n"
                f"{'#'*60}\n\n"
            )
            content = (header + raw).encode("utf-8")

            # ── 4. Subir a S3 ─────────────────────────────────────────────────
            # ContentType text/plain para que S3 lo muestre correctamente en el navegador.
            # ServerSideEncryption AES256: cifrado en reposo dentro del bucket.
            client.put_object(
                Bucket               = bucket,
                Key                  = s3_key,
                Body                 = content,
                ContentType          = "text/plain; charset=utf-8",
                ServerSideEncryption = "AES256",  # cifrado en reposo (SSE-S3)
            )
            msg = f"  ✔ {sw_name} → s3://{bucket}/{s3_key}"
            results.append(msg)

        except Exception as e:
            msg = f"  ✘ {sw_name} → Error: {e}"
            results.append(msg)

    # ── Mostrar resultados ────────────────────────────────────────────────────
    summary = "\n".join(results)
    _show_in_preview(app, f"=== Backup S3 — {timestamp} ===\n\n{summary}")

    ok_count   = sum(1 for r in results if "✔" in r)
    fail_count = len(results) - ok_count
    messagebox.showinfo(
        "Backup S3 completado",
        f"Bucket: s3://{bucket}\n\n"
        f"✔ Exitosos : {ok_count}\n"
        f"✘ Fallidos : {fail_count}\n\n"
        + summary
    )
