# ================================================
# FILE: services/storage/__init__.py
# ================================================
from .base_adapter import BaseStorageAdapter, SyncException
from .rclone_adapter import RcloneCloudAdapter

# OCP: Hier können später LocalNetworkAdapter, DropboxAdapter etc. ergänzt werden.