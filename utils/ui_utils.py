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
    if master and master.winfo_viewable():
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
        y = master.winfo_rooty() + master.winfo_height() - height - padding
    else:
        x = (screen_width // 2) - (width // 2)
        y = screen_height - height - (padding * 3)

    return f"{int(width)}x{int(height)}+{int(x)}+{int(y)}"


def get_bottom_right_geometry(width, height, screen_width, screen_height, padding=20):
    """
    Berechnet den Geometrie-String für Toasts unten rechts in der Bildschirmecke.
    """
    x = screen_width - width - padding
    y = screen_height - height - (padding * 3)

    return f"{int(width)}x{int(height)}+{int(x)}+{int(y)}"


class TextAnimator:
    """
    Ein universeller Helfer für endlose Text-Animationen (z.B. lade Punkte '.', '..', '...').
    """

    def __init__(self, master, interval=500, max_dots=3):
        self.master = master
        self.interval = interval
        self.max_dots = max_dots
        self.dot_count = 0
        self._is_running = False
        self._callbacks = []

    def register(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._tick()

    def stop(self):
        self._is_running = False

    def _tick(self):
        if not self._is_running or not getattr(self.master, "winfo_exists", lambda: False)():
            return

        self.dot_count = (self.dot_count + 1) % (self.max_dots + 1)
        dots = "." * self.dot_count

        for cb in self._callbacks:
            try:
                cb(dots)
            except Exception:
                pass

        self.master.after(self.interval, self._tick)


class CountdownTimer:
    """
    Ein universeller Helfer für finite Countdowns.
    Kapselt die gesamte 'self.after' Logik sauber von der View weg.
    """

    def __init__(self, master, seconds, on_tick_callback=None, on_finish_callback=None):
        self.master = master
        self.total_seconds = seconds
        self.current_seconds = seconds
        self.on_tick_callback = on_tick_callback
        self.on_finish_callback = on_finish_callback

        self._is_running = False
        self._job_id = None

    def start(self):
        if not self._is_running:
            self._is_running = True
            # Feuert direkt den ersten Tick (z.B. "12s")
            self._tick()

    def stop(self):
        self._is_running = False
        if self._job_id and getattr(self.master, "after_cancel", None):
            try:
                self.master.after_cancel(self._job_id)
            except Exception:
                pass
        self._job_id = None

    def _tick(self):
        if not self._is_running or not getattr(self.master, "winfo_exists", lambda: False)():
            return

        if self.current_seconds <= 0:
            self._is_running = False
            if self.on_finish_callback:
                self.on_finish_callback()
            return

        if self.on_tick_callback:
            try:
                self.on_tick_callback(self.current_seconds)
            except Exception:
                pass

        self.current_seconds -= 1
        self._job_id = self.master.after(1000, self._tick)