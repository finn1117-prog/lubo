"""Platform web-login boundary for the commercial desktop application."""

from .cookies import BrowserCookie, CookieValidationError, build_cookie_header, normalize_webview_cookies
from .models import KUAISHOU_PROFILE, PLATFORM_PROFILE_BY_KEY, PLATFORM_PROFILES, PlatformProfile
from .service import (
    CookieLoginService,
    EncryptedStoreCookieAdapter,
    LoginSnapshot,
    LoginState,
    SecureCookieStore,
)
from .webview import BrowserLoginError, PyWebView2Browser

__all__ = [
    "KUAISHOU_PROFILE",
    "PLATFORM_PROFILES",
    "PLATFORM_PROFILE_BY_KEY",
    "BrowserCookie",
    "BrowserLoginError",
    "CookieLoginService",
    "CookieValidationError",
    "EncryptedStoreCookieAdapter",
    "LoginSnapshot",
    "LoginState",
    "PlatformProfile",
    "PyWebView2Browser",
    "SecureCookieStore",
    "build_cookie_header",
    "normalize_webview_cookies",
]
