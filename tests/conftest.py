# ================================================
# FILE: tests/conftest.py
# ================================================
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config.settings
from core.event_bus import EventBus
from core.game_state import GameState
from services.daws.base_adapter import BaseDAWAdapter
from services.storage.base_adapter import BaseStorageAdapter


# --- ULTIMATIVE ISOLATION (SANDBOXING) ---
@pytest.fixture(autouse=True)
def isolate_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(config.settings, "APPDATA_DIR", str(tmp_path))


# --- EVENTBUS SPION ---
class EventCatcher:
    def __init__(self):
        self.fired_events = []
        self.event_data = {}
        self.original_emit = EventBus.emit
        EventBus.emit = self._spy_emit

    def _spy_emit(self, event_type, data=None):
        self.fired_events.append(event_type)
        if data: self.event_data[event_type] = data
        self.original_emit(event_type, data)

    def restore(self):
        EventBus.emit = self.original_emit


@pytest.fixture(autouse=True)
def event_catcher():
    EventBus._listeners.clear()
    EventBus._ui_wrappers.clear()
    EventBus.clear_history()
    catcher = EventCatcher()
    yield catcher
    catcher.restore()


# --- MOCKS & FAKES (OCP & SoC) ---
class DummyDAWAdapter(BaseDAWAdapter):
    def __init__(self):
        self._is_running = False

    @property
    def name(self): return "Dummy Studio"

    @property
    def process_name(self): return "dummy.exe"

    @property
    def executable_path(self): return "C:\\dummy\\dummy.exe"

    def is_running(self): return self._is_running

    def kill_all_instances(self):
        was_running = self._is_running
        self._is_running = False
        return was_running

    def force_save_and_close(self):
        self._is_running = False
        return True


@pytest.fixture
def dummy_daw(): return DummyDAWAdapter()


# NEU: Cloud Mock für sichere Tests
class MockStorageAdapter(BaseStorageAdapter):
    def __init__(self):
        self.authenticated = True
        self.uploads = []
        self.downloads = []

    def is_authenticated(self): return self.authenticated

    def authenticate(self): self.authenticated = True

    def upload(self, local_path, remote_path): self.uploads.append((local_path, remote_path))

    def download(self, remote_path, local_path): self.downloads.append((remote_path, local_path))


@pytest.fixture
def mock_storage(): return MockStorageAdapter()


class MockNetworkManager:
    def __init__(self):
        self.is_connected = False
        self.sent_signals = []

    def connect(self, name, code): self.is_connected = True

    def disconnect(self): self.is_connected = False

    def send_signal(self, command, data=None):
        self.sent_signals.append({"command": command, "data": data or {}})


@pytest.fixture
def mock_network(): return MockNetworkManager()


class MockRouter:
    def __init__(self):
        self.current_view = None

    def show_finish(self): self.current_view = "FinishView"

    def show_home(self): self.current_view = "HomeView"

    def start_game(self): self.current_view = "GameView"


@pytest.fixture
def mock_router(): return MockRouter()


class MockIdentity:
    def get_or_create_id(self): return "TEST#123456"

    def get_public_id(self): return "TEST"

    def get_private_token(self): return "123456"

    def get_display_name(self): return "TestPlayer"


@pytest.fixture
def dummy_identity_service(): return MockIdentity()


@pytest.fixture
def empty_game_state(dummy_identity_service):
    state = GameState(dummy_identity_service)
    state.reset_match_data()
    return state