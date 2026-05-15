# ================================================
# FILE: services/daws/base_adapter.py
# ================================================
from abc import ABC, abstractmethod

class BaseDAWAdapter(ABC):
    @property
    @abstractmethod
    def name(self):
        """Name der DAW (z.B. 'FL Studio')"""
        pass

    @property
    @abstractmethod
    def process_name(self):
        """Prozess-Name (z.B. 'fl64.exe')"""
        pass

    @property
    @abstractmethod
    def executable_path(self):
        """Der Pfad zur ausführbaren Datei (.exe)"""
        pass

    @abstractmethod
    def is_running(self):
        """Prüft, ob die DAW gerade läuft"""
        pass

    @abstractmethod
    def kill_all_instances(self):
        """Beendet alle laufenden Prozesse dieser DAW"""
        pass

    @abstractmethod
    def force_save_and_close(self):
        """Triggert den Auto-Save und schließt die DAW"""
        pass