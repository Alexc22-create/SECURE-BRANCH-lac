import tkinter as tk
from tkinter import messagebox, scrolledtext
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

class SwitchConfiguratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automatización de Switch Multicapa - Cisco")
        self.root.geometry("600x750")

        # --- SECCIÓN DE CONEXIÓN ---
        tk.Label(root, text="--- Credenciales SSH ---", font=("Arial", 10, "bold")).pack(pady=5)
        
        frame_conn = tk.Frame(root)
        frame_conn.pack(pady=5)
        
        tk.Label(frame_conn, text="IP del Switch:").grid(row=0, column=0, sticky="e")
        self.ip_entry = tk.Entry(frame_conn)
        self.ip_entry.grid(row=0, column=1)

        tk.Label(frame_conn, text="Usuario:").grid(row=1, column=0, sticky="e")
        self.user_entry = tk.Entry(frame_conn)
        self.user_entry.grid(row=1, column=1)

        tk.Label(frame_conn, text="Contraseña:").grid(row=2, column=0, sticky="e")
        self.pass_entry = tk.Entry(frame_conn, show="*")
        self.pass_entry.grid(row=2, column=1)
        
        tk.Label(frame_conn, text="Enable Secret:").grid(row=3, column=0, sticky="e")
        self.secret_entry = tk.Entry(frame_conn, show="*")
        self.secret_entry.grid(row=3, column=1)

        # --- SECCIÓN BÁSICA ---
        tk.Label(root, text="--- Configuración Básica ---", font=("Arial", 10, "bold")).pack(pady=5)
        frame_basic = tk.Frame(root)
        frame_basic.pack(pady=5)

        tk.Label(frame_basic, text="Hostname:").grid(row=0, column=0, sticky="e")
        self.hostname_entry = tk.Entry(frame_basic)
        self.hostname_entry.grid(row=0, column=1)

        tk.Label(frame_basic, text="Banner (MOTD):").grid(row=1, column=0, sticky="e")
        self.banner_entry = tk.Entry(frame_basic)
        self.banner_entry.grid(row=1, column=1)

        # --- SECCIÓN VLANS Y DHCP ---
        tk.Label(root, text="--- VLANs y DHCP ---", font=("Arial", 10, "bold")).pack(pady=5)
        frame_vlan = tk.Frame(root)
        frame_vlan.pack(pady=5)

        tk.Label(frame_vlan, text="IDs de VLAN (ej. 10,20,30):").grid(row=0, column=0, sticky="e")
        self.vlans_entry = tk.Entry(frame_vlan)
        self.vlans_entry.grid(row=0, column=1)

        self.dhcp_var = tk.BooleanVar()
        tk.Checkbutton(frame_vlan, text="Habilitar DHCP para estas VLANs (Red 192.168.X.0)", variable=self.dhcp_var).grid(row=1, column=0, columnspan=2)

        # --- SECCIÓN ACLs ---
        tk.Label(root, text="--- ACLs y Seguridad ---", font=("Arial", 10, "bold")).pack(pady=5)
        frame_acl = tk.Frame(root)
        frame_acl.pack(pady=5)

        self.acl_var = tk.BooleanVar()
        tk.Checkbutton(frame_acl, text="Bloquear Redes Sociales (Ejemplo Meta/Twitter)", variable=self.acl_var).grid(row=0, column=0, columnspan=2)

        tk.Label(frame_acl, text="Aplicar ACL en VLAN ID:").grid(row=1, column=0, sticky="e")
        self.acl_vlan_entry = tk.Entry(frame_acl)
        self.acl_vlan_entry.grid(row=1, column=1)

        # --- BOTÓN DE EJECUCIÓN ---
        tk.Button(root, text="Generar y Enviar Configuración", bg="green", fg="white", font=("Arial", 12, "bold"), command=self.deploy_config).pack(pady=15)

        # --- LOGS ---
        tk.Label(root, text="Registro de Actividad:").pack()
        self.log_area = scrolledtext.ScrolledText(root, width=70, height=12)
        self.log_area.pack(pady=5)

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def generate_commands(self):
        commands = []
        
        # 1. Configuración Básica
        hostname = self.hostname_entry.get()
        if hostname:
            commands.append(f"hostname {hostname}")
            
        banner = self.banner_entry.get()
        if banner:
            commands.append(f"banner motd #{banner}#")
            
        # Contraseñas globales
        secret = self.secret_entry.get()
        if secret:
            commands.append(f"enable secret {secret}")
            commands.append("line vty 0 4")
            commands.append(f"password {secret}")
            commands.append("login")
            commands.append("exit")

        # Habilitar enrutamiento (Esencial en switch multicapa)
        commands.append("ip routing")

        # 2. Configurar Salida por G0/0
        commands.append("interface GigabitEthernet0/0")
        commands.append("no switchport") # Lo convierte en puerto enrutado
        commands.append("ip address dhcp") # Obtiene IP de tu router de salida
        commands.append("no shutdown")
        commands.append("exit")

        # 3. VLANs y DHCP
        vlans_raw = self.vlans_entry.get()
        if vlans_raw:
            vlan_list = [v.strip() for v in vlans_raw.split(",") if v.strip().isdigit()]
            for vid in vlan_list:
                # Crear VLAN
                commands.append(f"vlan {vid}")
                commands.append(f"name RED_VLAN_{vid}")
                commands.append("exit")
                
                # Crear Interfaz SVI para enrutamiento
                commands.append(f"interface vlan {vid}")
                commands.append(f"ip address 192.168.{vid}.1 255.255.255.0")
                commands.append("no shutdown")
                commands.append("exit")

                # Crear DHCP si está marcado
                if self.dhcp_var.get():
                    commands.append(f"ip dhcp pool POOL_VLAN_{vid}")
                    commands.append(f"network 192.168.{vid}.0 255.255.255.0")
                    commands.append(f"default-router 192.168.{vid}.1")
                    commands.append("exit")

        # 4. ACLs Simplificadas
        if self.acl_var.get() and self.acl_vlan_entry.get().strip().isdigit():
            acl_vlan = self.acl_vlan_entry.get().strip()
            commands.append("ip access-list extended BLOCK_SOCIAL")
            # IPs simuladas de Facebook/Twitter para el ejemplo
            commands.append("deny ip any host 157.240.22.35") 
            commands.append("deny ip any host 104.244.42.1")
            commands.append("permit ip any any")
            commands.append("exit")
            
            # Aplicar ACL a la SVI de la VLAN
            commands.append(f"interface vlan {acl_vlan}")
            commands.append("ip access-group BLOCK_SOCIAL in")
            commands.append("exit")

        return commands

    def deploy_config(self):
        ip = self.ip_entry.get()
        user = self.user_entry.get()
        password = self.pass_entry.get()
        secret = self.secret_entry.get()

        if not all([ip, user, password]):
            messagebox.showerror("Error", "La IP, Usuario y Contraseña son obligatorios.")
            return

        commands = self.generate_commands()
        
        if not commands:
            messagebox.showwarning("Advertencia", "No se han definido parámetros para configurar.")
            return

        device = {
            'device_type': 'cisco_ios',
            'host': ip,
            'username': user,
            'password': password,
            'secret': secret,
        }

        self.log(f"Iniciando conexión SSH a {ip}...")
        
        try:
            # Conexión SSH con Netmiko
            net_connect = ConnectHandler(**device)
            net_connect.enable() # Entra a modo EXEC Privilegiado
            
            self.log("Conexión exitosa. Enviando comandos...")
            
            # Enviar configuración
            output = net_connect.send_config_set(commands)
            self.log(output)
            
            # Guardar configuración (write memory)
            net_connect.save_config()
            self.log("¡Configuración guardada exitosamente en el switch!")
            
            net_connect.disconnect()
            messagebox.showinfo("Éxito", "Configuración aplicada correctamente.")
            
        except NetmikoAuthenticationException:
            self.log("Error: Falló la autenticación. Revisa el usuario o contraseña.")
        except NetmikoTimeoutException:
            self.log("Error: Tiempo de espera agotado. Verifica la IP y que tengas conectividad a través de la VPN.")
        except Exception as e:
            self.log(f"Error inesperado: {str(e)}")

# Iniciar la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = SwitchConfiguratorApp(root)
    root.mainloop()
