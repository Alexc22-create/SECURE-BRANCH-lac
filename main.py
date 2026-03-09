app = FastAPI(title="NetConfig API", description="API para configuracion automatica de switches Cisco")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class SSHCredentials(BaseModel):
    host: str
    port: int = 22
    username: str
    password: str
    device_type: str = "cisco_ios"
    enable_secret: Optional[str] = None

class CommandRequest(BaseModel):
    credentials: SSHCredentials
    commands: list[str]

class TestConnectionRequest(BaseModel):
    credentials: SSHCredentials

class CommandResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None

# Generador de comandos IOS
class CiscoCommandGenerator:
    @staticmethod
    def generate_basic_config(config: dict) -> list[str]:
        commands = []
        if config.get("hostname"):
            commands.append(f"hostname {config['hostname']}")
        if config.get("domain_name"):
            commands.append(f"ip domain-name {config['domain_name']}")
        if config.get("enable_secret"):
            commands.append(f"enable secret {config['enable_secret']}")
        if config.get("admin_user") and config.get("admin_password"):
            commands.append(f"username {config['admin_user']} privilege 15 secret {config['admin_password']}")
        if config.get("banner_motd"):
            commands.append(f"banner motd #{config['banner_motd']}#")
        return commands

          @staticmethod
    def generate_vlan_config(vlans: list[dict]) -> list[str]:
        commands = []
        for vlan in vlans:
            commands.append(f"vlan {vlan['id']}")
            if vlan.get("name"):
                commands.append(f" name {vlan['name']}")
            commands.append("exit")
            # SVI
            if vlan.get("gateway") and vlan.get("mask"):
                commands.append(f"interface vlan {vlan['id']}")
                commands.append(f" ip address {vlan['gateway']} {vlan['mask']}")
                commands.append(" no shutdown")
                commands.append("exit")
        return commands
     @staticmethod
    def generate_trunk_config(trunks: list[dict]) -> list[str]:
        commands = []
        for trunk in trunks:
            commands.append(f"interface {trunk['name']}")
            commands.append(" switchport trunk encapsulation dot1q")
            commands.append(" switchport mode trunk")
            if trunk.get("allowed_vlans"):
                commands.append(f" switchport trunk allowed vlan {trunk['allowed_vlans']}")
            if trunk.get("native_vlan"):
                commands.append(f" switchport trunk native vlan {trunk['native_vlan']}")
            commands.append(" no shutdown")
            commands.append("exit")
        return commands

    @staticmethod
    def generate_ssh_config(config: dict) -> list[str]:
        commands = []
        commands.append("ip ssh version 2")
        if config.get("timeout"):
            commands.append(f"ip ssh time-out {config['timeout']}")
        if config.get("retries"):
            commands.append(f"ip ssh authentication-retries {config['retries']}")
        commands.append("line vty 0 15")
        commands.append(" transport input ssh")
        commands.append(" login local")
        if config.get("exec_timeout"):
            commands.append(f" exec-timeout {config['exec_timeout']}")
        commands.append("exit")
        if config.get("console_password"):
            commands.append("line console 0")
            commands.append(f" password {config['console_password']}")
            commands.append(" login")
            commands.append("exit")
        return commands

         @staticmethod
    def generate_ospf_config(config: dict) -> list[str]:
        commands = []
        process_id = config.get("process_id", 1)
        commands.append(f"router ospf {process_id}")
        if config.get("router_id"):
            commands.append(f" router-id {config['router_id']}")
        for network in config.get("networks", []):
            commands.append(f" network {network['network']} {network['wildcard']} area {network['area']}")
        commands.append("exit")
        return commands

    @staticmethod
    def generate_dhcp_config(pools: list[dict]) -> list[str]:
        commands = []
        for pool in pools:
            commands.append(f"ip dhcp pool {pool['name']}")
            commands.append(f" network {pool['network']} {pool['mask']}")
            if pool.get("gateway"):
                commands.append(f" default-router {pool['gateway']}")
            if pool.get("dns"):
                commands.append(f" dns-server {pool['dns']}")
            if pool.get("lease_days"):
                commands.append(f" lease {pool['lease_days']}")
            commands.append("exit")
        for pool in pools:
            for exclusion in pool.get("exclusions", []):
                commands.append(f"ip dhcp excluded-address {exclusion['start']} {exclusion['end']}")
        return commands

    @staticmethod
    def generate_acl_config(acls: list[dict]) -> list[str]:
        commands = []
        for acl in acls:
            if acl.get("type") == "standard":
                commands.append(f"ip access-list standard {acl['name']}")
            else:
                commands.append(f"ip access-list extended {acl['name']}")
            for rule in acl.get("rules", []):
                if acl.get("type") == "standard":
                    commands.append(f" {rule['action']} {rule.get('source', 'any')}")
                else:
                    src = rule.get("source", "any")
                    dst = rule.get("destination", "any")
                    proto = rule.get("protocol", "ip")
                    port_str = ""
                    if rule.get("port"):
                        port_str = f" eq {rule['port']}"
                    commands.append(f" {rule['action']} {proto} {src} {dst}{port_str}")
            commands.append("exit")
            # Aplicar a interfaz si se especifica
            if acl.get("apply_to"):
                commands.append(f"interface {acl['apply_to']['interface']}")
                commands.append(f" ip access-group {acl['name']} {acl['apply_to']['direction']}")
                commands.append("exit")
        return commands
# Funcion para ejecutar comandos via SSH
async def execute_ssh_commands(credentials: SSHCredentials, commands: list[str]) -> CommandResponse:
    device = {
        "device_type": credentials.device_type,
        "host": credentials.host,
        "port": credentials.port,
        "username": credentials.username,
        "password": credentials.password,
        "secret": credentials.enable_secret or credentials.password,
    }
    
    try:
        def run_commands():
            connection = ConnectHandler(**device)
            connection.enable()
            
            # Ejecutar comandos de configuracion
            output = connection.send_config_set(commands)
            
            # Guardar configuracion
            output += "\n" + connection.send_command("write memory")
            
            connection.disconnect()
            return output
        
        # Ejecutar en thread pool para no bloquear
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, run_commands)
        
        return CommandResponse(success=True, output=output)
    
    except NetMikoTimeoutException:
        return CommandResponse(
            success=False, 
            output="", 
            error="Timeout: No se pudo conectar al dispositivo. Verifica la IP y puerto."
        )
    except NetMikoAuthenticationException:
        return CommandResponse(
            success=False, 
            output="", 
            error="Error de autenticacion. Verifica usuario y contrasena."
        )
    except Exception as e:
        return CommandResponse(
            success=False, 
            output="", 
            error=f"Error de conexion: {str(e)}"
        )


# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "NetConfig API"}


@app.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """Prueba la conexion SSH sin enviar comandos"""
    device = {
        "device_type": request.credentials.device_type,
        "host": request.credentials.host,
        "port": request.credentials.port,
        "username": request.credentials.username,
        "password": request.credentials.password,
        "secret": request.credentials.enable_secret or request.credentials.password,
    }
    
    try:
        def test_conn():
            connection = ConnectHandler(**device)
            hostname = connection.find_prompt()
            connection.disconnect()
            return hostname
        
        loop = asyncio.get_event_loop()
        hostname = await loop.run_in_executor(None, test_conn)
        
        return {"success": True, "hostname": hostname, "message": "Conexion exitosa"}
    