from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from .errors import LicenseBindingError, LicenseNetworkError, LicenseServerError, LicenseSignatureError
from .identity import InstallationIdentityStore
from .models import LicenseClaims, LicenseDecision, LicenseState, SignedLicense, parse_timestamp
from .verification import Ed25519LicenseVerifier


class LicenseStore(Protocol):
    def save(self, value: object) -> None: ...

    def load(self) -> object | None: ...

    def delete(self) -> None: ...


class LicenseApi(Protocol):
    async def activate(self, activation_code: str, installation_id: str, device_fingerprint: str): ...

    async def validate(self, signed_license: Mapping[str, Any], installation_id: str, device_fingerprint: str): ...

    async def deactivate(self, signed_license: Mapping[str, Any], installation_id: str, device_fingerprint: str): ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class LicenseService:
    """Orchestrate activation, online validation, and protected offline use."""

    def __init__(
        self,
        api: LicenseApi,
        verifier: Ed25519LicenseVerifier,
        identity: InstallationIdentityStore,
        store: LicenseStore,
        *,
        offline_grace: timedelta = timedelta(days=3),
        clock_rollback_tolerance: timedelta = timedelta(minutes=5),
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        if offline_grace < timedelta(0):
            raise ValueError("offline_grace cannot be negative")
        self.api = api
        self.verifier = verifier
        self.identity = identity
        self.store = store
        self.offline_grace = offline_grace
        self.clock_rollback_tolerance = clock_rollback_tolerance
        self._now = now

    async def activate(self, activation_code: str) -> LicenseDecision:
        code = activation_code.strip()
        if not code:
            return LicenseDecision(False, LicenseState.INVALID, "请输入激活码")
        installation_id, fingerprint = self._identity()
        response = await self.api.activate(code, installation_id, fingerprint)
        return self._accept_online(response, installation_id, fingerprint)

    async def check_access(self, *, online: bool = True) -> LicenseDecision:
        state = self._load_state()
        if state is None:
            return LicenseDecision(False, LicenseState.MISSING, "尚未激活")
        now = self._current_time()
        clock_rolled_back = self._clock_rolled_back(state, now)
        installation_id, fingerprint = self._identity()
        try:
            signed = SignedLicense.from_mapping(state["license"])
            claims = self._verify_binding(signed, installation_id, fingerprint)
        except (KeyError, TypeError, ValueError, LicenseSignatureError, LicenseBindingError):
            return LicenseDecision(False, LicenseState.INVALID, "本地许可证无效")

        if online:
            try:
                response = await self.api.validate(signed.to_mapping(), installation_id, fingerprint)
                return self._accept_online(response, installation_id, fingerprint)
            except LicenseNetworkError:
                pass
            except LicenseServerError as exc:
                return LicenseDecision(False, LicenseState.REVOKED, str(exc), claims)
        if clock_rolled_back:
            return LicenseDecision(False, LicenseState.CLOCK_ROLLBACK, "检测到系统时间回拨，请联网校验")
        return self._offline_decision(state, signed, claims, now)

    async def validate(self) -> LicenseDecision:
        return await self.check_access(online=True)

    async def deactivate(self) -> None:
        state = self._load_state()
        if state is None:
            return
        installation_id, fingerprint = self._identity()
        signed = SignedLicense.from_mapping(state["license"])
        await self.api.deactivate(signed.to_mapping(), installation_id, fingerprint)
        self.store.delete()

    def local_status(self) -> LicenseDecision:
        state = self._load_state()
        if state is None:
            return LicenseDecision(False, LicenseState.MISSING, "尚未激活")
        now = self._current_time()
        if self._clock_rolled_back(state, now):
            return LicenseDecision(False, LicenseState.CLOCK_ROLLBACK, "检测到系统时间回拨，请联网校验")
        installation_id, fingerprint = self._identity()
        try:
            signed = SignedLicense.from_mapping(state["license"])
            claims = self._verify_binding(signed, installation_id, fingerprint)
        except (KeyError, TypeError, ValueError, LicenseSignatureError, LicenseBindingError):
            return LicenseDecision(False, LicenseState.INVALID, "本地许可证无效")
        return self._offline_decision(state, signed, claims, now)

    def _accept_online(self, response: Mapping[str, Any], installation_id: str, fingerprint: str) -> LicenseDecision:
        try:
            signed = SignedLicense.from_mapping(response)
            claims = self._verify_binding(signed, installation_id, fingerprint)
        except (ValueError, LicenseSignatureError, LicenseBindingError) as exc:
            raise LicenseServerError("license service returned an invalid signed license") from exc
        now = self._current_time()
        server_time = parse_timestamp(response.get("serverTime", response.get("server_time")))
        trusted_now = max(now, server_time) if server_time else now
        if claims.status != "active":
            return LicenseDecision(False, LicenseState.REVOKED, "许可证已停用", claims)
        if claims.expires_at and trusted_now > claims.expires_at:
            return LicenseDecision(False, LicenseState.EXPIRED, "许可证已过期", claims)
        self.store.save(
            {
                "version": 1,
                "license": signed.to_mapping(),
                "last_online": _timestamp(trusted_now),
                "last_seen": _timestamp(trusted_now),
            }
        )
        plan_names = {"MONTHLY": "月卡", "QUARTERLY": "季卡", "YEARLY": "年卡", "LIFETIME": "终身"}
        plan_name = plan_names.get(claims.membership_plan, "会员")
        expiry = f"，有效期至 {claims.expires_at.astimezone().strftime('%Y-%m-%d')}" if claims.expires_at else ""
        return LicenseDecision(True, LicenseState.ACTIVE, f"{plan_name}会员有效{expiry}", claims)

    def _offline_decision(
        self, state: dict[str, Any], signed: SignedLicense, claims: LicenseClaims, now: datetime
    ) -> LicenseDecision:
        if claims.status != "active":
            return LicenseDecision(False, LicenseState.REVOKED, "许可证已停用", claims)
        if claims.expires_at and now > claims.expires_at:
            return LicenseDecision(False, LicenseState.EXPIRED, "许可证已过期", claims)
        try:
            last_online = parse_timestamp(state["last_online"])
        except (KeyError, TypeError, ValueError):
            last_online = None
        if last_online is None:
            return LicenseDecision(False, LicenseState.NETWORK_REQUIRED, "需要联网校验许可证", claims)
        grace_end = last_online + self.offline_grace
        if claims.offline_grace_until:
            grace_end = min(grace_end, claims.offline_grace_until)
        if claims.expires_at:
            grace_end = min(grace_end, claims.expires_at)
        if now > grace_end:
            return LicenseDecision(False, LicenseState.NETWORK_REQUIRED, "离线宽限期已结束，请联网校验", claims)
        state["last_seen"] = _timestamp(max(now, last_online))
        state["license"] = signed.to_mapping()
        self.store.save(state)
        return LicenseDecision(True, LicenseState.OFFLINE_GRACE, "当前处于离线宽限期", claims)

    def _verify_binding(self, signed: SignedLicense, installation_id: str, fingerprint: str) -> LicenseClaims:
        self.verifier.verify(signed)
        claims = LicenseClaims.from_mapping(signed.claims)
        expected_installation = installation_id
        expected_fingerprint = fingerprint
        if claims.binding_hashed:
            expected_installation = hashlib.sha256(installation_id.encode("utf-8")).hexdigest()
            expected_fingerprint = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        if claims.installation_id != expected_installation or claims.device_fingerprint != expected_fingerprint:
            raise LicenseBindingError("license is bound to another installation or device")
        return claims

    def _identity(self) -> tuple[str, str]:
        return self.identity.load_or_create(), self.identity.fingerprint()

    def _load_state(self) -> dict[str, Any] | None:
        value = self.store.load()
        return value if isinstance(value, dict) and value.get("version") == 1 else None

    def _current_time(self) -> datetime:
        value = self._now()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _clock_rolled_back(self, state: Mapping[str, Any], now: datetime) -> bool:
        try:
            last_seen = parse_timestamp(state.get("last_seen"))
        except (TypeError, ValueError):
            return True
        return bool(last_seen and now + self.clock_rollback_tolerance < last_seen)
