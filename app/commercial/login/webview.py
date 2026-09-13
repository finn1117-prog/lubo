from __future__ import annotations

import multiprocessing
import os
import queue
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

from .cookies import (
    BrowserCookie,
    CookieValidationError,
    build_cookie_header,
    filter_platform_cookies,
    normalize_webview_cookies,
)
from .errors import LoginDisplayError
from .models import PlatformProfile


class BrowserLoginError(LoginDisplayError):
    pass


_OPEN_LOGIN_SCRIPT = """
(() => {
  const visible = (node) => node && node.getClientRects().length > 0;
  const nodes = () => Array.from(document.querySelectorAll('button,a,[role="button"],[role="tab"]'));
  const clickLabel = (labels) => {
    const candidate = nodes().find((node) => {
      const text = (node.innerText || node.textContent || '').trim();
      return visible(node) && labels.some((label) => text === label || text.includes(label));
    });
    if (candidate) candidate.click();
    return Boolean(candidate);
  };
  const opened = clickLabel(['登录', '登入', 'Log in', 'Login', 'Sign in']);
  setTimeout(() => clickLabel(['扫码登录', '二维码登录', '二维码', 'QR code', 'QR Code']), 700);
  return opened;
})()
"""


_FIT_LOGIN_VIEWPORT_SCRIPT = """
(() => {
  const fitLoginViewport = () => {
    const body = document.body;
    const root = document.documentElement;
    if (!body || !root) return false;
    body.style.transformOrigin = 'top left';
    body.style.zoom = '0.85';
    root.style.overflowX = 'hidden';
    return true;
  };
  fitLoginViewport();
  window.setTimeout(fitLoginViewport, 600);
  window.setTimeout(fitLoginViewport, 1800);
  return true;
})()
"""


def _recommended_window_size() -> tuple[int, int]:
    """Use most of the working screen without forcing a maximized login window."""
    screen_width, screen_height = 1360, 900
    if sys.platform == "win32":
        try:
            import ctypes

            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        except (AttributeError, OSError):
            pass
    return max(960, min(1280, screen_width - 80)), max(640, min(820, screen_height - 100))


def _wait_for_process_result(process, result_queue, timeout_seconds: float):
    """Drain IPC while the child is alive so a large Cookie payload cannot deadlock on exit."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BrowserLoginError("登录窗口响应超时，请重试")
        try:
            return result_queue.get(timeout=min(0.25, remaining))
        except queue.Empty:
            if not process.is_alive():
                raise BrowserLoginError("登录窗口异常退出，未获取到登录状态")


def _webview_process(profile: PlatformProfile, result_queue, storage_path: str, timeout_seconds: float) -> None:
    try:
        import webview
    except ImportError:
        result_queue.put(("error", "未安装网页登录组件 pywebview"))
        return

    window_width, window_height = _recommended_window_size()
    window = webview.create_window(
        f"登录{profile.display_name}（官方页面）",
        profile.login_url,
        width=window_width,
        height=window_height,
        min_size=(min(900, window_width), min(620, window_height)),
        confirm_close=True,
    )
    closed = threading.Event()
    delivered = threading.Event()

    def on_closed() -> None:
        closed.set()

    window.events.closed += on_closed

    def capture_when_authenticated() -> None:
        deadline = time.monotonic() + timeout_seconds
        login_open_attempted = False
        viewport_fitted_at = 0.0
        while not closed.is_set() and time.monotonic() < deadline:
            now = time.monotonic()
            if now - viewport_fitted_at >= 3.0:
                try:
                    window.evaluate_js(_FIT_LOGIN_VIEWPORT_SCRIPT)
                    viewport_fitted_at = now
                except Exception:
                    pass
            try:
                cookies = filter_platform_cookies(normalize_webview_cookies(window.get_cookies()), profile)
                build_cookie_header(cookies, profile)
            except CookieValidationError:
                if profile.auto_open_login and not login_open_attempted:
                    try:
                        window.evaluate_js(_OPEN_LOGIN_SCRIPT)
                        login_open_attempted = True
                    except Exception:
                        pass
                time.sleep(1.0)
                continue
            except Exception:
                time.sleep(1.0)
                continue
            result_queue.put(("cookies", [asdict(cookie) for cookie in cookies]))
            delivered.set()
            window.destroy()
            return
        if closed.is_set():
            return
        result_queue.put(("error", "登录等待超时，请重新打开登录页"))
        delivered.set()
        window.destroy()

    try:
        webview.start(
            capture_when_authenticated,
            gui="edgechromium",
            # Do not leave a second persistent browser cookie store behind.
            # The validated header is persisted only through EncryptedFileStore.
            private_mode=True,
            storage_path=storage_path,
        )
        if not delivered.is_set():
            result_queue.put(("error", "登录窗口已关闭，未获取到登录状态"))
    except Exception:
        result_queue.put(("error", "无法启动 WebView2，请确认已安装 Microsoft Edge WebView2 Runtime"))


class PyWebView2Browser:
    """Capture HttpOnly cookies through pywebview's native cookie API."""

    def __init__(self, storage_path: str | os.PathLike[str], timeout_seconds: float = 300):
        self.storage_path = str(Path(storage_path))
        self.timeout_seconds = timeout_seconds

    def capture(self, profile: PlatformProfile) -> list[BrowserCookie]:
        if sys.platform != "win32":
            raise BrowserLoginError("当前登录窗口仅支持 Windows 10/11")
        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue(maxsize=2)
        process = context.Process(
            target=_webview_process,
            args=(profile, result_queue, self.storage_path, self.timeout_seconds),
            name=f"{profile.key}-login-webview",
        )
        process.start()
        try:
            kind, payload = _wait_for_process_result(process, result_queue, self.timeout_seconds + 15)
            process.join(5)
            if process.is_alive():
                process.terminate()
                process.join(5)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(5)
            result_queue.close()
        if kind != "cookies":
            raise BrowserLoginError(str(payload))
        return [BrowserCookie(**item) for item in payload]
