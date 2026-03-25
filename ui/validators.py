"""
ui/validators.py — Funciones de validación reutilizables para la GUI
=====================================================================
Centraliza todas las reglas de validación de campos de formulario.
No depende de tkinter; retorna (bool, mensaje_error) para que cada
pestaña decida cómo mostrar el error al usuario.
"""
import re
import ipaddress


# ─────────────────────────────────────────────────────────────────────────────
#  IPv4 — dirección y máscara
# ─────────────────────────────────────────────────────────────────────────────

def is_valid_ip(ip: str) -> bool:
    """Devuelve True si ip es una dirección IPv4 válida (ej. 192.168.1.1)."""
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError:
        return False


def is_valid_mask(mask: str) -> bool:
    """
    Devuelve True si mask es una máscara de subred IPv4 válida
    (unos contiguos seguidos de ceros: 255.255.255.0, 255.255.0.0, etc.).
    """
    try:
        packed = int(ipaddress.IPv4Address(mask))
        inv = packed ^ 0xFFFFFFFF
        return (inv & (inv + 1)) == 0
    except ValueError:
        return False


def is_valid_wildcard(wild: str) -> bool:
    """
    Devuelve True si wild es un wildcard OSPF válido
    (ceros contiguos seguidos de unos: 0.0.0.255, 0.0.255.255, etc.).
    """
    try:
        packed = int(ipaddress.IPv4Address(wild))
        return (packed & (packed + 1)) == 0
    except ValueError:
        return False


def ip_in_network(ip: str, net: str, mask: str) -> bool:
    """Devuelve True si ip pertenece a la red net/mask."""
    try:
        network = ipaddress.IPv4Network(f"{net}/{mask}", strict=False)
        return ipaddress.IPv4Address(ip) in network
    except ValueError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Números enteros
# ─────────────────────────────────────────────────────────────────────────────

def is_positive_int(val: str, min_val: int = 1, max_val: int = None) -> bool:
    """Devuelve True si val es un entero >= min_val (y <= max_val si se indica)."""
    try:
        n = int(val)
        if n < min_val:
            return False
        if max_val is not None and n > max_val:
            return False
        return True
    except (ValueError, TypeError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  VLAN
# ─────────────────────────────────────────────────────────────────────────────

def validate_vlan_id(vid: str) -> tuple:
    """
    Valida que vid sea un ID de VLAN correcto (entero entre 1 y 4094).
    Devuelve (True, '') si es válido, (False, mensaje) si no.
    """
    try:
        n = int(vid)
        if 1 <= n <= 4094:
            return True, ""
        return False, f"El ID de VLAN debe estar entre 1 y 4094 (valor: {n})."
    except (ValueError, TypeError):
        return False, f"El ID de VLAN debe ser un número entero (valor: '{vid}')."


# ─────────────────────────────────────────────────────────────────────────────
#  Interfaces Cisco
# ─────────────────────────────────────────────────────────────────────────────

# Patrón que cubre GigabitEthernet0/1, Gi0/1, FastEthernet0/0, Fa0/0,
# Tunnel0, Loopback0, Vlan10, etc.
_IFACE_RE = re.compile(
    r'^(GigabitEthernet|FastEthernet|Ethernet|Gi|Fa|Et|Tunnel|Tu|Loopback|Lo|Vlan)\d+(/\d+)*$',
    re.IGNORECASE,
)

_PORT_SEGMENT_RE = re.compile(
    r'^(GigabitEthernet|FastEthernet|Ethernet|Gi|Fa|Et)\d+/\d+(-\d+)?$',
    re.IGNORECASE,
)


def is_valid_interface(iface: str) -> bool:
    """
    Devuelve True si iface tiene formato de interfaz Cisco válido.
    Ejemplos válidos: GigabitEthernet0/1, Gi0/1, Tunnel0, Vlan10.
    """
    return bool(_IFACE_RE.match(iface.strip()))


def validate_port_range(ports: str) -> tuple:
    """
    Valida el campo de rangos de puertos (Gi0/1-3, Gi0/1,Gi0/3, etc.).
    Devuelve (True, '') si es válido, (False, mensaje) si no.
    Cadena vacía se considera válida (campo opcional).
    """
    if not ports.strip():
        return True, ""
    segments = [p.strip() for p in ports.split(',')]
    for seg in segments:
        if not _PORT_SEGMENT_RE.match(seg):
            return False, (
                f"Formato de puerto inválido: '{seg}'.\n"
                "Formatos aceptados: Gi0/1  |  Gi0/1-3  |  Gi0/1,Gi0/2,Gi0/3"
            )
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
#  Nombres (class-map, policy-map, pool DHCP, etc.)
# ─────────────────────────────────────────────────────────────────────────────

_NAME_RE = re.compile(r'^[A-Za-z0-9_\-]+$')


def is_valid_ios_name(name: str) -> bool:
    """
    Devuelve True si name es un nombre válido para IOS
    (solo letras, dígitos, guiones y guiones bajos; sin espacios).
    """
    return bool(_NAME_RE.match(name.strip())) if name.strip() else False


# ─────────────────────────────────────────────────────────────────────────────
#  PSK / contraseñas
# ─────────────────────────────────────────────────────────────────────────────

def is_valid_psk(psk: str) -> bool:
    """
    Devuelve True si psk es una clave pre-compartida aceptable para IOS:
    sin espacios, longitud entre 1 y 128 caracteres.
    """
    return bool(psk) and ' ' not in psk and len(psk) <= 128
