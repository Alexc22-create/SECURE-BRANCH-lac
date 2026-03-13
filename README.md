# Configurador IOSvL2 — v2.1

Herramienta GUI para configurar switches Cisco IOS 15.x / IOSvL2 de forma masiva (N sucursales).

## Estructura del proyecto

```
SECURE-BRANCH-lac/
│
├── app.py                  # Punto de entrada + clase principal (SwitchConfiguratorV2)
├── constants.py            # Colores, versión, UPLINK_IFACE, DSCP_PRESETS
│
├── core/                   # Lógica de negocio — sin dependencias de Tkinter
│   ├── command_builder.py  # Genera comandos IOS (DHCP, VLANs, ACLs, OSPF, QoS)
│   └── connector.py        # Conexión SSH, detección L2/L3, envío de comandos
│
└── ui/                     # Interfaz gráfica Tkinter
    ├── widgets.py           # Fábrica de widgets estilizados (botones, entries, etc.)
    ├── tabs_sw_dhcp.py      # Pestañas ① Sucursales y ② DHCP
    ├── tab_vlan.py          # Pestaña ③ VLANs y Puertos
    ├── tab_routing.py       # Pestaña ④ Enrutamiento (rutas + OSPF)
    ├── tab_qos.py           # Pestaña ⑤ QoS MQC (class-map, policy-map, service-policy)
    └── tab_exec_backup.py   # Pestañas ⑥ Ejecución y ⑦ Backup
```

## Cómo ejecutar

```bash
pip install netmiko
python app.py
```

## Flujo de uso

1. **① Sucursales** — Agrega los switches con IP, usuario y contraseñas.
2. **② DHCP** — Define pools DHCP (red, máscara, gateway).
3. **③ VLANs** — Crea VLANs, asigna puertos y vincula un pool DHCP.
4. **④ Enrutamiento** — Configura ip routing, rutas estáticas y OSPF.
5. **⑤ QoS** — Define class-maps, policy-map y service-policy.
6. **⑥ Ejecución** — Selecciona sucursales y aplica la config.
7. **⑦ Backup** — Exporta/importa config JSON o descarga running-config.

## Protecciones automáticas

- `GigabitEthernet0/0` (uplink) **nunca se toca**.
- SSH, usuarios, VTY y crypto key **nunca se modifican**.
- En switches L2 detectados automáticamente, se omite `ip routing` y las SVIs con IP.
- La limpieza solo borra lo que la app configuró, sin afectar rutas/OSPF preexistentes.

## Dependencias

```
tkinter   (incluido en Python estándar)
netmiko   (pip install netmiko)
```
