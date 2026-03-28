# Configurador IOSvL2 — v2.2

Herramienta GUI para configurar switches Cisco IOSvL2 de forma masiva (N sucursales).

**Firmware objetivo:** `vios_l2-ADVENTERPRISEK9-M`, IOS Experimental 15.2(20200924:215240)

---

## Estructura del proyecto

```
SECURE-BRANCH-lac/
│
├── app.py                   # Punto de entrada + clase principal (SwitchConfiguratorV2)
├── constants.py             # Colores, versión, UPLINK_IFACE, DSCP_PRESETS, THEMES
├── app_config.json          # Config persistente generada por la pestaña ⚙ (auto-creado)
│
├── core/                    # Lógica de negocio — sin dependencias de Tkinter
│   ├── command_builder.py   # Genera comandos IOS (DHCP, VLANs, ACLs, OSPF, QoS,
│   │                        #   Seguridad, GRE over IPsec, DNS configurable)
│   └── connector.py         # Conexión SSH, detección L2/L3, envío de comandos,
│                            #   restauración de running-config con filtrado de seguridad
│
└── ui/                      # Interfaz gráfica Tkinter
    ├── widgets.py            # Fábrica de widgets estilizados + switch_theme()
    ├── validators.py         # Validaciones reutilizables (IPs, máscaras, VLANs, puertos,
    │                         #   nombres IOS, wildcards, PSKs)
    ├── preview_window.py     # Ventana de vista previa de comandos IOS (coloreado por tipo)
    ├── tabs_sw_dhcp.py       # Pestañas ① Sucursales y ② DHCP
    ├── tab_vlan.py           # Pestaña ③ VLANs y Puertos
    ├── tab_routing.py        # Pestaña ④ Enrutamiento (rutas + OSPF)
    ├── tab_qos.py            # Pestaña ⑤ QoS MQC (class-map, policy-map, service-policy)
    ├── tab_exec_backup.py    # Pestañas ⑥ Ejecución y ⑦ Backup (local + AWS S3 + restauración)
    ├── tab_security_gre.py   # Pestañas ⑧ Seguridad y ⑨ GRE over IPsec
    └── tab_config.py         # Pestaña ⑩ Configuración de Empresa y Estilos
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
| ② | **DHCP** | Define pools DHCP (red, máscara, gateway, exclusiones). DNS configurable desde pestaña ⚙. |
| ③ | **VLANs y Puertos** | Crea VLANs, asigna puertos (access/trunk), vincula pool DHCP y define ACLs custom. |
| ④ | **Enrutamiento** | ip routing, rutas estáticas, ruta por defecto, OSPF. |
| ⑤ | **QoS MQC** | class-map (DSCP/IP/ACL), policy-map (police/shape/priority/set dscp), service-policy. |
| ⑥ | **Ejecución** | Selecciona sucursales y aplica la config con log en tiempo real. Vista previa de todos los comandos. |
| ⑦ | **Backup** | Exportar/importar JSON, descargar running-config local, **subir a AWS S3**, **restaurar running-config desde archivo**. |
| ⑧ | **Seguridad** | Enable secret, bloqueo por intentos fallidos, banner MOTD. |
| ⑨ | **GRE/IPsec** | Túneles GRE cifrados con IKEv1 + ESP-AES-256 sobre IPsec. |
| ⑩ | **⚙ Configuración** | Nombre de empresa, defaults SSH/DHCP/OSPF/Seguridad/S3, DNS personalizables, tema visual. |

---

## Funcionalidades nuevas en v2.2

### ⑩ Configuración de Empresa y Estilos

Centraliza los parámetros que normalmente son iguales en toda la empresa y permite cambiar el tema visual en tiempo real.

**Parámetros configurables:**
- **Información de empresa:** nombre que aparece en el título de la ventana
- **Defaults SSH:** usuario, puerto y timeout de conexión por defecto
- **Interfaz de uplink protegida:** se puede cambiar la interfaz que la app nunca modifica
- **Defaults DHCP:** DNS primario y secundario, máscara por defecto
- **Defaults OSPF:** PID y área por defecto
- **Defaults Seguridad:** intentos máximos de login, ventana de tiempo, duración de bloqueo, banner MOTD
- **Defaults AWS S3:** región, bucket y prefijo por defecto

Los valores se persisten en `app_config.json` y se pueden aplicar a todas las pestañas con un solo botón. Incluye restauración a valores de fábrica.

---

### Temas visuales

La aplicación soporta 3 temas que se aplican en tiempo real y se guardan para la próxima sesión:

| Tema | Estilo |
|------|--------|
| **GitHub Dark** | Tema oscuro con acentos azules (por defecto) |
| **Monokai Pro** | Tema oscuro con acentos púrpura y naranja |
| **Nord Light** | Tema claro con acentos azul acero |

Cada tema define la paleta completa: fondos, acentos, textos, bordes y colores de consola. Se seleccionan desde tarjetas visuales interactivas en la pestaña ⚙.

---

### Vista previa de comandos IOS

Todas las pestañas incluyen un botón de vista previa que abre una ventana con los comandos IOS que se enviarán al switch **antes de ejecutarlos**. Características:

- Coloreado por tipo de comando (bloques, configuración, negaciones, acciones, comentarios)
- Numeración de líneas
- Botón de copiado al portapapeles
- Enmascaramiento de contraseñas y PSKs en la vista previa (los comandos reales no se modifican)

---

### Validaciones completas de formularios

Todos los formularios validan los datos antes de agregarlos a la configuración. El módulo `ui/validators.py` centraliza las reglas de validación:

- **Direcciones IPv4:** formato correcto (ej. `192.168.1.1`)
- **Máscaras de subred:** unos contiguos seguidos de ceros (ej. `255.255.255.0`)
- **Wildcards OSPF:** ceros contiguos seguidos de unos (ej. `0.0.0.255`)
- **IDs de VLAN:** entero entre 1 y 4094
- **Interfaces Cisco:** formato válido (GigabitEthernet0/1, Gi0/1, Tunnel0, Vlan10, etc.)
- **Rangos de puertos:** Gi0/1-3, Gi0/1,Gi0/2, etc.
- **Nombres IOS:** solo letras, dígitos, guiones y guiones bajos
- **PSKs/contraseñas:** sin espacios, longitud entre 1 y 128 caracteres
- **Pertenencia a red:** verifica que una IP pertenezca a una red/máscara dada

---

### DNS configurable para DHCP

Los pools DHCP ahora usan servidores DNS configurables desde la pestaña ⚙ Configuración. Si no se configuran, se usa `8.8.8.8` como fallback. Los DNS se pasan como parámetro a `build_all_commands()` y se incluyen en cada pool con el comando `dns-server`.

---

### ⑦ Restauración de running-config desde archivo

En la pestaña Backup se puede restaurar un `running-config` previamente guardado en un archivo `.txt` directamente al switch vía SSH.

**Flujo:**
1. Seleccionar la sucursal destino
2. Elegir el archivo `.txt` con el running-config
3. Vista previa y confirmación
4. Envío de comandos al switch con `write memory` al finalizar

**Filtrado de seguridad automático:** se filtran líneas que no son comandos IOS válidos (cabeceras, comentarios) y comandos peligrosos que podrían comprometer el acceso al dispositivo:
```
username, enable password, enable secret, crypto key, aaa,
line vty, ip http, snmp-server community, no crypto
```
Las líneas filtradas se reportan en el log de consola.

---

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
Si se superan **5 intentos fallidos** en **60 segundos**, el switch bloquea el acceso VTY/SSH por **120 segundos** y registra el evento en syslog. Los valores son configurables desde la UI y se pueden pre-definir en la pestaña ⚙.

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
| `GigabitEthernet0/0` | Nunca se modifica (uplink de gestión). Configurable desde pestaña ⚙. |
| SSH / VTY / crypto key | Nunca se tocan |
| Switches L2 | Se omite `ip routing` y SVIs con IP (detección automática) |
| Limpieza | Solo borra lo que la app configuró; rutas y OSPF preexistentes se preservan |
| Enable secret | Se aplica **al final** del deploy para no cerrar la sesión SSH activa |
| Sanitización de ACL custom | Solo permite `permit`, `deny`, `remark`; bloquea inyección de comandos (`exit`, `do`, `configure`, `enable`, `username`, `crypto key`, etc.) |
| Enmascaramiento de secrets | Las contraseñas y PSKs se enmascaran en la vista previa de comandos (los valores reales solo se envían al switch) |
| Filtrado en restauración de config | Comandos peligrosos (`username`, `enable secret`, `crypto key`, `aaa`, `line vty`, `ip http`, `snmp-server community`) se filtran automáticamente al restaurar un running-config |
| Validación de IPs en exclusiones DHCP | Se valida que las IPs excluidas sean IPv4 válidas y pertenezcan a la red del pool |
| Validación de formularios | Todos los campos se validan antes de agregar datos (IPs, máscaras, VLANs, interfaces, nombres, etc.) |

---

## Dependencias

| Paquete | Uso | Instalación |
|---------|-----|-------------|
| `tkinter` | Interfaz gráfica | Incluido en Python estándar |
| `netmiko` | Conexión SSH a switches Cisco | `pip install netmiko --break-system-packages` |
| `boto3` | Backup a AWS S3 | `pip install boto3 --break-system-packages` (opcional) |
