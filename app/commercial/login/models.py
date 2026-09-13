from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class PlatformProfile:
    """Login and Cookie rules for one existing StreamCap platform key."""

    key: str
    display_name: str
    login_url: str
    cookie_domains: tuple[str, ...]
    authentication_cookie_groups: tuple[frozenset[str], ...]
    prefer_qr: bool = False
    auto_open_login: bool = False
    authentication_probe_script: str | None = None

    def __post_init__(self) -> None:
        parsed = urlsplit(self.login_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Platform login URL must be an absolute HTTPS URL")
        if not self.key or not self.cookie_domains or not self.authentication_cookie_groups:
            raise ValueError("Platform profile is incomplete")


def _p(
    key: str,
    name: str,
    url: str,
    domains: tuple[str, ...],
    *cookie_groups: tuple[str, ...],
    qr: bool = False,
    auto: bool = False,
    probe: str | None = None,
) -> PlatformProfile:
    return PlatformProfile(
        key=key,
        display_name=name,
        login_url=url,
        cookie_domains=domains,
        authentication_cookie_groups=tuple(frozenset(value.casefold() for value in group) for group in cookie_groups),
        prefer_qr=qr,
        auto_open_login=auto,
        authentication_probe_script=probe,
    )


_XHS_AUTHENTICATION_PROBE = """
(() => {
  const unwrap = (value) => value && typeof value === 'object' && 'value' in value ? value.value : value;
  const state = unwrap(window.__INITIAL_STATE__);
  const userState = unwrap(state && state.user);
  const userInfo = unwrap(userState && (userState.userInfo || userState.user_info));
  if (!userInfo || typeof userInfo !== 'object') return false;
  return Boolean(userInfo.userId || userInfo.user_id || userInfo.redId || userInfo.red_id);
})()
"""


# Complete set of keys from the former Cookie Settings page, plus Kuaishou
# which was migrated in V1.1. Recording consumes these exact key names.
PLATFORM_PROFILES: tuple[PlatformProfile, ...] = (
    _p(
        "kuaishou",
        "快手",
        "https://live.kuaishou.com/",
        ("kuaishou.com",),
        ("userid", "kuaishou.live.web_st"),
        ("userid", "passtoken"),
        qr=True,
        auto=True,
    ),
    _p(
        "douyin",
        "抖音",
        "https://www.douyin.com/",
        ("douyin.com",),
        ("sessionid",),
        ("sessionid_ss",),
        qr=True,
        auto=True,
    ),
    _p("tiktok", "TikTok", "https://www.tiktok.com/login", ("tiktok.com",), ("sessionid",)),
    _p("huya", "虎牙", "https://www.huya.com/", ("huya.com",), ("udb_uid",), ("yyuid",), qr=True, auto=True),
    _p("douyu", "斗鱼", "https://www.douyu.com/", ("douyu.com",), ("acf_uid", "acf_auth"), qr=True, auto=True),
    _p("yy", "YY", "https://www.yy.com/", ("yy.com",), ("yyuid",), ("udb_uid",), qr=True, auto=True),
    _p(
        "bilibili",
        "哔哩哔哩",
        "https://passport.bilibili.com/login",
        ("bilibili.com",),
        ("sessdata", "dedeuserid"),
        qr=True,
    ),
    _p(
        "xhs",
        "小红书",
        "https://www.xiaohongshu.com/explore",
        ("xiaohongshu.com", "xhslink.com"),
        ("web_session",),
        qr=True,
        auto=True,
        probe=_XHS_AUTHENTICATION_PROBE,
    ),
    _p("bigo", "Bigo", "https://www.bigo.tv/", ("bigo.tv",), ("bigo_userid",), ("access_token",), auto=True),
    _p("blued", "Blued", "https://app.blued.cn/", ("blued.cn",), ("access_token",), ("blued_uid",), auto=True),
    _p(
        "soop",
        "SOOP",
        "https://www.sooplive.co.kr/",
        ("sooplive.co.kr", "sooplive.com"),
        ("pdboxuser", "pdboxticket"),
        auto=True,
    ),
    _p("netease", "网易CC", "https://cc.163.com/", ("163.com",), ("ntes_sess",), qr=True, auto=True),
    _p("qiandurebo", "千度热播", "https://qiandurebo.com/", ("qiandurebo.com",), ("phpsessid",), auto=True),
    _p(
        "pandalive",
        "PandaTV",
        "https://www.pandalive.co.kr/",
        ("pandalive.co.kr",),
        ("sesskey",),
        ("phpsessid",),
        auto=True,
    ),
    _p("maoerfm", "猫耳FM", "https://fm.missevan.com/", ("missevan.com",), ("token",), ("user_id",), auto=True),
    _p("winktv", "WinkTV", "https://www.winktv.co.kr/", ("winktv.co.kr",), ("phpsessid",), auto=True),
    _p("flextv", "FlexTV", "https://www.flextv.co.kr/", ("flextv.co.kr", "ttinglive.com"), ("phpsessid",), auto=True),
    _p("look", "Look直播", "https://look.163.com/", ("163.com",), ("ntes_sess",), qr=True, auto=True),
    _p("popkontv", "PopkonTV", "https://www.popkontv.com/", ("popkontv.com",), ("phpsessid",), auto=True),
    _p(
        "twitcasting",
        "TwitCasting",
        "https://twitcasting.tv/indexlogin.php",
        ("twitcasting.tv",),
        ("twitcasting-user",),
        ("tc_session",),
    ),
    _p("baidu", "百度直播", "https://passport.baidu.com/v2/?login", ("baidu.com",), ("bduss",), qr=True),
    _p("weibo", "微博", "https://weibo.com/login.php", ("weibo.com", "sina.com.cn"), ("sub",), qr=True),
    _p(
        "kugou",
        "酷狗直播",
        "https://fanxing.kugou.com/",
        ("kugou.com",),
        ("kg_mid", "userid"),
        ("token",),
        qr=True,
        auto=True,
    ),
    _p("twitch", "Twitch", "https://www.twitch.tv/login", ("twitch.tv",), ("auth-token",)),
    _p("liveme", "LiveMe", "https://www.liveme.com/", ("liveme.com",), ("access_token",), ("userid",), auto=True),
    _p("huajiao", "花椒", "https://www.huajiao.com/", ("huajiao.com",), ("token",), ("userid",), qr=True, auto=True),
    _p("liuxing", "流星直播", "https://www.7u66.com/", ("7u66.com",), ("phpsessid",), auto=True),
    _p(
        "showroom",
        "SHOWROOM",
        "https://www.showroom-live.com/user/login",
        ("showroom-live.com",),
        ("sr_id",),
        ("session",),
    ),
    _p("acfun", "AcFun", "https://www.acfun.cn/login/", ("acfun.cn",), ("auth_key",), ("acpassthrough",), qr=True),
    _p("changliao", "畅聊", "https://www.tlclw.com/", ("tlclw.com",), ("phpsessid",), auto=True),
    _p("yinbo", "音播", "https://www.ybw1666.com/", ("ybw1666.com",), ("phpsessid",), auto=True),
    _p("inke", "映客", "https://www.inke.cn/", ("inke.cn",), ("sessionid",), ("token",), qr=True, auto=True),
    _p("zhihu", "知乎", "https://www.zhihu.com/signin", ("zhihu.com",), ("z_c0",)),
    _p("chzzk", "CHZZK", "https://nid.naver.com/nidlogin.login", ("naver.com",), ("nid_ses",), ("nid_aut",)),
    _p("haixiu", "嗨秀", "https://www.haixiutv.com/", ("haixiutv.com",), ("phpsessid",), auto=True),
    _p("vvxq", "VV星球", "https://www.vvxqiu.com/", ("vvxqiu.com",), ("phpsessid",), ("token",), auto=True),
    _p("17live", "17Live", "https://17.live/", ("17.live",), ("access_token",), ("userid",), auto=True),
    _p("lang", "浪Live", "https://www.lang.live/", ("lang.live",), ("phpsessid",), ("token",), auto=True),
    _p(
        "piaopiao", "漂漂直播", "https://m.pp.weimipopo.com/", ("weimipopo.com",), ("phpsessid",), ("token",), auto=True
    ),
    _p("6room", "六间房", "https://v.6.cn/", ("6.cn",), ("userid",), ("sessionid",), qr=True, auto=True),
    _p("lehai", "乐嗨", "https://www.lehaitv.com/", ("lehaitv.com",), ("phpsessid",), ("token",), auto=True),
    _p("catshow", "花猫", "https://h.catshow168.com/", ("catshow168.com",), ("phpsessid",), ("token",), auto=True),
    _p("shopee", "Shopee", "https://shopee.com/", ("shopee.com", "shopee.cn"), ("spc_ec",), ("spc_u",), auto=True),
    _p(
        "youtube",
        "YouTube",
        "https://accounts.google.com/ServiceLogin?service=youtube",
        ("youtube.com", "google.com"),
        ("sapisid", "sid"),
        ("__secure-3papisid",),
    ),
    _p(
        "taobao",
        "淘宝直播",
        "https://login.taobao.com/",
        ("taobao.com", "tb.cn"),
        ("cookie2", "unb"),
        ("lgc",),
        qr=True,
    ),
    _p("jd", "京东直播", "https://passport.jd.com/new/login.aspx", ("jd.com", "3.cn"), ("pt_key", "pt_pin"), qr=True),
)

PLATFORM_PROFILE_BY_KEY = {profile.key: profile for profile in PLATFORM_PROFILES}
KUAISHOU_PROFILE = PLATFORM_PROFILE_BY_KEY["kuaishou"]
