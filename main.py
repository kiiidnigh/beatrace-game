# ================================================
# FILE: main.py
# ================================================
import os
import sys

if "--profile" in sys.argv:
    idx = sys.argv.index("--profile")
    profile_name = sys.argv[idx + 1]
    os.environ["BEATRACE_PROFILE"] = profile_name
    print(f"🛠️ [DEV MODE] Isoliertes Profil geladen: {profile_name}")

import logging
from datetime import datetime
from config import settings
from services.sound_service import SoundService
from ui.main_window import MainWindow
from core.i18n import Translator


def setup_logging():
    log_dir = os.path.join(settings.APPDATA_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(log_dir, f"beatrace_instance_{timestamp}_PID{os.getpid()}.log")

    settings.CURRENT_LOG_FILE = log_filename

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    logging.info("=" * 40)
    logging.info(f"Beatrace Client gestartet (PID: {os.getpid()})")
    logging.info(f"Speicherort Daten: {settings.APPDATA_DIR}")
    logging.info("=" * 40)


if __name__ == "__main__":
    setup_logging()
    try:
        # i18n System initialisieren, BEVOR die UI geladen wird
        Translator.initialize()

        # Startet den Sound Service global.
        # Er klinkt sich automatisch in die UI Buttons ein.
        sound_service = SoundService()

        app = MainWindow()

        def tk_report_exception(self, exc_type, exc_value, exc_traceback):
            logging.error("Tkinter Callback Exception", exc_info=(exc_type, exc_value, exc_traceback))

        app.report_callback_exception = tk_report_exception.__get__(app, MainWindow)
        app.mainloop()
    except Exception:
        logging.critical("Kritischer Absturz beim Start", exc_info=True)