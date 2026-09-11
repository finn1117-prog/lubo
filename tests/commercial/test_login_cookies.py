from http.cookies import SimpleCookie

import pytest

from app.commercial.login import KUAISHOU_PROFILE, CookieValidationError, build_cookie_header
from app.commercial.login.cookies import BrowserCookie, filter_platform_cookies, normalize_webview_cookies


def test_normalizes_httponly_simple_cookie_from_webview_api():
    raw = SimpleCookie()
    raw["userId"] = "user-1"
    raw["userId"]["domain"] = ".live.kuaishou.com"
    raw["userId"]["httponly"] = True

    cookies = normalize_webview_cookies(raw)

    assert cookies == [BrowserCookie("userId", "user-1", "live.kuaishou.com", http_only=True)]


def test_domain_filter_rejects_suffix_confusion_and_unrelated_cookies():
    cookies = [
        BrowserCookie("userId", "good", ".kuaishou.com"),
        BrowserCookie("userId", "evil", "kuaishou.com.example.org"),
        BrowserCookie("foreign", "secret", "example.org"),
    ]

    assert filter_platform_cookies(cookies, KUAISHOU_PROFILE) == [cookies[0]]


def test_cookie_header_requires_authenticated_cookie_group():
    anonymous = [BrowserCookie("did", "device", ".kuaishou.com")]
    with pytest.raises(CookieValidationError, match="未检测到有效登录状态"):
        build_cookie_header(anonymous, KUAISHOU_PROFILE)


def test_cookie_header_is_stable_and_contains_only_allowed_domains():
    cookies = [
        BrowserCookie("kuaishou.live.web_st", "token", "live.kuaishou.com", http_only=True),
        BrowserCookie("userId", "42", ".kuaishou.com"),
        BrowserCookie("x", "outside", "example.org"),
    ]

    assert build_cookie_header(cookies, KUAISHOU_PROFILE) == "kuaishou.live.web_st=token; userId=42"


@pytest.mark.parametrize("value", ["bad;injected", "bad\r\nX-Test: yes"])
def test_cookie_header_drops_unsafe_values(value):
    cookies = [
        BrowserCookie("userId", "42", ".kuaishou.com"),
        BrowserCookie("kuaishou.live.web_st", value, ".kuaishou.com"),
    ]
    with pytest.raises(CookieValidationError):
        build_cookie_header(cookies, KUAISHOU_PROFILE)
