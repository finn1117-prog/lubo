from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Protocol, runtime_checkable

from .cookies import BrowserCookie, build_cookie_header
from .errors import LoginDisplayError
from .models import BrowserLoginResult, PlatformProfile


class LoginState(StrEnum):
    SIGNED_OUT = "signed_out"
    LOADING = "loading"
    SIGNED_IN = "signed_in"
    TEMPORARY = "temporary"
    INVALID = "invalid"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class LoginSnapshot:
    state: LoginState
    message: str = ""
    verified_at: str | None = None
    has_credential: bool = False


@runtime_checkable
class SecureCookieStore(Protocol):
    def save_cookie(
        self, platform_key: str, cookie_header: str, *, temporary: bool = False
    ) -> object | Awaitable[object]: ...

    def load_cookie(self, platform_key: str) -> str | None | Awaitable[str | None]: ...

    def delete_cookie(self, platform_key: str) -> object | Awaitable[object]: ...


class BrowserLogin(Protocol):
    def capture(self, profile: PlatformProfile) -> BrowserLoginResult | list[BrowserCookie]: ...


RuntimeCookieCallback = Callable[[str, str | None], object | Awaitable[object]]
StateCallback = Callable[[LoginSnapshot], object | Awaitable[object]]


async def _resolve(value):
    return await value if inspect.isawaitable(value) else value


class EncryptedStoreCookieAdapter:
    """Wrap one ``commercial.security.EncryptedFileStore`` per platform."""

    def __init__(self, store, platform_key: str):
        self._store = store
        self._platform_key = platform_key
        self.verified_at: str | None = None
        self.temporary = False

    def _check_key(self, platform_key: str) -> None:
        if platform_key != self._platform_key:
            raise ValueError("Cookie store used with the wrong platform")

    @property
    def has_credential(self) -> bool:
        path = getattr(self._store, "path", None)
        return bool(path and path.exists())

    def save_cookie(self, platform_key: str, cookie_header: str, *, temporary: bool = False) -> None:
        self._check_key(platform_key)
        self.verified_at = datetime.now(timezone.utc).isoformat()
        self.temporary = temporary
        self._store.save(
            {
                "version": 2,
                "platform": platform_key,
                "cookie_header": cookie_header,
                "verified_at": self.verified_at,
                "temporary": temporary,
                "expires_at": ((datetime.now(timezone.utc) + timedelta(hours=2)).isoformat() if temporary else None),
            }
        )

    def load_cookie(self, platform_key: str) -> str | None:
        self._check_key(platform_key)
        payload = self._store.load()
        if payload is None:
            return None
        if not isinstance(payload, dict) or payload.get("platform") != platform_key:
            raise RuntimeError("本地登录凭据格式无效")
        if platform_key == "xhs" and payload.get("version", 1) < 2:
            self._store.delete()
            return None
        expires_at = payload.get("expires_at")
        if payload.get("temporary") and isinstance(expires_at, str):
            if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                self._store.delete()
                return None
        self.temporary = bool(payload.get("temporary"))
        timestamp = payload.get("verified_at")
        self.verified_at = timestamp if isinstance(timestamp, str) else None
        value = payload.get("cookie_header")
        return value if isinstance(value, str) and value else None

    def delete_cookie(self, platform_key: str) -> None:
        self._check_key(platform_key)
        self._store.delete()
        self.verified_at = None
        self.temporary = False


class CookieLoginService:
    def __init__(
        self,
        profile: PlatformProfile,
        browser: BrowserLogin,
        store: SecureCookieStore,
        runtime_cookie_callback: RuntimeCookieCallback,
        state_callback: StateCallback | None = None,
    ):
        self.profile = profile
        self._browser = browser
        self._store = store
        self._runtime_cookie_callback = runtime_cookie_callback
        self._state_callback = state_callback
        self.snapshot = LoginSnapshot(LoginState.SIGNED_OUT, "尚未登录")

    async def _publish(
        self,
        state: LoginState,
        message: str,
        verified_at: str | None = None,
        has_credential: bool = False,
    ) -> None:
        self.snapshot = LoginSnapshot(state, message, verified_at, has_credential)
        if self._state_callback:
            await _resolve(self._state_callback(self.snapshot))

    def set_state_callback(self, callback: StateCallback | None) -> None:
        self._state_callback = callback

    async def restore(self) -> LoginSnapshot:
        try:
            cookie_header = await _resolve(self._store.load_cookie(self.profile.key))
            if not cookie_header:
                await self._publish(LoginState.SIGNED_OUT, "尚未登录")
                return self.snapshot
            await _resolve(self._runtime_cookie_callback(self.profile.key, cookie_header))
            temporary = bool(getattr(self._store, "temporary", False))
            await self._publish(
                LoginState.TEMPORARY if temporary else LoginState.SIGNED_IN,
                "游客凭据临时有效，请登录真实账号以便长期录制" if temporary else "已从本机安全存储恢复登录",
                getattr(self._store, "verified_at", None),
                True,
            )
        except Exception:
            has_credential = bool(getattr(self._store, "has_credential", False))
            await self._publish(
                LoginState.INVALID if has_credential else LoginState.ERROR,
                "本机登录凭据已失效，请重新登录" if has_credential else "无法读取本机登录凭据，请重新登录",
                has_credential=has_credential,
            )
        return self.snapshot

    async def login(self) -> LoginSnapshot:
        previous = self.snapshot
        await self._publish(
            LoginState.LOADING,
            f"正在打开{self.profile.display_name}官方登录页…",
            previous.verified_at,
            previous.has_credential,
        )
        try:
            if inspect.iscoroutinefunction(self._browser.capture):
                captured = await self._browser.capture(self.profile)
            else:
                captured = await asyncio.to_thread(self._browser.capture, self.profile)
            result = captured if isinstance(captured, BrowserLoginResult) else BrowserLoginResult(captured)
            cookie_header = build_cookie_header(result.cookies, self.profile)
            await _resolve(self._store.save_cookie(self.profile.key, cookie_header, temporary=result.temporary))
            await _resolve(self._runtime_cookie_callback(self.profile.key, cookie_header))
            await self._publish(
                LoginState.TEMPORARY if result.temporary else LoginState.SIGNED_IN,
                (
                    "游客凭据临时有效 2 小时；如需长期稳定录制，请登录真实账号"
                    if result.temporary
                    else "登录成功，凭据已加密保存在本机"
                ),
                getattr(self._store, "verified_at", None),
                True,
            )
        except LoginDisplayError as exc:
            await self._publish(
                LoginState.INVALID if previous.has_credential else LoginState.ERROR,
                str(exc) or "登录未完成，请重试",
                previous.verified_at,
                previous.has_credential,
            )
        except Exception:
            # Never surface arbitrary exception text: third-party errors can
            # contain request headers and therefore session cookies.
            await self._publish(
                LoginState.ERROR,
                "登录失败，请检查网络和登录组件后重试",
                previous.verified_at,
                previous.has_credential,
            )
        return self.snapshot

    async def mark_invalid(self, message: str = "登录凭据已失效，请重新登录") -> LoginSnapshot:
        """Let a platform use/validation failure update the shared UI state."""
        await self._publish(
            LoginState.INVALID,
            message,
            self.snapshot.verified_at,
            self.snapshot.has_credential,
        )
        return self.snapshot

    async def logout(self) -> LoginSnapshot:
        previous = self.snapshot
        await self._publish(
            LoginState.LOADING,
            "正在退出…",
            previous.verified_at,
            previous.has_credential,
        )
        try:
            await _resolve(self._store.delete_cookie(self.profile.key))
            await _resolve(self._runtime_cookie_callback(self.profile.key, None))
            await self._publish(LoginState.SIGNED_OUT, "已退出，本机登录凭据已删除")
        except Exception:
            await self._publish(
                LoginState.ERROR,
                "退出失败，请稍后重试",
                previous.verified_at,
                previous.has_credential,
            )
        return self.snapshot
