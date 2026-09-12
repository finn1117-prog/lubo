from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .license import Ed25519LicenseVerifier, InstallationIdentityStore, LicenseApiClient, LicenseService
from .login import PLATFORM_PROFILES, CookieLoginService, EncryptedStoreCookieAdapter, PyWebView2Browser
from .security import DPAPIProtector, EncryptedFileStore


@dataclass(slots=True)
class CommercialRuntime:
    license_service: LicenseService | None
    login_services: dict[str, CookieLoginService]
    configuration_error: str | None = None

    @property
    def login_service(self) -> CookieLoginService | None:
        """Compatibility alias for integrations that still request Kuaishou directly."""
        return self.login_services.get("kuaishou")


def create_commercial_runtime(
    data_dir: str | Path,
    runtime_cookie_callback,
    legacy_cookies: Mapping[str, str] | None = None,
) -> CommercialRuntime:
    """Build the commercial services without coupling them to StreamCap's core."""
    base_url = os.getenv("LICENSE_SERVER_URL", "").strip()
    public_key = os.getenv("LICENSE_PUBLIC_KEY", "").strip().replace("\\n", "\n")
    if not base_url or not public_key:
        return CommercialRuntime(
            license_service=None,
            login_services={},
            configuration_error="商业授权服务尚未配置，请联系软件提供方。",
        )

    secure_dir = Path(data_dir) / "commercial"
    protector = DPAPIProtector(entropy=b"LuboDaren-v1")
    try:
        license_service = LicenseService(
            LicenseApiClient(base_url),
            Ed25519LicenseVerifier(public_key),
            InstallationIdentityStore(secure_dir / "installation.json"),
            EncryptedFileStore(secure_dir / "license.dat", protector),
            offline_grace=timedelta(days=max(0, int(os.getenv("LICENSE_OFFLINE_GRACE_DAYS", "7")))),
        )
        login_services: dict[str, CookieLoginService] = {}
        for profile in PLATFORM_PROFILES:
            cookie_store = EncryptedStoreCookieAdapter(
                EncryptedFileStore(secure_dir / f"{profile.key}.cookie", protector),
                profile.key,
            )
            legacy_value = (legacy_cookies or {}).get(profile.key, "")
            legacy_cookie = legacy_value.strip() if isinstance(legacy_value, str) else ""
            if legacy_cookie and not cookie_store.has_credential:
                cookie_store.save_cookie(profile.key, legacy_cookie)
            login_services[profile.key] = CookieLoginService(
                profile,
                PyWebView2Browser(secure_dir / "webview" / profile.key),
                cookie_store,
                runtime_cookie_callback,
            )
    except Exception as exc:
        return CommercialRuntime(None, {}, f"商业授权配置无效：{exc}")
    return CommercialRuntime(license_service, login_services)
