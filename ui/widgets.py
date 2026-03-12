"""
ui/widgets.py — Fábrica de widgets Tkinter reutilizables
=========================================================
Provee funciones helper para crear widgets con el estilo visual de la app
(colores, fuentes, bordes) de forma consistente en todas las pestañas.

Ventaja: si quieres cambiar el estilo de todos los botones, solo editas aquí.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# (en core/ y ui/ sube un nivel con dirname() adicional)
import tkinter as tk
from tkinter import ttk, scrolledtext

from constants import (
    BG, BG2, BG3, ACCENT, ACCENT2, SUCCESS, TEXT, TEXT2, BORDER
)


def apply_style(root):
    """
    Configura el tema ttk global de la aplicación.
    Debe llamarse una vez al inicializar la ventana principal.

    Personaliza: Notebook, Tabs, Frame, LabelFrame, Combobox, Checkbutton, Scrollbar.
    """
    s = ttk.Style(root)
    s.theme_use("clam")   # 'clam' es el más personalizable en multiplataforma

    # Notebook (contenedor de pestañas)
    s.configure("TNotebook",       background=BG,  borderwidth=0)
    s.configure("TNotebook.Tab",   background=BG2, foreground=TEXT2,
                padding=[14, 6],   font=("Consolas", 9, "bold"))
    s.map("TNotebook.Tab",
          background=[("selected", BG3)],
          foreground=[("selected", ACCENT)])

    # Frames y contenedores
    s.configure("TFrame",          background=BG2)
    s.configure("TLabelframe",     background=BG2, foreground=TEXT2, bordercolor=BORDER)
    s.configure("TLabelframe.Label", background=BG2, foreground=ACCENT,
                font=("Consolas", 9, "bold"))

    # Combobox (desplegable)
    s.configure("TCombobox",       fieldbackground=BG3, background=BG3,
                foreground=TEXT,   selectbackground=ACCENT2)

    # Checkbutton
    s.configure("TCheckbutton",    background=BG2, foreground=TEXT,
                font=("Consolas", 9))
    s.map("TCheckbutton",          background=[("active", BG2)])

    # Scrollbar
    s.configure("TScrollbar",      background=BG3, troughcolor=BG)


# ── Widgets individuales ───────────────────────────────────────────────────────

def make_frame(parent) -> tk.Frame:
    """Frame simple con fondo de panel (BG2)."""
    return tk.Frame(parent, bg=BG2)


def make_label(parent, text, fg=TEXT2, font=("Consolas", 9), **kw) -> tk.Label:
    """Etiqueta estilizada. fg puede sobreescribirse para colores de estado."""
    return tk.Label(parent, text=text, fg=fg, bg=BG2, font=font, **kw)


def make_entry(parent, width=18, show="", state="normal") -> tk.Entry:
    """
    Campo de entrada de texto.

    Parámetros
    ----------
    show  : '' para texto plano, '*' para contraseñas.
    state : 'normal' o 'disabled'.
    """
    return tk.Entry(
        parent, width=width, bg=BG3, fg=TEXT,
        insertbackground=TEXT, show=show, state=state,
        relief="flat", font=("Consolas", 9),
        highlightthickness=1,
        highlightcolor=ACCENT,
        highlightbackground=BORDER,
    )


def make_button(parent, text, cmd, color=ACCENT2, fg="white", **kw) -> tk.Button:
    """
    Botón estilizado con cursor de mano y colores personalizables.

    color : Color de fondo del botón (por defecto naranja/rojo de acción).
    fg    : Color del texto del botón.
    """
    return tk.Button(
        parent, text=text, command=cmd,
        bg=color, fg=fg, relief="flat",
        activebackground=BG3, activeforeground=TEXT,
        font=("Consolas", 9, "bold"), cursor="hand2",
        padx=10, pady=4, **kw,
    )


def make_listbox(parent, width=70, height=5) -> tk.Listbox:
    """
    Listbox con scroll implícito y estilo oscuro.
    Los ítems se muestran en ACCENT (azul) sobre fondo negro.
    """
    return tk.Listbox(
        parent, width=width, height=height,
        bg=BG, fg=ACCENT,
        selectbackground=ACCENT2, selectforeground="white",
        font=("Consolas", 8), relief="flat",
        highlightthickness=1, highlightbackground=BORDER,
    )


def make_labelframe(parent, text) -> ttk.LabelFrame:
    """LabelFrame con título en ACCENT y borde sutil."""
    return ttk.LabelFrame(parent, text=text, padding=(8, 4))


def make_scrolled_text(parent, width=88, height=6, fg="#00ff41") -> scrolledtext.ScrolledText:
    """
    Área de texto con scrollbar integrado.
    Por defecto usa verde terminal (#00ff41) para el log de consola.
    """
    return scrolledtext.ScrolledText(
        parent, width=width, height=height,
        bg="#010409", fg=fg,
        font=("Consolas", 8),
        insertbackground=TEXT, relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
    )


def make_title(parent, text):
    """Título de sección grande (naranja/rojo), centrado, con margen."""
    tk.Label(
        parent, text=text, fg=ACCENT2, bg=BG2,
        font=("Consolas", 12, "bold"),
    ).pack(pady=(10, 4))


def make_scrolled_frame(parent):
    """
    Crea un frame con scroll vertical usando Canvas + Scrollbar.
    Útil para pestañas con mucho contenido vertical (VLANs, QoS).

    Retorna
    -------
    tk.Frame : El frame interno donde colocar los widgets.
    """
    canvas  = tk.Canvas(parent, bg=BG2, highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    inner_frame = tk.Frame(canvas, bg=BG2)

    # Recalcular el área de scroll cuando cambia el tamaño del frame interno
    inner_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Soporte para scroll con la rueda del mouse
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    return inner_frame
