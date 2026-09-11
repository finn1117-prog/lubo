"""Platform web-login boundary for the commercial desktop application."""

from .cookies import BrowserCookie, CookieValidationError, build_cookie_header, normalize_webview_cookies
from .models import KUAISHOU_PROFILE, PlatformProfile
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
