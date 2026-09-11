from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from http.cookies import Morsel, SimpleCookie

from .errors import LoginDisplayError
from .models import PlatformProfile


class CookieValidationError(LoginDisplayError):
    """Raised when captured cookies do not prove an authenticated session."""


@dataclass(frozen=True, slots=True)
class BrowserCookie:
    name: str
    value: str
    domain: str
    path: str = "/"
    http_only: bool = False
    secure: bool = False


def _clean_domain(domain: object) -> str:
    return str(domain or "").strip().lower().lstrip(".")


def _domain_allowed(domain: str, allowed_domains: tuple[str, ...]) -> bool:
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)


def _cookie_from_mapping(item: Mapping[str, object], fallback_name: str = "") -> BrowserCookie | None:
    name = str(item.get("name") or item.get("key") or fallback_name).strip()
    value = str(item.get("value") or "")
    if not name or not value:
        return None
    return BrowserCookie(
        name=name,
        value=value,
        domain=_clean_domain(item.get("domain")),
        path=str(item.get("path") or "/"),
        http_only=bool(item.get("httpOnly") or item.get("httponly")),
        secure=bool(item.get("secure")),
    )


def _cookies_from_simple_cookie(cookie: SimpleCookie) -> list[BrowserCookie]:
    result: list[BrowserCookie] = []
    for name, morsel in cookie.items():
        result.append(
            BrowserCookie(
                name=name,
                value=morsel.value,
                domain=_clean_domain(morsel["domain"]),
                path=morsel["path"] or "/",
                http_only=bool(morsel["httponly"]),
                secure=bool(morsel["secure"]),
            )
        )
    return result


def normalize_webview_cookies(raw_cookies: object) -> list[BrowserCookie]:
    """Normalize pywebview cookie results without using ``document.cookie``.

    pywebview documents ``Window.get_cookies`` as returning SimpleCookie data,
    while renderer/version combinations may expose a list of mappings or
    Morsels. Supporting those public shapes keeps the platform logic isolated.
    """

    if raw_cookies is None:
        return []
    if isinstance(raw_cookies, SimpleCookie):
        return _cookies_from_simple_cookie(raw_cookies)
    if isinstance(raw_cookies, Mapping):
        if "name" in raw_cookies or "key" in raw_cookies:
            cookie = _cookie_from_mapping(raw_cookies)
            return [cookie] if cookie else []
        result: list[BrowserCookie] = []
        for name, value in raw_cookies.items():
            if isinstance(value, Morsel):
                result.extend(_cookies_from_simple_cookie(SimpleCookie({name: value.value})))
            elif isinstance(value, Mapping):
                cookie = _cookie_from_mapping(value, fallback_name=str(name))
                if cookie:
                    result.append(cookie)
            elif value:
                result.append(BrowserCookie(str(name), str(value), ""))
        return result
    if isinstance(raw_cookies, Iterable) and not isinstance(raw_cookies, (str, bytes)):
        result: list[BrowserCookie] = []
        for item in raw_cookies:
            if isinstance(item, SimpleCookie):
                result.extend(_cookies_from_simple_cookie(item))
            elif isinstance(item, Morsel):
                cookie = SimpleCookie()
                cookie[item.key] = item.value
                cookie[item.key]["domain"] = item["domain"]
                cookie[item.key]["path"] = item["path"]
                cookie[item.key]["httponly"] = item["httponly"]
                cookie[item.key]["secure"] = item["secure"]
                result.extend(_cookies_from_simple_cookie(cookie))
            elif isinstance(item, Mapping):
                cookie = _cookie_from_mapping(item)
                if cookie:
                    result.append(cookie)
        return result
    raise CookieValidationError("浏览器返回了不支持的 Cookie 数据格式")


def filter_platform_cookies(cookies: Iterable[BrowserCookie], profile: PlatformProfile) -> list[BrowserCookie]:
    allowed_domains = tuple(_clean_domain(domain) for domain in profile.cookie_domains)
    filtered: list[BrowserCookie] = []
    for cookie in cookies:
        if not cookie.domain or not _domain_allowed(_clean_domain(cookie.domain), allowed_domains):
            continue
        if any(char in cookie.name or char in cookie.value for char in ("\r", "\n", ";")):
            continue
        filtered.append(cookie)
    return filtered


def build_cookie_header(cookies: Iterable[BrowserCookie], profile: PlatformProfile) -> str:
    filtered = filter_platform_cookies(cookies, profile)
    cookie_names = {cookie.name.casefold() for cookie in filtered}
    if not any(group <= cookie_names for group in profile.authentication_cookie_groups):
        raise CookieValidationError("未检测到有效登录状态，请在官方页面完成登录后重试")

    # A Cookie header cannot encode domain/path. Prefer the most specific
    # candidate when the browser store contains duplicate cookie names.
    selected: dict[str, BrowserCookie] = {}
    for cookie in filtered:
        previous = selected.get(cookie.name)
        rank = (len(_clean_domain(cookie.domain)), len(cookie.path or "/"))
        previous_rank = (
            (len(_clean_domain(previous.domain)), len(previous.path or "/")) if previous is not None else (-1, -1)
        )
        if rank >= previous_rank:
            selected[cookie.name] = cookie
    return "; ".join(f"{name}={cookie.value}" for name, cookie in sorted(selected.items()))
