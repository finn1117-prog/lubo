import base64
import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa

from app.commercial.license import (
    Ed25519LicenseVerifier,
    InstallationIdentityStore,
    LicenseApiClient,
    LicenseNetworkError,
    LicenseService,
    LicenseSignatureError,
    LicenseState,
    SignedLicense,
    device_fingerprint,
)


class MemoryStore:
    def __init__(self):
        self.value = None

    def save(self, value):
        self.value = value

    def load(self):
        return self.value

    def delete(self):
        self.value = None


class FakeApi:
    def __init__(self, response):
        self.response = response
        self.offline = False
        self.activation_code = None

    async def activate(self, activation_code, installation_id, device_fingerprint):
        self.activation_code = activation_code
        return self.response

    async def validate(self, signed_license, installation_id, device_fingerprint):
        if self.offline:
            raise LicenseNetworkError("offline")
        return self.response

    async def deactivate(self, signed_license, installation_id, device_fingerprint):
        return {}


def signed_response(private_key, claims, server_time):
    document = SignedLicense(dict(claims), "")
    signature = eddsa.new(private_key, "rfc8032").sign(document.message())
    return {
        "license": SignedLicense(dict(claims), base64.b64encode(signature).decode("ascii")).to_mapping(),
        "serverTime": server_time.isoformat(),
    }


class IdentityTests(unittest.TestCase):
    def test_installation_id_and_fingerprint_are_stable(self):
        components = {"machine": "AMD64", "guid": "ABC"}
        with tempfile.TemporaryDirectory() as directory:
            identity = InstallationIdentityStore(Path(directory) / "identity.json", lambda: components)
            self.assertEqual(identity.load_or_create(), identity.load_or_create())
            self.assertEqual(identity.fingerprint(), device_fingerprint(components))
            self.assertNotIn("ABC", identity.fingerprint())


class LicenseApiTests(unittest.IsolatedAsyncioTestCase):
    def test_http_is_limited_to_local_development(self):
        client = httpx.AsyncClient(base_url="http://127.0.0.1:3000")
        self.addAsyncCleanup(client.aclose)
        LicenseApiClient("http://127.0.0.1:3000", client=client)
        with self.assertRaises(ValueError):
            LicenseApiClient("http://licenses.example.com", client=client)

    async def test_activation_uses_camel_case_contract(self):
        captured = {}

        async def handler(request):
            captured.update(__import__("json").loads(request.content))
            return httpx.Response(200, json={"ok": True})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost:3000") as client:
            api = LicenseApiClient("http://localhost:3000", client=client)
            await api.activate("CODE", "installation", "fingerprint")
        self.assertEqual(
            captured,
            {"activationCode": "CODE", "installationId": "installation", "deviceFingerprint": "fingerprint"},
        )


class SignatureTests(unittest.TestCase):
    def test_typescript_contract_fixture_verifies_and_round_trips(self):
        payload = (
            "eyJkZXZpY2VGaW5nZXJwcmludEhhc2giOiJiYmJiIiwiZXhwaXJlc0F0IjpudWxsLCJpbnN0YWxsYXRpb25IYXNoIjoiYWFh"
            "YSIsImlzc3VlZEF0IjoiMjAyNi0wOS0xMVQwMDowMDowMC4wMDBaIiwibGljZW5zZUlkIjoiZml4dHVyZS1saWNlbnNlIiwib2"
            "ZmbGluZUdyYWNlVW50aWwiOiIyMDI2LTA5LTE4VDAwOjAwOjAwLjAwMFoiLCJzdGF0dXMiOiJhY3RpdmUiLCJ2ZXJzaW9uIjox"
            "fQ"
        )
        signature = "UGrDpzAyiWPn06j1DTKIvFEKm6_dvIHi41GCGYEWOs85Yi-QpFsZucZ-zeo8DQoFVmQ143XsnGbLOUqClpaKDw"
        public_key = "11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo="
        fixture = {"algorithm": "Ed25519", "payload": payload, "signature": signature}
        signed = SignedLicense.from_mapping(fixture)
        Ed25519LicenseVerifier(public_key).verify(signed)
        self.assertEqual(signed.to_mapping(), fixture)

    def test_ed25519_verification_rejects_tampering(self):
        private_key = ECC.generate(curve="Ed25519")
        public_key = private_key.public_key().export_key(format="raw")
        claims = {"licenseId": "lic", "installationHash": "iid", "deviceFingerprintHash": "fp"}
        signature = eddsa.new(private_key, "rfc8032").sign(SignedLicense(claims, "").message())
        signed = SignedLicense(claims, base64.b64encode(signature).decode("ascii"))
        verifier = Ed25519LicenseVerifier(public_key)
        verifier.verify(signed)
        signed.claims["license_id"] = "tampered"
        with self.assertRaises(LicenseSignatureError):
            verifier.verify(signed)


class LicenseServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.current = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)
        self.private_key = ECC.generate(curve="Ed25519")
        self.public_key = self.private_key.public_key().export_key(format="raw")
        self.temp = tempfile.TemporaryDirectory()
        self.identity = InstallationIdentityStore(
            Path(self.temp.name) / "identity.json", lambda: {"guid": "stable-device"}
        )
        self.installation_id = self.identity.load_or_create()
        self.fingerprint = self.identity.fingerprint()
        self.claims = {
            "licenseId": "license-1",
            "installationHash": hashlib.sha256(self.installation_id.encode()).hexdigest(),
            "deviceFingerprintHash": hashlib.sha256(self.fingerprint.encode()).hexdigest(),
            "status": "active",
            "membershipPlan": "YEARLY",
            "issuedAt": self.current.isoformat(),
            "validUntil": (self.current + timedelta(days=365)).isoformat(),
        }
        self.api = FakeApi(signed_response(self.private_key, self.claims, self.current))
        self.store = MemoryStore()
        self.service = LicenseService(
            self.api,
            Ed25519LicenseVerifier(self.public_key),
            self.identity,
            self.store,
            offline_grace=timedelta(days=3),
            now=lambda: self.current,
        )

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_activation_stores_signed_license_but_not_activation_code(self):
        result = await self.service.activate("SECRET-ACTIVATION-CODE")
        self.assertTrue(result.allowed)
        self.assertEqual(result.state, LicenseState.ACTIVE)
        self.assertEqual(result.claims.membership_plan, "YEARLY")
        self.assertIn("年卡会员有效", result.reason)
        self.assertNotIn("SECRET-ACTIVATION-CODE", repr(self.store.value))

    async def test_network_failure_uses_limited_offline_grace(self):
        await self.service.activate("CODE")
        self.api.offline = True
        self.current += timedelta(days=2)
        result = await self.service.check_access()
        self.assertTrue(result.allowed)
        self.assertEqual(result.state, LicenseState.OFFLINE_GRACE)
        self.current += timedelta(days=2)
        result = await self.service.check_access()
        self.assertFalse(result.allowed)
        self.assertEqual(result.state, LicenseState.NETWORK_REQUIRED)

    async def test_clock_rollback_is_rejected_offline_and_online_can_recover(self):
        await self.service.activate("CODE")
        self.current -= timedelta(days=1)
        self.api.offline = True
        result = await self.service.check_access()
        self.assertEqual(result.state, LicenseState.CLOCK_ROLLBACK)
        self.api.offline = False
        result = await self.service.check_access()
        self.assertTrue(result.allowed)

    async def test_device_mismatch_invalidates_cached_license(self):
        await self.service.activate("CODE")
        self.identity._component_provider = lambda: {"guid": "different-device"}
        result = self.service.local_status()
        self.assertFalse(result.allowed)
        self.assertEqual(result.state, LicenseState.INVALID)


if __name__ == "__main__":
    unittest.main()
