from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .license import Ed25519LicenseVerifier, InstallationIdentityStore, LicenseApiClient, LicenseService
from .login import KUAISHOU_PROFILE, CookieLoginService, EncryptedStoreCookieAdapter, PyWebView2Browser
from .security import DPAPIProtector, EncryptedFileStore


@dataclass(slots=True)
class CommercialRuntime:
    license_service: LicenseService | None
    login_service: CookieLoginService | None
    configuration_error: str | None = None


def create_commercial_runtime(
    data_dir: str | Path,
    runtime_cookie_callback,
    legacy_kuaishou_cookie: str = "",
) -> CommercialRuntime:
    """Build the commercial services without coupling them to StreamCap's core."""
    base_url = os.getenv("LICENSE_SERVER_URL", "").strip()
    public_key = os.getenv("LICENSE_PUBLIC_KEY", "").strip().replace("\\n", "\n")
    if not base_url or not public_key:
        return CommercialRuntime(
            license_service=None,
            login_service=None,
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
        cookie_store = EncryptedStoreCookieAdapter(
            EncryptedFileStore(secure_dir / "kuaishou.cookie", protector),
            KUAISHOU_PROFILE.key,
        )
        if legacy_kuaishou_cookie.strip():
            cookie_store.save_cookie(KUAISHOU_PROFILE.key, legacy_kuaishou_cookie.strip())
        login_service = CookieLoginService(
            KUAISHOU_PROFILE,
            PyWebView2Browser(secure_dir / "webview"),
            cookie_store,
            runtime_cookie_callback,
        )
    except Exception as exc:
        return CommercialRuntime(None, None, f"商业授权配置无效：{exc}")
    return CommercialRuntime(license_service, login_service)
