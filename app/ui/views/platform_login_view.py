from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

import flet as ft

from ...commercial.login import CookieLoginService, LoginSnapshot, LoginState
from ..base_page import PageBase


class PlatformLoginPage(PageBase):
    """Single credential entry point for every former Cookie Settings key."""

    def __init__(self, app, login_services: Mapping[str, CookieLoginService] | None = None):
        super().__init__(app)
        self.page_name = "platform_login"
        self.login_services = dict(login_services or {})
        self.platform_controls: dict[str, dict[str, ft.Control]] = {}
        self.platform_list = ft.ListView(expand=True, spacing=10, padding=ft.Padding.only(bottom=24))
        self.search = ft.TextField(
            hint_text="搜索平台",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._filter_platforms,
            width=360,
            height=46,
        )
        self._active_login: str | None = None
        for key, service in self.login_services.items():
            service.set_state_callback(self._state_callback(key))

    def _state_callback(self, platform_key: str):
        async def callback(snapshot: LoginSnapshot) -> None:
            await self.on_state_change(platform_key, snapshot)

        return callback

    async def load(self):
        self.platform_controls.clear()
        self.platform_list.controls = [
            self._build_platform_card(key, service) for key, service in self.login_services.items()
        ]
        self.content_area.controls = [
            ft.Container(
                expand=True,
                padding=32,
                content=ft.Column(
                    [
                        ft.Text("平台登录", size=28, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"统一管理 {len(self.login_services)} 个平台的本地登录凭据。"
                            "凭据经系统加密保存，页面不会显示 Cookie 明文。",
                            color=ft.Colors.GREY_600,
                        ),
                        self.search,
                        ft.Divider(height=1),
                        self.platform_list,
                    ],
                    spacing=16,
                    expand=True,
                ),
            )
        ]
        self.content_area.update()
        for key, service in self.login_services.items():
            self._apply_snapshot(key, service.snapshot)
        self._safe_update()

    def _build_platform_card(self, key: str, service: CookieLoginService) -> ft.Control:
        credential = ft.Text("未保存", color=ft.Colors.GREY_600)
        status = ft.Text("未登录", weight=ft.FontWeight.W_600)
        verified = ft.Text("-", color=ft.Colors.GREY_600)
        progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
        login_button = ft.Button(
            "登录",
            icon=ft.Icons.LOGIN,
            data=key,
            on_click=self.on_login,
            width=104,
            height=36,
        )
        logout_button = ft.TextButton(
            "退出",
            icon=ft.Icons.LOGOUT,
            data=key,
            on_click=self.on_logout,
            visible=False,
            width=104,
            height=32,
        )
        hint = "优先进入二维码登录" if service.profile.prefer_qr else "进入官方登录页面"
        card = ft.Card(
            content=ft.Container(
                padding=ft.Padding.symmetric(horizontal=20, vertical=16),
                content=ft.Row(
                    [
                        ft.Container(
                            width=40,
                            height=40,
                            border_radius=12,
                            bgcolor=ft.Colors.BLUE_600,
                            alignment=ft.alignment.Alignment.CENTER,
                            content=ft.Text(
                                service.profile.display_name[:1],
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(service.profile.display_name, size=17, weight=ft.FontWeight.W_600),
                                ft.Text(hint, size=12, color=ft.Colors.GREY_500),
                            ],
                            width=130,
                            spacing=3,
                        ),
                        ft.Column(
                            [ft.Text("本地凭证", size=11, color=ft.Colors.GREY_500), credential],
                            width=90,
                        ),
                        ft.Column(
                            [
                                ft.Text("状态", size=11, color=ft.Colors.GREY_500),
                                ft.Row([progress, status]),
                            ],
                            width=115,
                        ),
                        ft.Column(
                            [ft.Text("最近验证", size=11, color=ft.Colors.GREY_500), verified],
                            width=120,
                        ),
                        ft.Column([login_button, logout_button], spacing=0, width=104),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
            )
        )
        self.platform_controls[key] = {
            "card": card,
            "credential": credential,
            "status": status,
            "verified": verified,
            "progress": progress,
            "login": login_button,
            "logout": logout_button,
        }
        return card

    def on_login(self, event):
        key = str(event.control.data)
        if self._active_login is None and key in self.login_services:
            self.page.run_task(self._run_login, key)

    async def _run_login(self, key: str):
        self._active_login = key
        self._refresh_action_availability()
        try:
            await self.login_services[key].login()
        finally:
            self._active_login = None
            self._refresh_action_availability()

    def on_logout(self, event):
        key = str(event.control.data)
        if self._active_login is None and key in self.login_services:
            self.page.run_task(self._run_logout, key)

    async def _run_logout(self, key: str):
        self._active_login = key
        self._refresh_action_availability()
        try:
            await self.login_services[key].logout()
        finally:
            self._active_login = None
            self._refresh_action_availability()

    async def on_state_change(self, platform_key: str, snapshot: LoginSnapshot):
        self._apply_snapshot(platform_key, snapshot)
        self._safe_update()

    def _apply_snapshot(self, platform_key: str, snapshot: LoginSnapshot) -> None:
        controls = self.platform_controls.get(platform_key)
        if not controls:
            return
        loading = snapshot.state == LoginState.LOADING
        signed_in = snapshot.state == LoginState.SIGNED_IN
        invalid = snapshot.state == LoginState.INVALID
        controls["progress"].visible = loading
        controls["credential"].value = "已安全保存" if snapshot.has_credential else "未保存"
        controls["credential"].color = ft.Colors.GREEN_700 if snapshot.has_credential else ft.Colors.GREY_600
        if signed_in:
            controls["status"].value = "有效"
        elif loading:
            controls["status"].value = "验证中"
        elif invalid:
            controls["status"].value = "已失效"
        elif snapshot.state == LoginState.ERROR:
            controls["status"].value = "登录失败"
        else:
            controls["status"].value = "未登录"
        controls["status"].color = (
            ft.Colors.GREEN_700
            if signed_in
            else ft.Colors.RED_600
            if snapshot.state in {LoginState.INVALID, LoginState.ERROR}
            else None
        )
        controls["verified"].value = self._format_time(snapshot.verified_at)
        controls["login"].content = "重新登录" if snapshot.has_credential else "登录"
        controls["logout"].visible = snapshot.has_credential
        self._refresh_action_availability()

    def _refresh_action_availability(self) -> None:
        for key, controls in self.platform_controls.items():
            controls["login"].disabled = self._active_login is not None
            controls["logout"].disabled = self._active_login is not None
            controls["progress"].visible = key == self._active_login
        self._safe_update()

    def _filter_platforms(self, event) -> None:
        query = str(event.data or "").strip().casefold()
        for key, service in self.login_services.items():
            card = self.platform_controls.get(key, {}).get("card")
            if card:
                card.visible = not query or query in key.casefold() or query in service.profile.display_name.casefold()
        self._safe_update()

    @staticmethod
    def _format_time(value: str | None) -> str:
        if not value:
            return "-"
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return "-"

    def _safe_update(self) -> None:
        try:
            self.content_area.update()
        except (AssertionError, RuntimeError):
            pass
