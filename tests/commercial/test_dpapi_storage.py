import json
import sys
import tempfile
import unittest
from pathlib import Path

from app.commercial.security import DPAPIProtector, EncryptedFileStore, UnsupportedPlatformError
from app.commercial.security.dpapi import SecureStorageError


class ReversibleProtector:
    def protect(self, plaintext: bytes) -> bytes:
        return bytes(value ^ 0xA5 for value in plaintext)

    def unprotect(self, ciphertext: bytes) -> bytes:
        return self.protect(ciphertext)


class EncryptedFileStoreTests(unittest.TestCase):
    def test_round_trip_and_no_plaintext(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret.json"
            store = EncryptedFileStore(path, ReversibleProtector())
            store.save({"cookie": "sensitive-value"})
            self.assertEqual(store.load(), {"cookie": "sensitive-value"})
            self.assertNotIn("sensitive-value", path.read_text(encoding="utf-8"))

    def test_corrupt_envelope_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret.json"
            path.write_text(json.dumps({"version": 1, "ciphertext": "***"}), encoding="utf-8")
            with self.assertRaises(SecureStorageError):
                EncryptedFileStore(path, ReversibleProtector()).load()


class DPAPITests(unittest.TestCase):
    def test_windows_round_trip_or_explicit_non_windows_error(self):
        protector = DPAPIProtector(entropy=b"unit-test")
        if sys.platform == "win32":
            encrypted = protector.protect(b"secret")
            self.assertNotEqual(encrypted, b"secret")
            self.assertEqual(protector.unprotect(encrypted), b"secret")
        else:
            with self.assertRaises(UnsupportedPlatformError):
                protector.protect(b"secret")


if __name__ == "__main__":
    unittest.main()

