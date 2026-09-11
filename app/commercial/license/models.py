from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def decode_base64(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.b64decode(padded, altchars=b"-_", validate=True)
    except ValueError as exc:
        raise ValueError("invalid base64 value") from exc


@dataclass(frozen=True)
class SignedLicense:
    claims: dict[str, Any]
    signature: str
    algorithm: str = "Ed25519"
    payload_bytes: bytes | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SignedLicense:
        container = value.get("license", value)
        if not isinstance(container, Mapping):
            raise ValueError("license response is missing a signed license")
        signature = container.get("signature")
        algorithm = container.get("algorithm", "Ed25519")
        payload = container.get("payload", container.get("claims"))
        if not isinstance(signature, str):
            raise ValueError("license response is missing a signature")
        if isinstance(payload, str):
            payload_bytes = decode_base64(payload)
            decoded = json.loads(payload_bytes.decode("utf-8"))
            if not isinstance(decoded, dict):
                raise ValueError("signed payload must be a JSON object")
            claims = decoded
        elif isinstance(payload, Mapping):
            claims = dict(payload)
            payload_bytes = canonical_json(claims)
        else:
            raise ValueError("license response is missing its payload")
        return cls(claims=claims, signature=signature, algorithm=str(algorithm), payload_bytes=payload_bytes)

    def message(self) -> bytes:
        return self.payload_bytes if self.payload_bytes is not None else canonical_json(self.claims)

    def to_mapping(self) -> dict[str, Any]:
        payload = base64.urlsafe_b64encode(self.message()).rstrip(b"=").decode("ascii")
        return {"algorithm": self.algorithm, "payload": payload, "signature": self.signature}


@dataclass(frozen=True)
class LicenseClaims:
    license_id: str
    installation_id: str
    device_fingerprint: str
    status: str
    issued_at: datetime | None
    expires_at: datetime | None
    offline_grace_until: datetime | None
    binding_hashed: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> LicenseClaims:
        license_id = value.get("licenseId", value.get("license_id", value.get("id")))
        binding_hashed = "installationHash" in value or "deviceFingerprintHash" in value
        required = {
            "license_id": license_id,
            "installation_id": value.get("installationHash", value.get("installation_id")),
            "device_fingerprint": value.get("deviceFingerprintHash", value.get("device_fingerprint")),
        }
        if any(not isinstance(item, str) or not item for item in required.values()):
            raise ValueError("license payload is missing required binding claims")
        return cls(
            license_id=required["license_id"],
            installation_id=required["installation_id"],
            device_fingerprint=required["device_fingerprint"],
            status=str(value.get("status", "active")).lower(),
            issued_at=parse_timestamp(value.get("issuedAt", value.get("issued_at"))),
            expires_at=parse_timestamp(
                value.get("expiresAt", value.get("validUntil", value.get("expires_at", value.get("valid_until"))))
            ),
            offline_grace_until=parse_timestamp(value.get("offlineGraceUntil", value.get("offline_grace_until"))),
            binding_hashed=binding_hashed,
        )


class LicenseState(str, Enum):
    ACTIVE = "active"
    OFFLINE_GRACE = "offline_grace"
    MISSING = "missing"
    EXPIRED = "expired"
    REVOKED = "revoked"
    DEVICE_MISMATCH = "device_mismatch"
    CLOCK_ROLLBACK = "clock_rollback"
    INVALID = "invalid"
    NETWORK_REQUIRED = "network_required"


@dataclass(frozen=True)
class LicenseDecision:
    allowed: bool
    state: LicenseState
    reason: str
    claims: LicenseClaims | None = None
