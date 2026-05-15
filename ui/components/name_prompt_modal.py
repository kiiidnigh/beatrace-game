# ================================================
# FILE: ui/components/name_prompt_modal.py
# ================================================
import customtkinter as ctk
from utils.ui_utils import get_centered_geometry
from utils.file_utils import load_prefs, save_prefs
from core.i18n import translate


class NamePromptModal(ctk.CTkToplevel):
    def __init__(self, master, game_state, on_submit_callback):
        super().__init__(master)
        self.game_state = game_state
        self.on_submit_callback = on_submit_callback

        self.title(translate("social.invite_name_title"))
        self.resizable(False, False)

        # An Hauptfenster gebunden
        self.transient(master)
        self.grab_set()

        self.geometry(get_centered_geometry(master, width=350, height=200))

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text=translate("social.invite_name_prompt"), font=("Helvetica", 14, "bold")).pack(
            pady=(20, 10))

        self.entry = ctk.CTkEntry(self, width=200, justify="center")
        self.entry.pack(pady=10)
        self.entry.focus()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text=translate("common.btn_save"), width=100,
                      fg_color="#1DB954", hover_color="#14833b", command=self.on_submit).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=translate("common.btn_cancel"), width=100,
                      fg_color="#c0392b", hover_color="#e74c3c", command=self.destroy).pack(side="left", padx=5)

    def on_submit(self):
        new_name = self.entry.get().strip()
        if new_name:
            self.game_state.my_name = new_name
            prefs = load_prefs()
            prefs["last_username"] = new_name
            save_prefs(prefs)

            self.destroy()
            if self.on_submit_callback:
                self.on_submit_callback(new_name)