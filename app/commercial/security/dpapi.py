"""Small ctypes wrapper around Windows Data Protection API (DPAPI)."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


class SecureStorageError(RuntimeError):
    """Raised when protected data cannot be encrypted or decrypted."""


class UnsupportedPlatformError(SecureStorageError):
    """Raised when Windows-only secure storage is used elsewhere."""


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes) -> tuple[_DataBlob, object | None]:
    if not data:
        return _DataBlob(0, None), None
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


class DPAPIProtector:
    """Protect bytes for the current Windows user.

    The optional entropy is application-specific and must remain stable. DPAPI
    still binds ciphertext to the Windows user even when no entropy is supplied.
    """

    _CRYPTPROTECT_UI_FORBIDDEN = 0x01

    def __init__(self, entropy: bytes | None = None, description: str = "LuboDaren secure data") -> None:
        self._entropy = entropy
        self._description = description

    @staticmethod
    def _libraries():
        if sys.platform != "win32":
            raise UnsupportedPlatformError("DPAPI secure storage is available only on Windows")
        return ctypes.WinDLL("crypt32", use_last_error=True), ctypes.WinDLL("kernel32", use_last_error=True)

    def protect(self, plaintext: bytes) -> bytes:
        crypt32, kernel32 = self._libraries()
        source, source_buffer = _blob(plaintext)
        entropy, entropy_buffer = _blob(self._entropy or b"")
        output = _DataBlob()
        entropy_pointer = ctypes.byref(entropy) if self._entropy is not None else None
        success = crypt32.CryptProtectData(
            ctypes.byref(source),
            self._description,
            entropy_pointer,
            None,
            None,
            self._CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output),
        )
        del source_buffer, entropy_buffer
        if not success:
            raise SecureStorageError(f"DPAPI encryption failed with Windows error {ctypes.get_last_error()}")
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            kernel32.LocalFree(output.pbData)

    def unprotect(self, ciphertext: bytes) -> bytes:
        crypt32, kernel32 = self._libraries()
        source, source_buffer = _blob(ciphertext)
        entropy, entropy_buffer = _blob(self._entropy or b"")
        output = _DataBlob()
        description = wintypes.LPWSTR()
        entropy_pointer = ctypes.byref(entropy) if self._entropy is not None else None
        success = crypt32.CryptUnprotectData(
            ctypes.byref(source),
            ctypes.byref(description),
            entropy_pointer,
            None,
            None,
            self._CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output),
        )
        del source_buffer, entropy_buffer
        if not success:
            raise SecureStorageError(f"DPAPI decryption failed with Windows error {ctypes.get_last_error()}")
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            if description:
                kernel32.LocalFree(description)
            kernel32.LocalFree(output.pbData)
