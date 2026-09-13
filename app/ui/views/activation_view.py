from __future__ import annotations

import flet as ft

from ...commercial.license import LicenseDecision, LicenseError, LicenseState
from ...utils.logger import logger
from ..base_page import PageBase


class ActivationPage(PageBase):
    def __init__(self, app):
        super().__init__(app)
        self.page_name = "activation"
        self.code_field = ft.TextField(
            hint_text="请输入激活码",
            autofocus=True,
            width=760,
            height=58,
            border_radius=12,
            text_size=16,
            content_padding=ft.Padding.symmetric(horizontal=18, vertical=14),
            on_submit=self.activate,
        )
        self.status_icon = ft.Icon(ft.Icons.INFO_OUTLINE, size=20)
        self.status = ft.Text("", size=14, expand=True)
        self.progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
        self.retry_button = ft.TextButton("重新校验", icon=ft.Icons.REFRESH, on_click=self.retry, visible=False)
        self.status_area = ft.Container(
            content=ft.Row(
                [self.progress, self.status_icon, self.status, self.retry_button],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=760,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=12,
        )
        self.activate_button = ft.Button(
            "激活并进入",
            icon=ft.Icons.VERIFIED_USER,
            on_click=self.activate,
            width=760,
            height=54,
            color=ft.Colors.WHITE,
            bgcolor="#6D4AFF",
            elevation=0,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=13)),
        )
        self.deactivate_button = ft.Button(
            "在本机停用",
            icon=ft.Icons.LINK_OFF,
            on_click=self.deactivate,
            visible=False,
            width=760,
            height=48,
            elevation=0,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        )

    async def load(self):
        self.content_area.controls = [self._build()]
        self.content_area.update()
        await self.show_decision(self.app.license_decision)

    def _palette(self) -> dict[str, str]:
        dark = self.page.theme_mode == ft.ThemeMode.DARK
        if dark:
            return {
                "page": "#11121A",
                "strong": "#F7F7FC",
                "muted": "#AAAABD",
                "subtle": "#85859A",
                "border": "#3A3752",
                "divider": "#39364D",
                "field": "#171822",
                "plan": "#1D1E2A",
            }
        return {
            "page": "#F8F8FF",
            "strong": "#111326",
            "muted": "#77798F",
            "subtle": "#8B8DA1",
            "border": "#D9D5ED",
            "divider": "#E2DEEF",
            "field": "#FFFFFF",
            "plan": "#FFFFFF",
        }

    def _build_plan_strip(self, palette: dict[str, str]) -> ft.Container:
        plans = [("月卡", "30 天"), ("季卡", "90 天"), ("年卡", "365 天"), ("终身会员", "199 元")]
        cells = []
        for index, (name, detail) in enumerate(plans):
            cells.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(name, size=17, weight=ft.FontWeight.W_600, color=palette["strong"]),
                            ft.Text(detail, size=14, color=palette["muted"]),
                        ],
                        spacing=3,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    height=78,
                    alignment=ft.Alignment.CENTER,
                    border=(
                        ft.Border(right=ft.BorderSide(1, palette["divider"]))
                        if index < len(plans) - 1
                        else None
                    ),
                    col={"xs": 6, "sm": 3},
                )
            )
        return ft.Container(
            content=ft.ResponsiveRow(cells, spacing=0, run_spacing=0),
            width=760,
            bgcolor=palette["plan"],
            border=ft.Border.all(1, palette["border"]),
            border_radius=40,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

    def _build(self):
        palette = self._palette()
        self.code_field.bgcolor = palette["field"]
        self.code_field.border_color = palette["border"]
        self.code_field.focused_border_color = "#6D4AFF"
        self.code_field.hint_style = ft.TextStyle(color=palette["subtle"])

        content = ft.Container(
            width=820,
            padding=ft.Padding.only(left=24, right=24, top=28, bottom=28),
            content=ft.Column(
                [
                    ft.Image(src="images/logo-mark.svg", width=82, height=82, fit=ft.BoxFit.CONTAIN),
                    ft.Text("激活录播达人", size=36, weight=ft.FontWeight.BOLD, color=palette["strong"]),
                    ft.Text("输入激活码，开启稳定录制", size=18, color=palette["muted"]),
                    ft.Container(height=8),
                    self._build_plan_strip(palette),
                    ft.Text(
                        "激活码自动识别会员档位，默认绑定 1 台设备",
                        size=13,
                        color=palette["subtle"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=2),
                    ft.Column(
                        [
                            ft.Text("激活码", size=15, weight=ft.FontWeight.W_600, color=palette["strong"]),
                            self.code_field,
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    self.status_area,
                    self.activate_button,
                    self.deactivate_button,
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.LOCK_OUTLINE, size=15, color=palette["subtle"]),
                            ft.Text(
                                "激活信息仅用于授权校验，直播账号凭据不会上传到授权服务器。",
                                size=12,
                                color=palette["subtle"],
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=5,
                        wrap=True,
                    ),
                ],
                spacing=13,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        return ft.Container(
            content=content,
            expand=True,
            bgcolor=palette["page"],
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=10, bottom=10),
        )

    async def activate(self, _=None):
        if not self.app.license_service:
            self.status.value = self.app.commercial_runtime.configuration_error or "授权服务不可用"
            self._style_status(False)
            self.content_area.update()
            return
        await self._set_loading(True, "正在激活…")
        try:
            decision = await self.app.license_service.activate(self.code_field.value or "")
        except LicenseError as exc:
            logger.warning(f"License activation rejected: {exc}")
            decision = LicenseDecision(False, LicenseState.NETWORK_REQUIRED, f"激活失败：{exc}")
        except Exception as exc:
            logger.exception(f"Unexpected license activation error: {exc}")
            decision = LicenseDecision(False, LicenseState.INVALID, f"激活失败：{exc}")
        await self._set_loading(False)
        await self.app.apply_license_decision(decision, navigate=True)

    async def retry(self, _=None):
        await self._set_loading(True, "正在校验…")
        decision = await self.app.check_license()
        await self._set_loading(False)
        await self.app.apply_license_decision(decision, navigate=decision.allowed)

    async def deactivate(self, _=None):
        if self.app.license_service:
            await self._set_loading(True, "正在停用…")
            try:
                await self.app.license_service.deactivate()
                decision = LicenseDecision(False, LicenseState.MISSING, "本机授权已停用")
            except Exception:
                decision = LicenseDecision(False, LicenseState.NETWORK_REQUIRED, "停用失败，请联网后重试")
            await self._set_loading(False)
            await self.app.apply_license_decision(decision)

    def _style_status(self, allowed: bool):
        dark = self.page.theme_mode == ft.ThemeMode.DARK
        if allowed:
            color, background, icon = (
                ("#54D58B", "#173C2A", ft.Icons.CHECK_CIRCLE_OUTLINE)
                if dark
                else ("#178A4D", "#EAF8EF", ft.Icons.CHECK_CIRCLE_OUTLINE)
            )
        else:
            color, background, icon = (
                ("#FF7B83", "#3D2028", ft.Icons.ERROR_OUTLINE)
                if dark
                else ("#E33E46", "#FFF0F1", ft.Icons.ERROR_OUTLINE)
            )
        self.status.color = color
        self.status_icon.color = color
        self.status_icon.icon = icon
        self.status_area.bgcolor = background
        self.retry_button.icon_color = color
        self.retry_button.style = ft.ButtonStyle(color=color)

    async def show_decision(self, decision: LicenseDecision):
        self.status.value = decision.reason
        self._style_status(decision.allowed)
        self.code_field.visible = not decision.allowed
        self.activate_button.visible = not decision.allowed
        self.retry_button.visible = decision.state not in {LicenseState.MISSING, LicenseState.INVALID}
        self.deactivate_button.visible = decision.allowed
        try:
            self.content_area.update()
        except (AssertionError, RuntimeError):
            pass

    async def _set_loading(self, loading: bool, message: str | None = None):
        self.progress.visible = loading
        self.status_icon.visible = not loading
        self.code_field.disabled = loading
        self.activate_button.disabled = loading
        self.retry_button.disabled = loading
        self.deactivate_button.disabled = loading
        if message:
            self.status.value = message
            palette = self._palette()
            self.status.color = palette["muted"]
            self.status_area.bgcolor = palette["plan"]
        self.content_area.update()
