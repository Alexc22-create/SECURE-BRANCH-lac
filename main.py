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