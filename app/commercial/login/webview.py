from __future__ import annotations

import multiprocessing
import os
import queue
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

from .cookies import BrowserCookie, CookieValidationError, build_cookie_header, normalize_webview_cookies
from .errors import LoginDisplayError
from .models import PlatformProfile


class BrowserLoginError(LoginDisplayError):
    pass


def _webview_process(profile: PlatformProfile, result_queue, storage_path: str, timeout_seconds: float) -> None:
    try:
        import webview
    except ImportError:
        result_queue.put(("error", "未安装网页登录组件 pywebview"))
        return

    window = webview.create_window(
        f"登录{profile.display_name}（官方页面）",
        profile.login_url,
        width=1100,
        height=760,
        min_size=(760, 540),
        confirm_close=True,
    )
    closed = threading.Event()
    delivered = threading.Event()

    def on_closed() -> None:
        closed.set()

    window.events.closed += on_closed

    def capture_when_authenticated() -> None:
        deadline = time.monotonic() + timeout_seconds
        while not closed.is_set() and time.monotonic() < deadline:
            try:
                cookies = normalize_webview_cookies(window.get_cookies())
                build_cookie_header(cookies, profile)
            except CookieValidationError:
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
        process.join(self.timeout_seconds + 15)
        if process.is_alive():
            process.terminate()
            process.join(5)
            raise BrowserLoginError("登录窗口响应超时，请重试")
        try:
            kind, payload = result_queue.get(timeout=2)
        except queue.Empty:
            raise BrowserLoginError("登录窗口已关闭，未获取到登录状态")
        finally:
            result_queue.close()
        if kind != "cookies":
            raise BrowserLoginError(str(payload))
        return [BrowserCookie(**item) for item in payload]
