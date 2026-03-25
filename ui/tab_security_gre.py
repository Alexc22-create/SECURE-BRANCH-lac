"""
ui/tab_security_gre.py — Pestañas ⑧ Seguridad  y  ⑨ GRE over IPsec
=====================================================================
Pestaña ⑧ Seguridad:
  - Enable secret (contraseña cifrada nivel 5)
  - Login block-for: bloqueo automático tras N intentos fallidos
  - Banner MOTD personalizable

Pestaña ⑨ GRE over IPsec:
  - Tunnel GRE (Tunnel0): source, destination, IPs del túnel
  - IKEv1 (ISAKMP): propuesta de fase 1 (encr, hash, auth, DH, lifetime)
  - IPsec: transform-set fase 2 + crypto map + bind a interfaz

Compatible con:
  vios_l2-ADVENTERPRISEK9-M, IOS 15.2(20200924:215240) — IOSvL2 experimental.
  NOTA: este firmware soporta GRE + IPsec en modo software.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import messagebox

from constants import (BG, BG2, BG3, ACCENT, ACCENT2, SUCCESS, WARN,
                       TEXT, TEXT2, BORDER)
from ui.widgets import (make_frame, make_label, make_entry, make_button,
                        make_labelframe, make_title, make_scrolled_text)
from ui.preview_window import show_preview


# ═══════════════════════════════════════════════════════════════════════════════
#  PESTAÑA ⑧ — SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

def build_tab_security(app, parent):
    """
    Construye la pestaña de Seguridad del dispositivo.

    Widgets creados en 'app':
      app.sec_enable_pw      : Entry — contraseña de enable (enable secret)
      app.sec_login_block    : Entry — segundos de bloqueo tras N intentos
      app.sec_login_attempts : Entry — número de intentos antes de bloquear
      app.sec_login_window   : Entry — ventana de tiempo para contar intentos (seg)
      app.sec_banner_text    : ScrolledText — texto libre del banner MOTD
    """
    make_title(parent, "🔐  Seguridad del Dispositivo")

    # ── Enable Secret ─────────────────────────────────────────────────────────
    # 'enable secret' usa MD5 (type 5); más seguro que 'enable password' (tipo 7).
    # En IOSvL2 15.2 se recomienda siempre usar 'secret' en lugar de 'password'.
    frm_enable = make_labelframe(parent, "🔑  Enable Secret  (cifrado MD5 — type 5)")
    frm_enable.pack(fill="x", padx=20, pady=6)
    make_label(frm_enable,
               "Contraseña de acceso a modo privilegiado (enable).",
               fg=TEXT2).pack(anchor="w")
    f = make_frame(frm_enable); f.pack(fill="x", pady=4)
    make_label(f, "Contraseña:", width=18).grid(row=0, column=0, sticky="w")
    app.sec_enable_pw = make_entry(f, width=30, show="*")
    app.sec_enable_pw.grid(row=0, column=1, padx=6)
    make_label(f, "(se aplica con 'enable secret')", fg=TEXT2,
               width=36).grid(row=0, column=2)

    # ── Login Block-for ───────────────────────────────────────────────────────
    # Sintaxis IOS: login block-for <seg_bloqueo> attempts <N> within <seg_ventana>
    # Ejemplo: login block-for 120 attempts 5 within 60
    #   → Si en 60 seg hay 5 intentos fallidos, bloquear VTY por 120 seg.
    frm_block = make_labelframe(parent,
        "🚫  Bloqueo por intentos fallidos  (login block-for)")
    frm_block.pack(fill="x", padx=20, pady=6)
    make_label(frm_block,
               "Bloquea el acceso VTY/SSH si se superan N intentos fallidos en una ventana de tiempo.",
               fg=TEXT2).pack(anchor="w")

    fg = make_frame(frm_block); fg.pack(fill="x", pady=4)
    # Intentos permitidos antes de bloquear
    make_label(fg, "Intentos máx:", width=18).grid(row=0, column=0, sticky="w")
    app.sec_login_attempts = make_entry(fg, width=8)
    app.sec_login_attempts.insert(0, "5")        # valor por defecto: 5 intentos
    app.sec_login_attempts.grid(row=0, column=1, padx=6)

    # Ventana de tiempo (segundos) en que se cuentan los intentos fallidos
    make_label(fg, "Ventana (seg):", width=18).grid(row=0, column=2, sticky="w")
    app.sec_login_window = make_entry(fg, width=8)
    app.sec_login_window.insert(0, "60")         # contar intentos en 60 segundos
    app.sec_login_window.grid(row=0, column=3, padx=6)

    # Tiempo de bloqueo tras superar el límite
    make_label(fg, "Bloquear (seg):", width=18).grid(row=0, column=4, sticky="w")
    app.sec_login_block = make_entry(fg, width=8)
    app.sec_login_block.insert(0, "120")         # bloquear 120 segundos = 2 minutos
    app.sec_login_block.grid(row=0, column=5, padx=6)

    make_label(frm_block,
               "Ejemplo → login block-for 120 attempts 5 within 60",
               fg=TEXT2).pack(anchor="w", pady=(0, 4))

    # ── Banner MOTD ───────────────────────────────────────────────────────────
    # MOTD = Message Of The Day; aparece ANTES del login en SSH/Telnet/consola.
    # Usar delimitador '#' que IOS acepta; el texto no puede contener '#'.
    # ADVERTENCIA LEGAL: es buena práctica incluir un aviso de "acceso no autorizado".
    frm_banner = make_labelframe(parent, "📢  Banner MOTD  (Message Of The Day)")
    frm_banner.pack(fill="x", padx=20, pady=6)
    make_label(frm_banner,
               "Mensaje mostrado antes del login por SSH/consola. No usar el carácter '#'.",
               fg=TEXT2).pack(anchor="w")

    app.sec_banner_text = make_scrolled_text(frm_banner, width=90, height=6)
    app.sec_banner_text.pack(padx=6, pady=4)

    # Banner de ejemplo con aviso legal (buena práctica en entornos corporativos)
    app.sec_banner_text.insert("1.0",
        "**********************************************************************\n"
        "*  ACCESO RESTRINGIDO - Solo personal autorizado                     *\n"
        "*  Toda actividad es monitoreada y registrada.                       *\n"
        "*  El acceso no autorizado es un delito y sera perseguido por ley.   *\n"
        "**********************************************************************"
    )

    # ── Botón de previsualización ─────────────────────────────────────────────
    make_button(parent, "👁  Ver comandos que se generarán",
                lambda: _preview_security_commands(app),
                color=BG3).pack(pady=8)


def _preview_security_commands(app):
    """Muestra en la ventana de vista previa los comandos IOS de seguridad."""
    cmds = build_security_commands(
        enable_pw     = app.sec_enable_pw.get().strip(),
        attempts      = app.sec_login_attempts.get().strip(),
        window        = app.sec_login_window.get().strip(),
        block_for     = app.sec_login_block.get().strip(),
        banner_text   = app.sec_banner_text.get("1.0", tk.END).strip(),
    )
    show_preview(
        app.root, "Seguridad — enable secret, login block-for, banner MOTD", cmds,
        note="Estos comandos se aplican al final de la ejecución "
             "para no interrumpir la sesión SSH activa.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PESTAÑA ⑨ — GRE OVER IPSEC
# ═══════════════════════════════════════════════════════════════════════════════

def build_tab_gre(app, parent):
    """
    Construye la pestaña de configuración GRE over IPsec.

    Arquitectura del túnel:
      Físico:  SW-local [Gi0/X] ←── GRE encapsulado en IPsec ──→ [Gi0/X] SW-remoto
      Lógico:  Tunnel0 (10.x.x.1) ──────────────────────────────── Tunnel0 (10.x.x.2)

    IKEv1 Fase 1 (ISAKMP): autentica los peers y negocia claves maestras.
    IPsec Fase 2 (ESP):     cifra los paquetes GRE reales con AES/SHA.

    Widgets creados en 'app':
      app.gre_tunnel_id      : Entry — número de interfaz de túnel (ej. 0)
      app.gre_local_src      : Entry — IP origen (interfaz física del SW local)
      app.gre_remote_dst     : Entry — IP destino (interfaz pública del peer)
      app.gre_tunnel_ip      : Entry — IP del túnel en el lado local (ej. 10.0.0.1)
      app.gre_tunnel_mask    : Entry — máscara del punto a punto del túnel
      app.gre_isakmp_key     : Entry — pre-shared key para autenticación IKE
      app.gre_isakmp_peer    : Entry — IP del peer IPsec (= gre_remote_dst usualmente)
      app.gre_map_name       : Entry — nombre del crypto map
      app.gre_map_seq        : Entry — número de secuencia del crypto map
      app.gre_bind_iface     : Entry — interfaz física donde se aplica el crypto map
      app.gre_list           : Listbox — túneles GRE configurados
      app.gre_tunnels        : list[dict] — estado en memoria
    """
    app.gre_tunnels = []   # estado en memoria: lista de configs de túnel

    make_title(parent, "🌐  GRE over IPsec  —  IOSvL2 15.2")
    make_label(parent,
               "Configura túneles GRE cifrados con IPsec (IKEv1 + ESP-AES-256/SHA).",
               fg=TEXT2).pack()

    # ── Sección: Interfaz de Túnel GRE ───────────────────────────────────────
    frm_gre = make_labelframe(parent, "📡  Interfaz de Túnel GRE")
    frm_gre.pack(fill="x", padx=20, pady=5)

    rows_gre = [
        ("Túnel ID (ej. 0):",         "gre_tunnel_id",   "0",               6),
        ("IP origen local (src):",     "gre_local_src",   "192.168.1.1",    15),
        ("IP destino peer (dst):",     "gre_remote_dst",  "200.0.0.2",      15),
        ("IP del túnel (local):",      "gre_tunnel_ip",   "10.100.0.1",     15),
        ("Máscara del túnel:",         "gre_tunnel_mask", "255.255.255.252", 15),
    ]
    for col, (label, attr, default, w) in enumerate(rows_gre):
        f = make_frame(frm_gre); f.pack(side="left", padx=10, pady=4)
        make_label(f, label, fg=TEXT2).pack(anchor="w")
        e = make_entry(f, width=w)
        e.insert(0, default)
        e.pack()
        setattr(app, attr, e)

    # ── Sección: IKEv1 / ISAKMP (Fase 1) ────────────────────────────────────
    # IKE Fase 1 negocia el canal seguro (SA de gestión) usando:
    #   encr aes 256 → cifrado AES-256 bits
    #   hash sha     → integridad SHA-1
    #   auth pre-share → autenticación por clave compartida (PSK)
    #   group 2      → Diffie-Hellman 1024 bits (el máx en IOSvL2 15.2)
    #   lifetime 86400 → SA válida 24 horas antes de renegociar
    frm_ike = make_labelframe(parent, "🔒  IKEv1 / ISAKMP  (Fase 1 — autenticación de peers)")
    frm_ike.pack(fill="x", padx=20, pady=5)
    make_label(frm_ike,
               "Pre-shared key (PSK): la misma en ambos extremos del túnel.",
               fg=TEXT2).pack(anchor="w")

    fi = make_frame(frm_ike); fi.pack(fill="x", pady=4)
    make_label(fi, "Pre-shared Key:", width=20).grid(row=0, column=0, sticky="w")
    app.gre_isakmp_key = make_entry(fi, width=28, show="*")
    app.gre_isakmp_key.grid(row=0, column=1, padx=6)

    make_label(fi, "IP del peer IPsec:", width=20).grid(row=0, column=2, sticky="w")
    app.gre_isakmp_peer = make_entry(fi, width=16)
    app.gre_isakmp_peer.insert(0, "200.0.0.2")
    app.gre_isakmp_peer.grid(row=0, column=3, padx=6)

    make_label(frm_ike,
               "Propuesta fija: encr aes 256 | hash sha | auth pre-share | group 2 | lifetime 86400",
               fg=TEXT2).pack(anchor="w", pady=(0, 4))

    # ── Sección: Crypto Map (Fase 2 — IPsec) ─────────────────────────────────
    # El crypto map une:
    #   - La ACL que define el tráfico a cifrar (el GRE en este caso)
    #   - El transform-set (ESP-AES-256 + ESP-SHA-HMAC)
    #   - El peer (dirección IP del otro extremo)
    # Luego se aplica a la interfaz física de salida (el uplink o la WAN).
    frm_map = make_labelframe(parent,
        "🗺  Crypto Map  (Fase 2 — transform-set ESP-AES-256 / ESP-SHA)")
    frm_map.pack(fill="x", padx=20, pady=5)

    fm = make_frame(frm_map); fm.pack(fill="x", pady=4)
    make_label(fm, "Nombre del crypto map:", width=22).grid(row=0, column=0, sticky="w")
    app.gre_map_name = make_entry(fm, width=20)
    app.gre_map_name.insert(0, "CMAP_GRE")
    app.gre_map_name.grid(row=0, column=1, padx=6)

    make_label(fm, "Secuencia:", width=12).grid(row=0, column=2, sticky="w")
    app.gre_map_seq = make_entry(fm, width=6)
    app.gre_map_seq.insert(0, "10")
    app.gre_map_seq.grid(row=0, column=3, padx=6)

    make_label(fm, "Interfaz física (bind):", width=22).grid(row=0, column=4, sticky="w")
    app.gre_bind_iface = make_entry(fm, width=22)
    app.gre_bind_iface.insert(0, "GigabitEthernet0/1")
    app.gre_bind_iface.grid(row=0, column=5, padx=6)

    make_label(frm_map,
               "Transform-set fijo: esp-aes 256 + esp-sha-hmac | mode transport",
               fg=TEXT2).pack(anchor="w", pady=(0, 4))

    # ── Botones: Agregar / Eliminar túnel ────────────────────────────────────
    bf = make_frame(parent); bf.pack(pady=6)
    make_button(bf, "➕  Agregar túnel GRE",
                lambda: _add_gre_tunnel(app), color=SUCCESS).grid(row=0, column=0, padx=8)
    make_button(bf, "🗑  Eliminar seleccionado",
                lambda: _del_gre_tunnel(app), color="#6e2020").grid(row=0, column=1, padx=8)
    make_button(bf, "👁  Ver comandos IOS",
                lambda: _preview_gre_commands(app), color=BG3).grid(row=0, column=2, padx=8)

    # ── Listbox de túneles configurados ─────────────────────────────────────
    make_label(parent, "Túneles GRE configurados:").pack(anchor="w", padx=20, pady=(6, 2))
    app.gre_list = tk.Listbox(parent, bg=BG3, fg=TEXT, selectbackground=ACCENT,
                               font=("Consolas", 10), height=6, width=100,
                               relief="flat", bd=0)
    app.gre_list.pack(padx=20, pady=2)


def _add_gre_tunnel(app):
    """Valida campos y agrega una configuración de túnel GRE a la lista en memoria."""
    tid   = app.gre_tunnel_id.get().strip()
    src   = app.gre_local_src.get().strip()
    dst   = app.gre_remote_dst.get().strip()
    tip   = app.gre_tunnel_ip.get().strip()
    tmask = app.gre_tunnel_mask.get().strip()
    psk   = app.gre_isakmp_key.get().strip()
    peer  = app.gre_isakmp_peer.get().strip()
    mname = app.gre_map_name.get().strip()
    mseq  = app.gre_map_seq.get().strip()
    biface = app.gre_bind_iface.get().strip()

    # Validar campos obligatorios
    if not all([tid, src, dst, tip, tmask, psk, peer, mname, mseq, biface]):
        messagebox.showwarning("Campos incompletos",
                               "Completa todos los campos del túnel GRE.")
        return

    entry = {
        "tunnel_id": tid, "src": src, "dst": dst,
        "tunnel_ip": tip, "tunnel_mask": tmask,
        "psk": psk, "peer": peer,
        "map_name": mname, "map_seq": mseq,
        "bind_iface": biface,
    }
    app.gre_tunnels.append(entry)

    # Mostrar en el listbox (sin la PSK por seguridad)
    app.gre_list.insert(tk.END,
        f"  Tunnel{tid}  {tip}/{tmask}  src:{src}→dst:{dst}  "
        f"peer:{peer}  map:{mname}/{mseq}  bind:{biface}")


def _del_gre_tunnel(app):
    """Elimina el túnel seleccionado en el listbox."""
    sel = app.gre_list.curselection()
    if not sel:
        messagebox.showwarning("Sin selección", "Selecciona un túnel para eliminar.")
        return
    idx = sel[0]
    app.gre_tunnels.pop(idx)
    app.gre_list.delete(idx)


def _preview_gre_commands(app):
    """Muestra en la ventana de vista previa los comandos IOS de GRE over IPsec."""
    cmds = build_gre_ipsec_commands(app.gre_tunnels)
    show_preview(
        app.root, "GRE over IPsec — ISAKMP, Crypto Map, Tunnel", cmds,
        note="Las PSKs aparecen en texto plano aquí. "
             "No compartas esta vista previa.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  GENERADORES DE COMANDOS IOS
#  (sin dependencias de tkinter — solo reciben dicts con parámetros)
# ═══════════════════════════════════════════════════════════════════════════════

def build_security_commands(
    enable_pw: str,
    attempts: str,
    window: str,
    block_for: str,
    banner_text: str,
) -> list:
    """
    Genera comandos IOS para:
      - enable secret (type 5 / MD5)
      - login block-for (bloqueo tras intentos fallidos)
      - banner motd (aviso de acceso)

    Compatible con IOSvL2 15.2(20200924:215240).

    Parámetros
    ----------
    enable_pw   : Contraseña de enable. Se usa 'enable secret' (MD5 type-5).
    attempts    : Número de intentos fallidos antes de bloquear.
    window      : Ventana en segundos para contar los intentos.
    block_for   : Segundos que el switch bloquea el acceso tras superar intentos.
    banner_text : Texto libre del banner MOTD. No debe contener '#'.

    Retorna
    -------
    list : Comandos IOS en orden listo para enviar.
    """
    cmds = []

    # ── Enable Secret ─────────────────────────────────────────────────────────
    # 'enable secret' almacena la contraseña con MD5 (type 5) en el running-config.
    # Es más seguro que 'enable password' que usa cifrado reversible (type 7).
    if enable_pw:
        cmds.append(f"enable secret {enable_pw}")

    # ── Login Block-For ───────────────────────────────────────────────────────
    # Requiere que 'login on-failure' esté activo (lo activa automáticamente en IOS 15.x).
    # Bloquea VTY/SSH completo durante 'block_for' segundos si se superan 'attempts'
    # intentos fallidos dentro de la ventana 'window' (en segundos).
    if attempts and window and block_for:
        try:
            # Validar que sean números enteros positivos
            a, w, b = int(attempts), int(window), int(block_for)
            if a > 0 and w > 0 and b > 0:
                cmds.append(f"login block-for {b} attempts {a} within {w}")
                # Registrar intentos fallidos en syslog (buena práctica)
                cmds.append("login on-failure log")
        except ValueError:
            pass   # Si no son números, simplemente se omite

    # ── Banner MOTD ───────────────────────────────────────────────────────────
    # IOS usa un delimitador para marcar inicio/fin del banner.
    # Se usa '#' como delimitador; se reemplaza '#' del texto por '*' para evitar conflicto.
    if banner_text:
        safe_text = banner_text.replace('#', '*')
        cmds.append(f"banner motd #{safe_text}#")

    return cmds


def build_gre_ipsec_commands(tunnels: list) -> list:
    """
    Genera comandos IOS completos para GRE over IPsec.

    Para cada túnel en la lista genera:
      1. ISAKMP policy (Fase 1 IKE)
      2. ISAKMP key (PSK para el peer)
      3. ACL para el tráfico GRE (tráfico entre src y dst)
      4. IPsec transform-set (Fase 2: ESP-AES-256 + ESP-SHA-HMAC)
      5. Crypto map (une ACL + transform-set + peer)
      6. Bind del crypto map a la interfaz física de salida
      7. Interfaz Tunnel (GRE puro; IPsec cifra transparentemente)

    Por qué GRE + IPsec y no solo IPsec?
    → IPsec no puede encapsular tráfico multicast/broadcast por sí solo.
      GRE crea un túnel punto a punto que sí permite multicast (necesario para
      OSPF, EIGRP, etc.) y luego IPsec cifra el túnel GRE completo.

    Compatible con IOSvL2 15.2 — grupo DH máximo soportado: group 2 (1024 bits).

    Parámetros
    ----------
    tunnels : lista de dicts con claves:
        tunnel_id, src, dst, tunnel_ip, tunnel_mask,
        psk, peer, map_name, map_seq, bind_iface

    Retorna
    -------
    list : Comandos IOS en orden correcto.
    """
    cmds = []

    for idx, t in enumerate(tunnels):
        tid   = t['tunnel_id']
        src   = t['src']
        dst   = t['dst']
        tip   = t['tunnel_ip']
        tmask = t['tunnel_mask']
        psk   = t['psk']
        peer  = t['peer']
        mname = t['map_name']
        mseq  = t['map_seq']
        biface = t['bind_iface']

        # Nombre único para el transform-set y la ACL de este túnel
        ts_name  = f"TS_GRE_{tid}"         # ej. TS_GRE_0
        acl_name = f"ACL_GRE_{tid}"        # ej. ACL_GRE_0
        policy_n = 10 + idx                # ISAKMP policy 10, 11, 12…

        # ── Fase 1: ISAKMP Policy ─────────────────────────────────────────────
        # Negocia el canal IKE seguro entre los dos peers.
        # IOSvL2 15.2 máximo: group 2 (DH 1024 bits).
        cmds += [
            f"crypto isakmp policy {policy_n}",
            " encr aes 256",           # cifrado AES de 256 bits
            " hash sha",               # integridad SHA-1
            " authentication pre-share",  # autenticación por clave compartida
            " group 2",                # Diffie-Hellman group 2 (1024 bits)
            " lifetime 86400",         # SA válida 24 horas
            "exit",
        ]

        # ── Fase 1: ISAKMP Key (PSK) ──────────────────────────────────────────
        # La misma PSK debe configurarse en el peer remoto con el IP invertido.
        cmds.append(f"crypto isakmp key {psk} address {peer}")

        # ── ACL para el tráfico GRE que IPsec debe cifrar ─────────────────────
        # IPsec necesita saber QUÉ tráfico cifrar.
        # GRE usa protocolo IP número 47; por eso se hace 'permit gre'.
        cmds += [
            f"ip access-list extended {acl_name}",
            f" permit gre host {src} host {dst}",   # cifrar solo el GRE entre estos dos extremos
            "exit",
        ]

        # ── Fase 2: Transform-Set ─────────────────────────────────────────────
        # Define los algoritmos de cifrado e integridad para los paquetes reales.
        # mode transport: solo cifra el payload (no el header IP externo),
        #                 porque GRE ya añade su propio header de transporte.
        cmds += [
            f"crypto ipsec transform-set {ts_name} esp-aes 256 esp-sha-hmac",
            f" mode transport",   # transport mode: cifra el payload GRE, no el IP header
            "exit",
        ]

        # ── Crypto Map ────────────────────────────────────────────────────────
        # Une: peer + ACL + transform-set. Se aplica a la interfaz de salida.
        cmds += [
            f"crypto map {mname} {mseq} ipsec-isakmp",
            f" set peer {peer}",
            f" set transform-set {ts_name}",
            f" match address {acl_name}",
            "exit",
        ]

        # ── Bind Crypto Map a interfaz física ─────────────────────────────────
        # El crypto map debe aplicarse en la interfaz por donde sale el tráfico WAN.
        # NUNCA se aplica sobre el uplink interno (Gi0/0 protegido).
        cmds += [
            f"interface {biface}",
            f" crypto map {mname}",
            "exit",
        ]

        # ── Interfaz de Túnel GRE ─────────────────────────────────────────────
        # El túnel GRE es una interfaz virtual punto a punto.
        # 'tunnel mode gre ip' = encapsulación GRE sobre IPv4.
        # Una vez que el crypto map está en la interfaz física, todo GRE
        # que pase por ella queda automáticamente cifrado con IPsec.
        cmds += [
            f"interface Tunnel{tid}",
            f" ip address {tip} {tmask}",
            f" tunnel source {src}",
            f" tunnel destination {dst}",
            " tunnel mode gre ip",     # modo GRE sobre IPv4 (el modo por defecto en IOS)
            " no shutdown",
            "exit",
        ]

    return cmds
