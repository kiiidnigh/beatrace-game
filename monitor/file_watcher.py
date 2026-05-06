import time
import threading
from utils.file_utils import calculate_md5  # Wir importieren unser neues Werkzeug!


class FileWatcher:
    def __init__(self, file_path):
        self.file_path = file_path
        self._is_monitoring = False

    def wait_for_sync_complete(self, expected_hash, callback):
        self._is_monitoring = True

        def loop():
            wait_start = time.time()

            while self._is_monitoring:
                if not expected_hash:
                    self._is_monitoring = False
                    if callback: callback(success=True)
                    return

                # Wir rufen einfach unser externes Utility auf!
                current_hash = calculate_md5(self.file_path)

                if current_hash == expected_hash:
                    self._is_monitoring = False
                    if callback: callback(success=True)
                    return

                if (time.time() - wait_start) > 60:
                    self._is_monitoring = False
                    if callback: callback(success=False)
                    return

                time.sleep(1.0)

        threading.Thread(target=loop, daemon=True).start()

    def stop(self):
        self._is_monitoring = False