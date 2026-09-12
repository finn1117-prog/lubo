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
            label="激活码",
            hint_text="请输入购买后获得的激活码",
            autofocus=True,
            width=420,
            height=52,
            on_submit=self.activate,
        )
        self.status = ft.Text("", color=ft.Colors.GREY_600)
        self.progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
        self.activate_button = ft.Button("激活并进入", icon=ft.Icons.VERIFIED_USER, on_click=self.activate)
        self.retry_button = ft.TextButton("重新校验", icon=ft.Icons.REFRESH, on_click=self.retry, visible=False)
        self.deactivate_button = ft.TextButton("在本机停用", on_click=self.deactivate, visible=False)

    async def load(self):
        self.content_area.controls = [self._build()]
        self.content_area.update()
        await self.show_decision(self.app.license_decision)

    def _build(self):
        return ft.Container(
            expand=True,
            alignment=ft.alignment.Alignment.CENTER,
            padding=32,
            content=ft.Container(
                width=560,
                padding=32,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=18,
                content=ft.Column(
                    [
                        ft.Image(src="images/logo-mark.svg", width=64, height=64),
                        ft.Text("激活录播达人", size=28, weight=ft.FontWeight.BOLD),
                        ft.Text("终身会员 · 199 元 · 默认绑定 1 台设备", color=ft.Colors.GREY_600),
                        ft.Divider(height=24),
                        self.code_field,
                        ft.Row([self.progress, self.status], spacing=10),
                        ft.Row([self.activate_button, self.retry_button, self.deactivate_button], spacing=8),
                        ft.Text(
                            "激活信息仅用于授权校验；直播账号凭据不会上传到授权服务器。",
                            size=12,
                            color=ft.Colors.GREY_500,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
            ),
        )

    async def activate(self, _=None):
        if not self.app.license_service:
            self.status.value = self.app.commercial_runtime.configuration_error or "授权服务不可用"
            self.status.color = ft.Colors.RED_600
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

    async def show_decision(self, decision: LicenseDecision):
        self.status.value = decision.reason
        self.status.color = ft.Colors.GREEN_600 if decision.allowed else ft.Colors.RED_600
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
        self.code_field.disabled = loading
        self.activate_button.disabled = loading
        self.retry_button.disabled = loading
        self.deactivate_button.disabled = loading
        if message:
            self.status.value = message
            self.status.color = ft.Colors.GREY_600
        self.content_area.update()
