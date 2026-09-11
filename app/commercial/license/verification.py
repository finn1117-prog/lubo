"""Ed25519 verification for server-issued license documents."""

from __future__ import annotations

import binascii

from .errors import LicenseSignatureError
from .models import SignedLicense, decode_base64


def _decode_public_key(value: str | bytes) -> bytes:
    if isinstance(value, bytes):
        return value
    stripped = value.strip()
    if stripped.startswith("-----BEGIN"):
        return stripped.encode("ascii")
    try:
        raw = bytes.fromhex(stripped) if len(stripped) == 64 else decode_base64(stripped)
    except (ValueError, binascii.Error) as exc:
        raise LicenseSignatureError("invalid Ed25519 public key encoding") from exc
    if len(raw) != 32:
        raise LicenseSignatureError("Ed25519 public key must contain 32 raw bytes")
    return raw


class Ed25519LicenseVerifier:
    """Verify licenses with a configured public key; private keys never enter the client."""

    def __init__(self, public_key: str | bytes) -> None:
        if not public_key:
            raise ValueError("a license verification public key is required")
        self._public_key = _decode_public_key(public_key)

    def verify(self, license_document: SignedLicense) -> None:
        if license_document.algorithm != "Ed25519":
            raise LicenseSignatureError("unsupported license signature algorithm")
        try:
            signature = decode_base64(license_document.signature)
        except ValueError as exc:
            raise LicenseSignatureError("invalid license signature encoding") from exc

        cryptography_error: Exception | None = None
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.hazmat.primitives.serialization import load_pem_public_key

            if self._public_key.startswith(b"-----BEGIN"):
                key = load_pem_public_key(self._public_key)
            else:
                key = Ed25519PublicKey.from_public_bytes(self._public_key)
            key.verify(signature, license_document.message())
            return
        except ImportError as exc:
            cryptography_error = exc
        except Exception as exc:
            raise LicenseSignatureError("license signature verification failed") from exc

        try:
            from Crypto.PublicKey import ECC
            from Crypto.Signature import eddsa

            if self._public_key.startswith(b"-----BEGIN"):
                key = ECC.import_key(self._public_key)
            else:
                key = eddsa.import_public_key(self._public_key)
            verifier = eddsa.new(key, mode="rfc8032")
            verifier.verify(license_document.message(), signature)
        except ImportError as exc:
            raise LicenseSignatureError(
                "Ed25519 verification requires cryptography or pycryptodome"
            ) from (cryptography_error or exc)
        except Exception as exc:
            raise LicenseSignatureError("license signature verification failed") from exc
