# ================================================
# FILE: utils/ui_utils.py
# ================================================

def get_centered_geometry(master, width, height):
    """
    Berechnet den Geometrie-String (BreitexHöhe+X+Y), um ein Fenster
    exakt mittig über seinem Master-Fenster zu positionieren.
    """
    if not master:
        return f"{width}x{height}"

    master.update_idletasks()
    x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
    y = master.winfo_rooty() + (master.winfo_height() // 2) - (height // 2)

    return f"{int(width)}x{int(height)}+{int(x)}+{int(y)}"


def get_bottom_center_geometry(master, width, height, screen_width, screen_height, padding=20):
    """
    Berechnet den Geometrie-String für Toasts.
    Ist das Master-Fenster sichtbar, dockt es unten an.
    Ist es unsichtbar (Stealth), dockt es unten am Bildschirm an.
    """
    if master and master.winfo_viewable():
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
        y = master.winfo_rooty() + master.winfo_height() - height - padding
    else:
        x = (screen_width // 2) - (width // 2)
        y = screen_height - height - (padding * 3)

    return f"{int(width)}x{int(height)}+{int(x)}+{int(y)}"