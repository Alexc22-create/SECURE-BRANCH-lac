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
