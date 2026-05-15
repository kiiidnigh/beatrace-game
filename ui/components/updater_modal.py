# ================================================
# FILE: ui/components/updater_modal.py
# ================================================
import customtkinter as ctk
from utils.ui_utils import get_centered_geometry
from core.event_bus import EventBus
from core.i18n import translate as t
from ui.components.custom_popup import CustomPopup


class UpdaterModal(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(t("updater.loading_title"))
        self.attributes('-topmost', True)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.geometry(get_centered_geometry(master, width=400, height=220))

        self._is_destroyed = False
        self.setup_ui()

        self._listeners = {
            "UPDATER_PROGRESS": lambda d: self.safe_execute(self._update_ui, d),
            "UPDATER_ERROR": lambda d: self.safe_execute(self._handle_error, d)
        }

        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def setup_ui(self):
        self.lbl_status = ctk.CTkLabel(self, text=t("updater.progress_connecting"),
                                       font=("Helvetica", 14, "bold"), text_color="#1DB954")
        self.lbl_status.pack(pady=(30, 15))

        self.progress_bar = ctk.CTkProgressBar(self, width=300, height=15, progress_color="#1DB954")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.lbl_percent = ctk.CTkLabel(self, text="0%", font=("Helvetica", 14), text_color="gray")
        self.lbl_percent.pack()

    def safe_execute(self, func, *args, **kwargs):
        def wrapper():
            if not getattr(self, '_is_destroyed', True) and self.winfo_exists():
                try:
                    func(*args, **kwargs)
                except Exception:
                    pass

        self.after(0, wrapper)

    def _update_ui(self, data):
        progress = data.get("progress", 0.0)
        status = data.get("status", "")

        self.progress_bar.set(progress)
        self.lbl_percent.configure(text=f"{int(progress * 100)}%")

        if status == "downloading":
            self.lbl_status.configure(text=t("updater.progress_downloading"))
        elif status == "installing":
            self.lbl_status.configure(text=t("updater.progress_installing"))

    def _handle_error(self, data):
        error_msg = t("updater.error_msg").replace("{error}", data.get("error", "Unknown Error"))
        self.destroy()
        CustomPopup(
            master=self.master,
            title=t("updater.error_title"),
            message=error_msg,
            icon="❌",
            btn_color="#c0392b",
            sound_type="error"
        )

    def destroy(self):
        self._is_destroyed = True
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)
        super().destroy()