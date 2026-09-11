"""Per-install identity and privacy-preserving device fingerprint."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path


def _windows_machine_guid() -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        import winreg

        access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, access) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip()
    except OSError:
        return None


def default_device_components() -> dict[str, str]:
    """Return stable machine attributes; callers must never transmit these raw."""
    components = {
        "system": platform.system(),
        "machine": platform.machine(),
        "node": platform.node(),
    }
    machine_guid = _windows_machine_guid()
    if machine_guid:
        components["windows_machine_guid"] = machine_guid
    else:
        components["mac_address"] = f"{uuid.getnode():012x}"
    return components


def device_fingerprint(components: Mapping[str, str] | None = None) -> str:
    values = components or default_device_components()
    canonical = "\n".join(f"{key}={str(values[key]).strip().lower()}" for key in sorted(values) if values[key])
    return hashlib.sha256(f"lubo-daren-device-v1\n{canonical}".encode()).hexdigest()


class InstallationIdentityStore:
    def __init__(
        self,
        path: str | Path,
        component_provider: Callable[[], Mapping[str, str]] = default_device_components,
    ):
        self.path = Path(path)
        self._component_provider = component_provider

    def load_or_create(self) -> str:
        existing = self._load()
        if existing:
            return existing
        installation_id = str(uuid.uuid4())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
                json.dump({"version": 1, "installation_id": installation_id}, temporary_file)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return installation_id

    def fingerprint(self) -> str:
        return device_fingerprint(self._component_provider())

    def _load(self) -> str | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))["installation_id"]
            return str(uuid.UUID(value))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None
