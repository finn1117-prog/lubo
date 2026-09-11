from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class PlatformProfile:
    """Declarative rules for one platform's official login page and cookies."""

    key: str
    display_name: str
    login_url: str
    cookie_domains: tuple[str, ...]
    authentication_cookie_groups: tuple[frozenset[str], ...]

    def __post_init__(self) -> None:
        parsed = urlsplit(self.login_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Platform login URL must be an absolute HTTPS URL")
        if not self.key or not self.cookie_domains or not self.authentication_cookie_groups:
            raise ValueError("Platform profile is incomplete")


KUAISHOU_PROFILE = PlatformProfile(
    key="kuaishou",
    display_name="快手",
    login_url="https://live.kuaishou.com/",
    cookie_domains=("kuaishou.com",),
    # Anonymous visitors also receive device cookies. These markers are only
    # issued as part of an authenticated Kuaishou session.
    authentication_cookie_groups=(
        frozenset({"userid", "kuaishou.live.web_st"}),
        frozenset({"userid", "passtoken"}),
    ),
)
