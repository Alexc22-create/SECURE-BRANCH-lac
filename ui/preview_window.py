"""
ui/preview_window.py — Ventana reutilizable de vista previa de comandos IOS
============================================================================
Muestra comandos IOS en una ventana Toplevel con tema oscuro,
coloreado por tipo de comando, número de línea y botón de copiado.
"""
import tkinter as tk

from constants import BG, BG3, ACCENT, ACCENT2, WARN, TEXT, TEXT2, BORDER

# ── Grupos de palabras clave para coloreado ───────────────────────────────────
_KW_BLOCK = {           # encabezados de bloque: azul claro
    "interface", "vlan", "router", "class-map", "policy-map",
    "crypto", "ip access-list",
}
_KW_CMD = {             # comandos de configuración: azul suave
    "ip ", "network", "switchport", "banner", "enable", "login",
    "service", "spanning-tree", "dns-server", "default-router",
    "tunnel", "match", "class ", "set ", "police", "shape",
    "priority", "bandwidth", "encr", "hash", "authentication",
    "group", "lifetime",
}
_KW_ACTION = {"no shutdown", "shutdown"}   # acciones: verde
_KW_END    = {"exit", "end", "!"}          # cierre de bloque: gris
_KW_NO     = "no "                         # negaciones: naranja/rojo


def _color_tag(line: str) -> str:
    """Devuelve el nombre del tag de color para una línea de comando."""
    s = line.strip().lower()
    if not s or s.startswith("!") or s.startswith("#"):
        return "comment"
    if s.startswith(_KW_NO):
        return "neg"
    if s in _KW_END:
        return "end_kw"
    if s in _KW_ACTION or s == "no shutdown":
        return "action"
    if any(s.startswith(kw) for kw in _KW_BLOCK):
        return "block"
    if any(s.startswith(kw) for kw in _KW_CMD):
        return "cmd"
    return "default"


def show_preview(root, title: str, commands: list, note: str = ""):
    """
    Abre una ventana Toplevel con la lista de comandos IOS formateados.

    Parámetros
    ----------
    root     : Widget raíz de la app (para centrar la ventana y gestionar el grab).
    title    : Texto del título de la ventana.
    commands : Lista de strings — cada uno es un comando IOS.
    note     : Texto informativo opcional que aparece sobre los comandos.
    """
    win = tk.Toplevel(root)
    win.title(f"Vista Previa — {title}")
    win.configure(bg=BG)
    win.geometry("900x600")
    win.minsize(700, 400)
    win.resizable(True, True)

    # ── Encabezado ────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=BG)
    hdr.pack(fill="x", padx=16, pady=(14, 2))

    tk.Label(hdr, text=f"📋  {title}", bg=BG, fg=ACCENT,
             font=("Consolas", 12, "bold")).pack(side="left")
    tk.Label(hdr, text=f"  {len(commands)} comandos",
             bg=BG, fg=TEXT2, font=("Consolas", 10)).pack(side="left", padx=6)

    # ── Nota informativa (opcional) ───────────────────────────────────────────
    if note:
        tk.Label(win, text=f"ℹ  {note}", bg=BG, fg=WARN,
                 font=("Consolas", 9), wraplength=860,
                 justify="left").pack(padx=16, anchor="w", pady=(0, 4))

    # ── Caso sin comandos ─────────────────────────────────────────────────────
    if not commands:
        tk.Label(win,
                 text="Sin comandos — agrega datos en esta pestaña primero.",
                 bg=BG, fg=TEXT2, font=("Consolas", 11)).pack(pady=50)
        tk.Button(win, text="✕  Cerrar", command=win.destroy,
                  bg="#6e2020", fg=TEXT, font=("Consolas", 10),
                  relief="flat", padx=12, pady=5,
                  cursor="hand2").pack()
        _center(win, root)
        return

    # ── Área de texto con scrollbars ──────────────────────────────────────────
    frm = tk.Frame(win, bg=BORDER, bd=1)
    frm.pack(fill="both", expand=True, padx=16, pady=6)

    txt = tk.Text(
        frm,
        bg="#0d1117", fg="#e6edf3",
        font=("Consolas", 10),
        wrap="none",
        relief="flat", bd=0,
        padx=10, pady=8,
        selectbackground=ACCENT,
        selectforeground="#0d1117",
        cursor="arrow",
    )
    vsb = tk.Scrollbar(frm, orient="vertical",   command=txt.yview)
    hsb = tk.Scrollbar(frm, orient="horizontal", command=txt.xview)
    txt.config(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    vsb.pack(side="right",  fill="y")
    hsb.pack(side="bottom", fill="x")
    txt.pack(fill="both", expand=True)

    # ── Tags de color ─────────────────────────────────────────────────────────
    txt.tag_configure("block",   foreground="#79c0ff")   # azul: interface/vlan/router
    txt.tag_configure("cmd",     foreground="#a5d6ff")   # azul suave: ip/network/switchport
    txt.tag_configure("neg",     foreground="#ff7b72")   # rojo: no ...
    txt.tag_configure("action",  foreground="#3fb950")   # verde: no shutdown
    txt.tag_configure("end_kw",  foreground="#8b949e")   # gris: exit / end
    txt.tag_configure("comment", foreground="#484f58",
                      font=("Consolas", 10, "italic"))   # muy gris: comentarios
    txt.tag_configure("lnum",    foreground="#3d444d")   # número de línea
    txt.tag_configure("default", foreground="#e6edf3")   # texto normal

    # ── Insertar líneas numeradas ─────────────────────────────────────────────
    for i, cmd in enumerate(commands, start=1):
        # Número de línea en gris oscuro
        txt.insert("end", f"{i:>4}  ", "lnum")
        tag = _color_tag(cmd)
        txt.insert("end", cmd + "\n", tag)

    txt.config(state="disabled")

    # ── Barra de botones ──────────────────────────────────────────────────────
    btn_bar = tk.Frame(win, bg=BG)
    btn_bar.pack(fill="x", padx=16, pady=(2, 12))

    def _copy():
        win.clipboard_clear()
        win.clipboard_append("\n".join(commands))
        copy_btn.config(text="✔  Copiado!")
        win.after(1800, lambda: copy_btn.config(text="📋  Copiar al portapapeles"))

    copy_btn = tk.Button(
        btn_bar, text="📋  Copiar al portapapeles",
        command=_copy,
        bg=BG3, fg=TEXT, font=("Consolas", 10),
        relief="flat", padx=12, pady=5, cursor="hand2",
    )
    copy_btn.pack(side="left", padx=4)

    tk.Button(
        btn_bar, text="✕  Cerrar",
        command=win.destroy,
        bg="#6e2020", fg=TEXT, font=("Consolas", 10),
        relief="flat", padx=12, pady=5, cursor="hand2",
    ).pack(side="right", padx=4)

    # ── Centrar y modal ───────────────────────────────────────────────────────
    _center(win, root)
    win.transient(root)
    win.grab_set()


def _center(win, root):
    """Centra la ventana Toplevel respecto a la ventana raíz."""
    win.update_idletasks()
    rw = root.winfo_rootx() + root.winfo_width()  // 2
    rh = root.winfo_rooty() + root.winfo_height() // 2
    ww, wh = win.winfo_width(), win.winfo_height()
    win.geometry(f"+{max(0, rw - ww // 2)}+{max(0, rh - wh // 2)}")
