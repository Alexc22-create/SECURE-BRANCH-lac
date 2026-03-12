"""
core/connector.py — Conexión SSH y ejecución en switches
=========================================================
Encapsula toda la lógica de Netmiko:
  - Crear parámetros de conexión
  - Detectar Layer 2 vs Layer 3
  - Enviar comandos uno a uno con logging y manejo de errores
  - Aplicar o limpiar configuración en un switch
  - Descargar el running-config (backup)

Este módulo no depende de tkinter; recibe una función de log como parámetro
para poder usarse tanto desde la GUI como desde scripts de línea de comandos.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import re
import time
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

from constants import UPLINK_IFACE
from core.command_builder import build_commands, build_cleanup_commands


def make_device_params(sw: dict) -> dict:
    """
    Construye el diccionario de parámetros que Netmiko necesita para conectarse.

    Parámetros
    ----------
    sw : dict con claves {ip, user, pass, secret}

    Retorna
    -------
    dict con todos los parámetros de ConnectHandler para Cisco IOS.
    """
    return {
        'device_type':           'cisco_ios',
        'host':                  sw['ip'],
        'username':              sw['user'],
        'password':              sw['pass'],
        'secret':                sw['secret'],
        'global_delay_factor':   2,           # factor de espera global entre comandos
        'read_timeout_override': 60,          # timeout de lectura en segundos
        'fast_cli':              True,         # modo rápido (reduce delays por defecto)
    }


def detect_l3(nc) -> bool:
    """
    Detecta si el switch tiene ip routing activo (Layer 3) o no (Layer 2).

    Estrategia: ejecuta 'show ip route connected' y busca líneas que comiencen
    con 'C' (ruta directamente conectada). Si las hay, el switch enruta.

    Parámetros
    ----------
    nc : Conexión Netmiko activa (en modo enable).

    Retorna
    -------
    bool : True = Layer 3 (ip routing activo), False = Layer 2.
    """
    try:
        out = nc.send_command("show ip route connected", delay_factor=2)
        return bool(re.search(r'^C\s+', out, re.MULTILINE))
    except Exception:
        return False   # Si falla, asumimos L2 por seguridad


def send_cmd_by_cmd(nc, commands: list, log_fn=None):
    """
    Envía una lista de comandos IOS al switch de forma individual,
    con esperas adaptativas y manejo de errores por comando.

    Por qué comando a comando y no config_mode + send_config_set?
    → Algunos comandos (OSPF, ip route) recalculan la tabla de routing
      y necesitan más tiempo. Este método ajusta el delay por comando.

    Parámetros
    ----------
    nc       : Conexión Netmiko activa (ya en modo config o enable).
    commands : Lista de strings con comandos IOS.
    log_fn   : Función de log opcional. Signature: log_fn(str).
    """
    for idx, cmd in enumerate(commands):
        if log_fn:
            log_fn(f"  [{idx+1}/{len(commands)}] {cmd}")

        # Comandos lentos: routing/OSPF recalculan SPF o tablas de enrutamiento.
        # Necesitan más delay para que el switch procese sin errores.
        is_slow = any(k in cmd.lower() for k in
                      ("ospf", "network", "router", "ip route", "no router"))
        delay        = 6   if is_slow else 2
        read_timeout = 120 if is_slow else 60

        try:
            out = nc.send_command_timing(
                cmd,
                delay_factor=delay,
                read_timeout=read_timeout,
                strip_prompt=False,
                strip_command=False,
            )
            # Mostrar respuesta solo si hay algo relevante (warnings, errores IOS, etc.)
            if out.strip() and log_fn:
                log_fn(f"    -> {out.strip()[:200]}")

            # Pausa extra para comandos lentos (evita que el siguiente comando
            # llegue antes de que el switch termine de procesar)
            time.sleep(1.0 if is_slow else 0.15)

        except Exception as e:
            if log_fn:
                log_fn(f"  [ERROR] '{cmd}' -> {str(e)[:120]}")
            time.sleep(2)
            # Intentar recuperar el canal (puede haberse quedado esperando input)
            try:
                nc.write_channel("\n")
                time.sleep(1)
                nc.read_channel()
            except Exception:
                if log_fn:
                    log_fn("  [FATAL] Socket cerrado, abortando este switch.")
                raise   # propagar para que _run_on_switch lo capture


def run_on_switch(sw: dict, config_params: dict, do_clean: bool = False, log_fn=None) -> bool:
    """
    Conecta a un switch y le aplica la configuración completa.

    Flujo:
      1. Conectar por SSH y entrar a modo enable.
      2. Detectar si es Layer 2 o Layer 3.
      3. Opcional: limpiar config previa (sin tocar SSH/acceso remoto).
      4. Generar y enviar los comandos de configuración.
      5. Guardar la config (write memory / copy run start).
      6. Desconectar.

    Parámetros
    ----------
    sw            : dict con {name, ip, user, pass, secret}.
    config_params : dict con todos los parámetros de build_commands()
                    (dhcp_pools, vlans_data, etc.).
    do_clean      : Si True, limpia la config anterior antes de aplicar.
    log_fn        : Función de log opcional.

    Retorna
    -------
    bool : True si la operación fue exitosa, False si hubo algún error.
    """
    if log_fn:
        log_fn(f"\n{'─'*56}")
        log_fn(f"  Sucursal: {sw['name']}  |  {sw['ip']}")
        log_fn(f"{'─'*56}")
    try:
        nc       = ConnectHandler(**make_device_params(sw))
        nc.enable()
        hostname = nc.find_prompt().replace("#", "").strip()
        is_l3    = detect_l3(nc)
        layer    = "Layer 3" if is_l3 else "Layer 2"
        if log_fn:
            log_fn(f"  ✔ Conectado: '{hostname}'  |  {layer}")

        # ── Limpieza opcional ─────────────────────────────────────────────────
        if do_clean:
            cleanup = build_cleanup_commands(
                nc,
                config_params.get('static_routes', []),
                config_params.get('ospf_networks', []),
                log_fn,
            )
            if cleanup:
                if log_fn:
                    log_fn(f"  [Limpieza] {len(cleanup)} comandos...")
                nc.config_mode()
                time.sleep(0.3)
                send_cmd_by_cmd(nc, cleanup, log_fn)
                nc.exit_config_mode()
                time.sleep(0.3)
            if log_fn:
                log_fn("  [Limpieza] ✔")

        # ── Generación y envío de comandos ────────────────────────────────────
        cmds = build_commands(is_l3=is_l3, log_fn=log_fn, **config_params)
        if cmds:
            if log_fn:
                log_fn(f"  [Config] Enviando {len(cmds)} comandos...")
            nc.config_mode()
            time.sleep(0.3)
            send_cmd_by_cmd(nc, cmds, log_fn)
            nc.exit_config_mode()
            time.sleep(0.3)

        # ── Guardar y desconectar ─────────────────────────────────────────────
        nc.save_config()   # equivale a "write memory" o "copy run start"
        if log_fn:
            log_fn(f"  ✔ {sw['name']} — GUARDADO EXITOSAMENTE")
        nc.disconnect()
        return True

    except NetmikoAuthenticationException:
        if log_fn:
            log_fn(f"  ✘ {sw['name']} — Error de Autenticación")
    except NetmikoTimeoutException:
        if log_fn:
            log_fn(f"  ✘ {sw['name']} — Timeout")
    except Exception as e:
        if log_fn:
            log_fn(f"  ✘ {sw['name']} — Error: {e}")
        import traceback
        if log_fn:
            log_fn(traceback.format_exc())
    return False


def fetch_running_config(sw: dict) -> str:
    """
    Descarga el running-config actual del switch.

    Parámetros
    ----------
    sw : dict con credenciales del switch.

    Retorna
    -------
    str : Contenido completo del running-config.

    Lanza
    -----
    Exception si no se puede conectar o autenticar.
    """
    nc  = ConnectHandler(**make_device_params(sw))
    nc.enable()
    raw = nc.send_command("show running-config", delay_factor=4)
    nc.disconnect()
    return raw


def test_connection(sw: dict):
    """
    Prueba la conexión SSH al switch y detecta Layer 2 vs Layer 3.

    Parámetros
    ----------
    sw : dict con credenciales del switch.

    Retorna
    -------
    dict : {
        'hostname': str,    # nombre del switch (del prompt)
        'is_l3':    bool,   # True = Layer 3
        'ver_out':  str,    # salida de 'show version | include IOS' (primeras 50 chars)
    }

    Lanza
    -----
    Exception si hay error de conexión o autenticación.
    """
    nc      = ConnectHandler(**make_device_params(sw))
    nc.enable()
    ver_out = nc.send_command("show version | include IOS", delay_factor=2)
    is_l3   = detect_l3(nc)
    hostname = nc.find_prompt().replace("#", "").strip()
    nc.disconnect()
    return {
        'hostname': hostname,
        'is_l3':    is_l3,
        'ver_out':  ver_out.strip()[:50],
    }
