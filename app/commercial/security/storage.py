"""Atomic encrypted file storage."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Protocol

from .dpapi import SecureStorageError


class Protector(Protocol):
    def protect(self, plaintext: bytes) -> bytes: ...

    def unprotect(self, ciphertext: bytes) -> bytes: ...


class EncryptedFileStore:
    """Store a JSON-compatible object in an encrypted, versioned envelope."""

    def __init__(self, path: str | Path, protector: Protector) -> None:
        self.path = Path(path)
        self.protector = protector

    def save(self, value: object) -> None:
        plaintext = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        encrypted = self.protector.protect(plaintext)
        envelope = json.dumps(
            {"version": 1, "ciphertext": base64.b64encode(encrypted).decode("ascii")},
            separators=(",", ":"),
        ).encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(file_descriptor, "wb") as temporary_file:
                temporary_file.write(envelope)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def load(self) -> object | None:
        if not self.path.exists():
            return None
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
            if envelope.get("version") != 1:
                raise SecureStorageError("unsupported secure storage format")
            encrypted = base64.b64decode(envelope["ciphertext"], validate=True)
            return json.loads(self.protector.unprotect(encrypted).decode("utf-8"))
        except SecureStorageError:
            raise
        except (KeyError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise SecureStorageError("secure storage is corrupt or unreadable") from exc

    def delete(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

