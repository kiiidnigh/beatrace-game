# ================================================
# FILE: ui/components/bug_report_modal.py
# ================================================
import customtkinter as ctk
from utils.ui_utils import get_centered_geometry
from core.i18n import translate
from services.telemetry_service import TelemetryService
from ui.components.custom_popup import CustomPopup


class BugReportModal(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(translate("bug_report.title"))
        self.resizable(False, False)

        # Bindet sich an das Hauptfenster (minimiert sich mit)
        self.transient(master)

        self.geometry(get_centered_geometry(master, width=500, height=400))

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text=translate("bug_report.question"), font=("Helvetica", 16, "bold")).pack(pady=(20, 10))
        self.textbox = ctk.CTkTextbox(self, width=450, height=200)
        self.textbox.pack(pady=10)
        ctk.CTkLabel(self, text=translate("bug_report.info"), text_color="gray", font=("Helvetica", 12)).pack(
            pady=(0, 10))

        self.btn_submit = ctk.CTkButton(self, text=translate("bug_report.btn_send"), fg_color="#c0392b",
                                        hover_color="#e74c3c", command=self.submit)
        self.btn_submit.pack(pady=10)

    def submit(self):
        user_msg = self.textbox.get("1.0", "end-1c").strip()
        if not user_msg:
            user_msg = translate("bug_report.empty_desc")
        self.btn_submit.configure(state="disabled", text=translate("bug_report.btn_sending"))

        def on_done(success):
            if self.winfo_exists():
                self.destroy()
            if success:
                CustomPopup(master=self.master, title=translate("bug_report.success_title"),
                            message=translate("bug_report.success_msg"),
                            icon="✅", btn_color="#1DB954", sound_type="ok")
            else:
                CustomPopup(master=self.master, title=translate("bug_report.error_title"),
                            message=translate("bug_report.error_msg"),
                            icon="❌", btn_color="#c0392b", sound_type="error")

        TelemetryService.send_crash_report(user_message=user_msg,
                                           callback=lambda s: self.after(0, lambda: on_done(s)))