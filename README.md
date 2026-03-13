# Configurador IOSvL2 — v2.2

Herramienta GUI para configurar switches Cisco IOSvL2 de forma masiva (N sucursales).

**Firmware objetivo:** `vios_l2-ADVENTERPRISEK9-M`, IOS Experimental 15.2(20200924:215240)

---

## Estructura del proyecto

```
SECURE-BRANCH-lac/
│
├── app.py                   # Punto de entrada + clase principal (SwitchConfiguratorV2)
├── constants.py             # Colores, versión, UPLINK_IFACE, DSCP_PRESETS
│
├── core/                    # Lógica de negocio — sin dependencias de Tkinter
│   ├── command_builder.py   # Genera comandos IOS (DHCP, VLANs, ACLs, OSPF, QoS,
│   │                        #   Seguridad, GRE over IPsec)
│   └── connector.py         # Conexión SSH, detección L2/L3, envío de comandos
│
└── ui/                      # Interfaz gráfica Tkinter
    ├── widgets.py            # Fábrica de widgets estilizados (botones, entries, etc.)
    ├── tabs_sw_dhcp.py       # Pestañas ① Sucursales y ② DHCP
    ├── tab_vlan.py           # Pestaña ③ VLANs y Puertos
    ├── tab_routing.py        # Pestaña ④ Enrutamiento (rutas + OSPF)
    ├── tab_qos.py            # Pestaña ⑤ QoS MQC (class-map, policy-map, service-policy)
    ├── tab_exec_backup.py    # Pestañas ⑥ Ejecución y ⑦ Backup (local + AWS S3)
    └── tab_security_gre.py   # Pestañas ⑧ Seguridad y ⑨ GRE over IPsec
```

---

## Cómo ejecutar

```bash
cd SECURE-BRANCH-lac
source env/bin/activate          # activar entorno virtual
python app.py
```

### Instalación de dependencias

```bash
pip install netmiko --break-system-packages   # SSH a switches Cisco
pip install boto3   --break-system-packages   # Backup a AWS S3 (opcional)
```

---

## Flujo de uso

| # | Pestaña | Qué se configura |
|---|---------|-----------------|
| ① | **Sucursales** | Agrega switches con IP, usuario y contraseñas. Prueba conexión SSH. |
| ② | **DHCP** | Define pools DHCP (red, máscara, gateway). |
| ③ | **VLANs y Puertos** | Crea VLANs, asigna puertos (access/trunk) y vincula un pool DHCP. |
| ④ | **Enrutamiento** | ip routing, rutas estáticas, ruta por defecto, OSPF. |
| ⑤ | **QoS MQC** | class-map (DSCP/IP/ACL), policy-map (police/shape/priority/set dscp), service-policy. |
| ⑥ | **Ejecución** | Selecciona sucursales y aplica la config con log en tiempo real. |
| ⑦ | **Backup** | Exportar/importar JSON, descargar running-config local, **subir a AWS S3**. |
| ⑧ | **Seguridad** | Enable secret, bloqueo por intentos fallidos, banner MOTD. |
| ⑨ | **GRE/IPsec** | Túneles GRE cifrados con IKEv1 + ESP-AES-256 sobre IPsec. |

---

## Funcionalidades nuevas en v2.2

### ⑧ Seguridad del dispositivo

Configura tres mecanismos de seguridad de acceso en un solo paso:

**Enable Secret (MD5 type-5)**
```
enable secret <contraseña>
```
Usa cifrado irreversible MD5 (type 5), más seguro que `enable password` (type 7).

**Bloqueo por intentos fallidos — `login block-for`**
```
login block-for 120 attempts 5 within 60
login on-failure log
```
Si se superan **5 intentos fallidos** en **60 segundos**, el switch bloquea el acceso VTY/SSH por **120 segundos** y registra el evento en syslog. Los valores son configurables desde la UI.

**Banner MOTD**
```
banner motd #<texto>#
```
Mensaje mostrado antes del login por SSH/consola. Incluye un aviso legal precargado. El delimitador `#` del texto se reemplaza automáticamente para evitar conflictos con el comando IOS.

---

### ⑨ GRE over IPsec

Configura túneles GRE cifrados con IPsec. Compatible con `vios_l2 15.2` (DH group 2 máximo).

**¿Por qué GRE + IPsec y no solo IPsec?**
IPsec no puede transportar tráfico multicast/broadcast por sí solo (necesario para OSPF, EIGRP). GRE crea un túnel punto a punto que sí lo permite, y luego IPsec cifra ese túnel completo.

---

### ⑦ Backup a AWS S3

Sube el `running-config` de cada switch seleccionado a un bucket S3.

**Ruta del objeto en S3:**
```
<prefijo>/<nombre-sucursal>/<YYYY-MM-DD_HH-MM-SS>.txt
```
Ejemplo: `backups/switches/SW-CDMX/2025-04-10_14-30-00.txt`

**Características:**
- Cifrado en reposo automático con **SSE-AES256** (`ServerSideEncryption: AES256`)
- Encabezado con metadatos (sucursal, IP, fecha, ruta S3) al inicio de cada archivo
- Botón de verificación de credenciales (`head_bucket`, sin costo AWS)
- Las credenciales **no se guardan en disco** ni se exportan en el JSON

**Configuración requerida:**
```
Access Key ID     : tu-access-key
Secret Access Key : tu-secret-key
Región AWS        : us-east-1
Bucket S3         : mi-bucket-backups
Prefijo/carpeta   : backups/switches/
```

---

## Protecciones automáticas

| Protección | Detalle |
|------------|---------|
| `GigabitEthernet0/0` | Nunca se modifica (uplink de gestión) |
| SSH / VTY / crypto key | Nunca se tocan |
| Switches L2 | Se omite `ip routing` y SVIs con IP (detección automática) |
| Limpieza | Solo borra lo que la app configuró; rutas y OSPF preexistentes se preservan |
| Enable secret | Se aplica **al final** del deploy para no cerrar la sesión SSH activa |

---

## Dependencias

| Paquete | Uso | Instalación |
|---------|-----|-------------|
| `tkinter` | Interfaz gráfica | Incluido en Python estándar |
| `netmiko` | Conexión SSH a switches Cisco | `pip install netmiko --break-system-packages` |
| `boto3` | Backup a AWS S3 | `pip install boto3 --break-system-packages` (opcional) |

