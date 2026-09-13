import asyncio
import multiprocessing

from app.commercial.login import KUAISHOU_PROFILE, BrowserLoginResult, CookieLoginService, LoginState
from app.commercial.login.cookies import BrowserCookie
from app.commercial.login.service import EncryptedStoreCookieAdapter
from app.commercial.login.webview import BrowserLoginError, _wait_for_process_result
from app.commercial.security import EncryptedFileStore


def _put_large_cookie_payload(result_queue):
    result_queue.put(("cookies", [{"name": "large", "value": "x" * 1_000_000}]))


def test_webview_result_queue_is_drained_before_child_exit():
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_put_large_cookie_payload, args=(result_queue,))
    process.start()
    try:
        kind, payload = _wait_for_process_result(process, result_queue, 10)
        assert kind == "cookies"
        assert len(payload[0]["value"]) == 1_000_000
        process.join(5)
        assert not process.is_alive()
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5)
        result_queue.close()


class FakeBrowser:
    def __init__(self, cookies=None, error=None):
        self.cookies = cookies or []
        self.error = error

    def capture(self, _profile):
        if self.error:
            raise self.error
        return self.cookies


class FakeCookieStore:
    def __init__(self):
        self.values = {}

    def save_cookie(self, key, value, *, temporary=False):
        self.values[key] = value

    def load_cookie(self, key):
        return self.values.get(key)

    def delete_cookie(self, key):
        self.values.pop(key, None)


def authenticated_cookies():
    return [
        BrowserCookie("userId", "42", ".kuaishou.com"),
        BrowserCookie("kuaishou.live.web_st", "token", "live.kuaishou.com", http_only=True),
    ]


def test_login_encrypts_via_store_and_injects_runtime_memory():
    store = FakeCookieStore()
    runtime = {}

    async def scenario():
        service = CookieLoginService(
            KUAISHOU_PROFILE,
            FakeBrowser(authenticated_cookies()),
            store,
            lambda key, value: runtime.__setitem__(key, value),
        )
        return await service.login()

    snapshot = asyncio.run(scenario())

    assert snapshot.state == LoginState.SIGNED_IN
    assert runtime["kuaishou"] == store.values["kuaishou"]
    assert "token" not in snapshot.message


def test_guest_cookie_is_reported_as_temporary_instead_of_authenticated():
    store = FakeCookieStore()

    async def scenario():
        service = CookieLoginService(
            KUAISHOU_PROFILE,
            FakeBrowser(BrowserLoginResult(authenticated_cookies(), temporary=True)),
            store,
            lambda _key, _value: None,
        )
        return await service.login()

    snapshot = asyncio.run(scenario())

    assert snapshot.state == LoginState.TEMPORARY
    assert "2 小时" in snapshot.message


def test_logout_deletes_store_and_runtime_cookie():
    store = FakeCookieStore()
    store.values["kuaishou"] = "userId=42; kuaishou.live.web_st=token"
    runtime = {"kuaishou": store.values["kuaishou"]}

    async def scenario():
        service = CookieLoginService(
            KUAISHOU_PROFILE,
            FakeBrowser(),
            store,
            lambda key, value: runtime.__setitem__(key, value),
        )
        return await service.logout()

    snapshot = asyncio.run(scenario())

    assert snapshot.state == LoginState.SIGNED_OUT
    assert "kuaishou" not in store.values
    assert runtime["kuaishou"] is None


def test_arbitrary_adapter_exception_never_leaks_cookie_to_ui():
    secret = "userId=42; kuaishou.live.web_st=TOP_SECRET"

    async def scenario():
        service = CookieLoginService(
            KUAISHOU_PROFILE,
            FakeBrowser(error=RuntimeError(secret)),
            FakeCookieStore(),
            lambda _key, _value: None,
        )
        return await service.login()

    snapshot = asyncio.run(scenario())

    assert snapshot.state == LoginState.ERROR
    assert "TOP_SECRET" not in snapshot.message


def test_failed_relogin_keeps_local_credential_and_marks_it_invalid():
    store = FakeCookieStore()
    store.values["kuaishou"] = "userId=42; kuaishou.live.web_st=old"

    async def scenario():
        service = CookieLoginService(
            KUAISHOU_PROFILE,
            FakeBrowser(error=BrowserLoginError("browser failed")),
            store,
            lambda _key, _value: None,
        )
        await service.restore()
        return await service.login()

    snapshot = asyncio.run(scenario())

    assert snapshot.state == LoginState.INVALID
    assert snapshot.has_credential
    assert store.values["kuaishou"].endswith("old")


class FakeEncryptedFileStore:
    def __init__(self):
        self.payload = None

    def save(self, payload):
        self.payload = payload

    def load(self):
        return self.payload

    def delete(self):
        self.payload = None


def test_encrypted_file_store_adapter_round_trip():
    encrypted_store = FakeEncryptedFileStore()
    adapter = EncryptedStoreCookieAdapter(encrypted_store, "kuaishou")

    adapter.save_cookie("kuaishou", "userId=42")

    assert adapter.load_cookie("kuaishou") == "userId=42"
    assert adapter.verified_at is not None
    assert encrypted_store.payload["verified_at"] == adapter.verified_at
    adapter.delete_cookie("kuaishou")
    assert adapter.load_cookie("kuaishou") is None


def test_legacy_xiaohongshu_guest_cookie_is_removed():
    encrypted_store = FakeEncryptedFileStore()
    encrypted_store.payload = {
        "version": 1,
        "platform": "xhs",
        "cookie_header": "web_session=guest",
        "verified_at": "2026-09-13T00:00:00+00:00",
    }
    adapter = EncryptedStoreCookieAdapter(encrypted_store, "xhs")

    assert adapter.load_cookie("xhs") is None
    assert encrypted_store.payload is None


class XorProtector:
    def protect(self, plaintext):
        return bytes(value ^ 0xA5 for value in plaintext)

    def unprotect(self, ciphertext):
        return self.protect(ciphertext)


def test_adapter_writes_no_plaintext_cookie_to_encrypted_file(tmp_path):
    path = tmp_path / "kuaishou-login.dat"
    adapter = EncryptedStoreCookieAdapter(EncryptedFileStore(path, XorProtector()), "kuaishou")

    adapter.save_cookie("kuaishou", "userId=42; kuaishou.live.web_st=TOP_SECRET")

    assert "TOP_SECRET" not in path.read_text(encoding="utf-8")
    assert adapter.load_cookie("kuaishou") == "userId=42; kuaishou.live.web_st=TOP_SECRET"
