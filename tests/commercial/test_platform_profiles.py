import inspect

from app.commercial.login import PLATFORM_PROFILE_BY_KEY, PLATFORM_PROFILES
from app.ui.views.settings_view import SettingsPage

FORMER_COOKIE_KEYS = {
    "douyin",
    "tiktok",
    "huya",
    "douyu",
    "yy",
    "bilibili",
    "xhs",
    "bigo",
    "blued",
    "soop",
    "netease",
    "qiandurebo",
    "pandalive",
    "maoerfm",
    "winktv",
    "flextv",
    "look",
    "popkontv",
    "twitcasting",
    "baidu",
    "weibo",
    "kugou",
    "twitch",
    "liveme",
    "huajiao",
    "liuxing",
    "showroom",
    "acfun",
    "changliao",
    "yinbo",
    "inke",
    "zhihu",
    "chzzk",
    "haixiu",
    "vvxq",
    "17live",
    "lang",
    "piaopiao",
    "6room",
    "lehai",
    "catshow",
    "shopee",
    "youtube",
    "taobao",
    "jd",
}


def test_unified_login_inventory_contains_every_former_cookie_platform():
    expected = FORMER_COOKIE_KEYS | {"kuaishou"}

    assert len(PLATFORM_PROFILES) == 46
    assert set(PLATFORM_PROFILE_BY_KEY) == expected
    assert len(PLATFORM_PROFILE_BY_KEY) == len(PLATFORM_PROFILES)


def test_every_platform_profile_has_secure_login_and_validation_rules():
    for profile in PLATFORM_PROFILES:
        assert profile.login_url.startswith("https://")
        assert profile.display_name
        assert profile.cookie_domains
        assert profile.authentication_cookie_groups
        assert all(group for group in profile.authentication_cookie_groups)


def test_settings_page_no_longer_builds_cookie_settings_tab():
    load_source = inspect.getsource(SettingsPage.load)

    assert "create_cookies_settings_tab" not in load_source
    assert 'self._["cookies_settings"]' not in load_source
