"""
core/command_builder.py — Generador de comandos IOS
====================================================
Convierte la configuración definida en la GUI (VLANs, DHCP, rutas, QoS)
en listas de comandos IOS listos para enviarse al switch.

No depende de tkinter; es pura lógica de negocio.
Esto facilita probar la generación de comandos sin abrir la interfaz gráfica.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import re
from constants import UPLINK_IFACE


def expand_ports(ports_str: str) -> str:
    """
    Normaliza nombres de interfaces a la forma completa que espera IOS 15.x.

    Acepta notación corta o larga:
      - "Gi0/1-3"     → "GigabitEthernet0/1-3"
      - "Gi0/1,Gi0/3" → "GigabitEthernet0/1, GigabitEthernet0/3"
      - "Fa0/2"       → "FastEthernet0/2"

    IOS acepta 'interface range' con nombre completo; la forma corta 'Gi' a veces
    genera errores según la versión del firmware, por eso normalizamos aquí.
    """
    parts  = [p.strip() for p in ports_str.split(',')]
    result = []
    for p in parts:
        m = re.match(
            r'^(gi(?:gabitethernet)?|fa(?:stethernet)?)(\d+)/(\d+)(?:-(\d+))?$',
            p, re.IGNORECASE)
        if m:
            prefix       = m.group(1).lower()
            mod, start   = m.group(2), m.group(3)
            end          = m.group(4)
            # Elegir el nombre largo según el tipo de interfaz
            full = (f"GigabitEthernet{mod}/{start}"
                    if prefix.startswith('gi') else
                    f"FastEthernet{mod}/{start}")
            if end:
                full += f"-{end}"   # rango: GigabitEthernet0/1-3
            result.append(full)
        else:
            result.append(p)        # ya viene en formato correcto o es desconocido
    return ', '.join(result)


def build_commands(
    is_l3: bool,
    chk_intervlan: bool,
    dhcp_pools: list,
    vlans_data: list,
    static_routes: list,
    chk_ospf: bool,
    ospf_pid: str,
    ospf_networks: list,
    qos_classes: list,
    pol_entries: list,
    pol_name: str,
    service_policies: list,
    log_fn=None,
) -> list:
    """
    Genera la lista completa de comandos IOS en modo configuración global.

    Parámetros
    ----------
    is_l3          : True si el switch tiene ip routing activo (detectado automáticamente).
    chk_intervlan  : Si el usuario marcó "Activar ip routing" en la pestaña de enrutamiento.
    dhcp_pools     : Lista de dicts {name, net, mask, gw}.
    vlans_data     : Lista de dicts con config de cada VLAN.
    static_routes  : Lista de dicts {dest, mask, nexthop}.
    chk_ospf       : Si OSPF está habilitado en la UI.
    ospf_pid       : PID del proceso OSPF (ej. "1").
    ospf_networks  : Lista de dicts {network, wildcard, area}.
    qos_classes    : Lista de dicts de class-maps.
    pol_entries    : Lista de dicts {class, action, value}.
    pol_name       : Nombre de la policy-map.
    service_policies: Lista de dicts {iface, dir, policy}.
    log_fn         : Función de logging opcional (ej. self.log). Si None, no loguea.

    Retorna
    -------
    list : Comandos IOS en orden correcto para enviar al switch.
    """
    cmds = []

    # ── 1. ip routing (solo switches Layer 3) ─────────────────────────────────
    # En switches L2 este comando no existe; se omite automáticamente.
    if chk_intervlan and is_l3:
        cmds += ["ip routing", "service dhcp"]
    elif not is_l3 and log_fn:
        log_fn("  [INFO] Switch L2 detectado → se omite 'ip routing' y SVIs con IP")

    # ── 2. DHCP pools (solo switches L3) ──────────────────────────────────────
    # En switches L2, el DHCP lo gestiona R1 (router-on-a-stick).
    # Para cada pool se excluye la IP del gateway antes de definir el rango.
    if is_l3:
        for pool in dhcp_pools:
            cmds.append(f"ip dhcp excluded-address {pool['gw']}")   # excluir gateway
            cmds += [
                f"ip dhcp pool {pool['name']}",
                f"network {pool['net']} {pool['mask']}",
                f"default-router {pool['gw']}",
                "dns-server 8.8.8.8",    # DNS público por defecto
                "exit"
            ]

    # ── 3. VLANs ──────────────────────────────────────────────────────────────
    # IOS 15.x usa "conf t → vlan X → name Y", NO "vlan database" (formato antiguo).
    for v in vlans_data:
        cmds.append(f"vlan {v['id']}")
        if v['name']:
            cmds.append(f"name {v['name']}")
        cmds.append("exit")

    # ── 4. Asignación de puertos a VLANs ──────────────────────────────────────
    # 'interface range' funciona de forma nativa en IOS 15.x para aplicar
    # la misma config a varios puertos en un solo bloque.
    for v in vlans_data:
        if v['assign_ports'] and v['ports']:
            ports_norm = expand_ports(v['ports'])

            # Elegir entre 'interface range' (múltiples) o 'interface' (único)
            is_range = ',' in ports_norm or re.search(r'-\d+$', ports_norm.split('/')[-1])
            iface_cmd = f"interface range {ports_norm}" if is_range else f"interface {ports_norm}"
            cmds.append(iface_cmd)

            if v['port_mode'] == 'trunk':
                # Trunk: permite pasar múltiples VLANs (conexión entre switches / router)
                cmds += [
                    "switchport trunk encapsulation dot1q",
                    "switchport mode trunk",
                    f"switchport trunk allowed vlan add {v['id']}",
                    "no shutdown",
                    "exit"
                ]
            else:
                # Access: un solo VLAN por puerto (usuarios finales)
                # portfast evita los 30 seg de STP al conectar un PC
                cmds += [
                    "switchport mode access",
                    f"switchport access vlan {v['id']}",
                    "spanning-tree portfast",
                    "no shutdown",
                    "exit"
                ]

    # ── 5. ACLs de seguridad ──────────────────────────────────────────────────
    # Se crean ACLs extendidas nombradas (una por VLAN que las necesite).
    # Las ACLs se aplican a la SVI en el paso siguiente (solo L3).
    for v in vlans_data:
        acl_name  = f"SEGURIDAD_VLAN_{v['id']}"
        needs_acl = v['block_social'] or v['custom_acl']
        if needs_acl:
            cmds.append(f"ip access-list extended {acl_name}")
            if v['block_social']:
                # Bloquear Facebook y Twitter por IP pública conocida (HTTPS/443)
                cmds += [
                    "deny tcp any host 157.240.22.35 eq 443",   # Facebook
                    "deny tcp any host 104.244.42.1  eq 443",   # Twitter/X
                ]
            if v['custom_acl']:
                # Reglas personalizadas ingresadas por el usuario (una por línea)
                cmds += [r.strip() for r in v['custom_acl'].split('\n') if r.strip()]
            cmds += ["permit ip any any", "exit"]   # permitir todo lo demás

    # ── 6. SVIs — Switch Virtual Interfaces (solo L3) ─────────────────────────
    # La SVI es la IP virtual del switch para esa VLAN; actúa como gateway.
    # En L2 no hay SVIs con IP; el gateway está en R1.
    if is_l3:
        for v in vlans_data:
            acl_name  = f"SEGURIDAD_VLAN_{v['id']}"
            needs_acl = v['block_social'] or v['custom_acl']
            svi_ip = svi_mask = None
            if v['dhcp_idx'] is not None:
                # Tomar la IP de gateway del pool DHCP asociado a esta VLAN
                p = dhcp_pools[v['dhcp_idx']]
                svi_ip, svi_mask = p['gw'], p['mask']
            if svi_ip or needs_acl:
                cmds.append(f"interface vlan {v['id']}")
                if svi_ip:
                    cmds += [f"ip address {svi_ip} {svi_mask}", "no shutdown"]
                if needs_acl:
                    # Aplicar la ACL en dirección entrante a la SVI
                    cmds.append(f"ip access-group {acl_name} in")
                cmds.append("exit")

    # ── 7. Rutas estáticas ────────────────────────────────────────────────────
    # Incluye la ruta por defecto (0.0.0.0/0 → R1) y rutas entre sucursales.
    for rt in static_routes:
        cmds.append(f"ip route {rt['dest']} {rt['mask']} {rt['nexthop']}")

    # ── 8. OSPF ───────────────────────────────────────────────────────────────
    # Anuncia las redes de las VLANs a R1 para que pueda hacer NAT a internet.
    # Sin esto, las nuevas VLANs no tendrán acceso a internet vía OSPF.
    if chk_ospf and ospf_networks:
        pid = ospf_pid.strip() or "1"
        cmds.append(f"router ospf {pid}")
        for n in ospf_networks:
            cmds.append(f"network {n['network']} {n['wildcard']} area {n['area']}")
        cmds.append("exit")

    # ── 9. QoS — class-maps ───────────────────────────────────────────────────
    # Cada class-map identifica un tipo de tráfico (por DSCP, IP, ACL, etc.).
    for cls in qos_classes:
        cmds += [
            f"class-map {cls['match_type']} {cls['name']}",
            f"match {cls['criteria']} {cls['value']}",
            "exit"
        ]

    # ── 10. QoS — policy-map ─────────────────────────────────────────────────
    # La policy-map define qué hacer con cada clase de tráfico:
    #   priority  → cola de alta prioridad (voz/video)
    #   bandwidth → garantía de ancho de banda mínimo
    #   police    → limitar tasa (descartar exceso)
    #   shape     → suavizar tráfico (buffer + retraso)
    #   set dscp  → re-marcar el DSCP del paquete
    if pol_entries and pol_name:
        cmds.append(f"policy-map {pol_name}")
        for pe in pol_entries:
            cmds.append(f"class {pe['class']}")
            a, v = pe['action'], pe['value']
            if   a == "police rate":     cmds += [f"police rate {v} bps", "exit"]
            elif a == "shape average":   cmds += [f"shape average {v}",   "exit"]
            elif a == "set dscp":        cmds += [f"set dscp {v}",        "exit"]
            else:                        cmds += [f"{a} {v}",             "exit"]
        cmds.append("exit")

    # ── 11. QoS — service-policy ─────────────────────────────────────────────
    # Asocia la policy-map a una interfaz de acceso (input/output/both).
    # NUNCA se aplica sobre el uplink (Gi0/0), que está protegido.
    for sp in service_policies:
        cmds += [
            f"interface {sp['iface']}",
            f"service-policy {sp['dir']} {sp['policy']}",
            "exit"
        ]

    return cmds


def build_cleanup_commands(nc, static_routes: list, ospf_networks: list, log_fn=None) -> list:
    """
    Lee el running-config del switch y genera comandos 'no ...' para limpiar
    únicamente lo que esta aplicación puede haber configurado previamente.

    Protege:
      - SSH, usuarios, VTY, crypto key (acceso remoto)
      - Interfaz de uplink (UPLINK_IFACE)
      - Rutas estáticas y redes OSPF que NO fueron configuradas por esta app
      - VLAN 1 (nativa, no se borra)

    Parámetros
    ----------
    nc            : Conexión Netmiko activa (ya en modo enable).
    static_routes : Rutas que la app configuró (para saber cuáles borrar).
    ospf_networks : Redes OSPF que la app configuró (ídem).
    log_fn        : Función de logging opcional.

    Retorna
    -------
    list : Comandos de limpieza listos para enviar al switch.
    """
    if log_fn:
        log_fn("  Leyendo running-config para limpieza...")
    raw     = nc.send_command("show running-config", delay_factor=3)
    cleanup = []

    # ── DHCP pools y exclusiones ──────────────────────────────────────────────
    for p in re.findall(r'^ip dhcp pool (\S+)', raw, re.MULTILINE):
        cleanup.append(f"no ip dhcp pool {p}")
    for e in re.findall(r'^ip dhcp excluded-address (.+)', raw, re.MULTILINE):
        cleanup.append(f"no ip dhcp excluded-address {e.strip()}")

    # ── ACLs nombradas de seguridad ───────────────────────────────────────────
    # Solo se borran las que tienen el prefijo "SEGURIDAD_VLAN_" que usa esta app.
    for a in re.findall(r'^ip access-list extended (SEGURIDAD_VLAN_\S+)', raw, re.MULTILINE):
        cleanup.append(f"no ip access-list extended {a}")

    # ── service-policy en interfaces ──────────────────────────────────────────
    for iface, body in re.findall(r'^interface (\S+)\n((?:[ \t].+\n)*)', raw, re.MULTILINE):
        if 'service-policy' in body:
            for d, pm in re.findall(r'service-policy (\S+) (\S+)', body):
                cleanup += [f"interface {iface}", f"no service-policy {d} {pm}", "exit"]

    # ── policy-map y class-map ────────────────────────────────────────────────
    for pm in re.findall(r'^policy-map (\S+)', raw, re.MULTILINE):
        cleanup.append(f"no policy-map {pm}")
    for cm in re.findall(r'^class-map \S+ (\S+)', raw, re.MULTILINE):
        cleanup.append(f"no class-map {cm}")

    # ── SVIs (interfaces VLAN) ────────────────────────────────────────────────
    # Se quita la IP y la ACL de cada SVI, excepto VLAN 1 (nativa del switch).
    for iface, vid, body in re.findall(
            r'^interface (Vlan(\d+))\n((?:[ \t].+\n)*)', raw, re.MULTILINE):
        if vid == "1":
            continue   # VLAN 1 es la VLAN de gestión, no se toca
        if 'ip address' in body:
            cleanup += [f"interface {iface}", "no ip address", "exit"]
        if 'ip access-group' in body:
            ag = re.search(r'ip access-group (\S+)', body)
            if ag:
                cleanup += [f"interface {iface}", f"no ip access-group {ag.group(1)} in", "exit"]

    # ── Puertos (modo acceso/trunk) ───────────────────────────────────────────
    # Se resetea el modo de cada puerto, excepto el uplink y las SVIs.
    for iface, body in re.findall(
            r'^interface (\S+)\n((?:[ \t].+\n)*)', raw, re.MULTILINE):
        if 'Vlan' in iface:
            continue   # saltar SVIs (ya manejadas arriba)
        if UPLINK_IFACE.lower() in iface.lower():
            continue   # NUNCA tocar el uplink
        if 'switchport access vlan' in body:
            cleanup += [f"interface {iface}", "no switchport access vlan",
                        "no switchport mode", "exit"]
        elif 'switchport mode trunk' in body:
            cleanup += [f"interface {iface}", "no switchport mode trunk", "exit"]

    # ── VLANs ─────────────────────────────────────────────────────────────────
    # IOS 15.x: "no vlan X" en conf-t elimina la VLAN y la quita de todos los puertos.
    vlan_raw = nc.send_command("show vlan brief", delay_factor=2)
    for vid in re.findall(r'^(\d+)\s+\S+\s+active', vlan_raw, re.MULTILINE):
        if vid != "1":
            cleanup.append(f"no vlan {vid}")

    # ── Rutas estáticas ───────────────────────────────────────────────────────
    # SOLO se borran las rutas que la app puso. Rutas preexistentes (ej: ruta por defecto
    # manual hacia R1) NO se tocan para proteger la conectividad del switch.
    for rt in static_routes:
        rt_str = f"{rt['dest']} {rt['mask']} {rt['nexthop']}"
        if f"ip route {rt_str}" in raw:   # verificar que realmente existe
            cleanup.append(f"no ip route {rt_str}")

    # ── OSPF — solo network statements conocidos ──────────────────────────────
    # NUNCA se borra el proceso OSPF completo ni redes preexistentes (uplinks, loopbacks).
    # Solo se quitan los 'network' que esta app configuró anteriormente.
    pid_m = re.search(r'^router ospf (\d+)', raw, re.MULTILINE)
    if pid_m and ospf_networks:
        pid = pid_m.group(1)
        for n in ospf_networks:
            net_str = f"{n['network']} {n['wildcard']} area {n['area']}"
            if net_str in raw:
                cleanup += [f"router ospf {pid}", f"no network {net_str}", "exit"]

    return cleanup
