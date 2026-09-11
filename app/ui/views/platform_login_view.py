import asyncio

import flet as ft

from ...commercial.login import CookieLoginService, LoginSnapshot, LoginState
from ..base_page import PageBase


class PlatformLoginPage(PageBase):
    """Commercial platform-login page; wiring is supplied by the app shell."""

    def __init__(self, app, login_service: CookieLoginService | None = None):
        super().__init__(app)
        self.page_name = "platform_login"
        self.login_service = login_service
        self.status_icon = ft.Icon(ft.Icons.LOGOUT, color=ft.Colors.GREY_500, size=34)
        self.status_title = ft.Text("尚未登录", size=18, weight=ft.FontWeight.W_600)
        self.status_detail = ft.Text("登录后可使用账号状态访问需要登录的直播间", color=ft.Colors.GREY_600)
        self.progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
        self.login_button = ft.Button("登录快手", icon=ft.Icons.LOGIN, on_click=self.on_login)
        self.logout_button = ft.TextButton("退出登录", icon=ft.Icons.LOGOUT, on_click=self.on_logout, visible=False)
        if login_service is not None:
            login_service.set_state_callback(self.on_state_change)

    async def load(self):
        self.content_area.controls = [self._build()]
        self.content_area.update()
        if self.login_service is None:
            await self.on_state_change(LoginSnapshot(LoginState.ERROR, "登录服务尚未接入"))
        else:
            await self.login_service.restore()

    def _build(self) -> ft.Control:
        return ft.Container(
            expand=True,
            padding=32,
            content=ft.Column(
                controls=[
                    ft.Text("平台登录", size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("使用平台官方页面登录，登录凭据仅加密保存在本机。", color=ft.Colors.GREY_600),
                    ft.Card(
                        content=ft.Container(
                            padding=24,
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                content=ft.Text("快", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                                width=46,
                                                height=46,
                                                alignment=ft.alignment.Alignment.CENTER,
                                                bgcolor="#FF5000",
                                                border_radius=12,
                                            ),
                                            ft.Column(
                                                [
                                                    ft.Text("快手", size=20, weight=ft.FontWeight.BOLD),
                                                    self.status_detail,
                                                ],
                                                spacing=4,
                                                expand=True,
                                            ),
                                            self.status_icon,
                                        ],
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    ft.Divider(),
                                    ft.Row(
                                        [self.progress, self.status_title],
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    ft.Row([self.login_button, self.logout_button], spacing=12),
                                    ft.Text(
                                        "登录窗口由 Microsoft Edge WebView2 打开。"
                                        "完成扫码或账号登录后，窗口会自动关闭。",
                                        size=12,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=16,
                            ),
                        )
                    ),
                ],
                spacing=18,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    async def on_login(self, _=None):
        if self.login_service is not None:
            await self.login_service.login()

    async def on_logout(self, _=None):
        if self.login_service is not None:
            await self.login_service.logout()

    async def on_state_change(self, snapshot: LoginSnapshot):
        loading = snapshot.state == LoginState.LOADING
        signed_in = snapshot.state == LoginState.SIGNED_IN
        self.progress.visible = loading
        self.login_button.disabled = loading
        self.login_button.content = "重新登录" if signed_in else "登录快手"
        self.logout_button.visible = signed_in
        self.logout_button.disabled = loading
        self.status_title.value = snapshot.message
        if signed_in:
            self.status_icon.name = ft.Icons.CHECK_CIRCLE
            self.status_icon.color = ft.Colors.GREEN_600
            self.status_detail.value = "已登录，可供录制任务在运行时使用"
        elif snapshot.state == LoginState.ERROR:
            self.status_icon.name = ft.Icons.ERROR_OUTLINE
            self.status_icon.color = ft.Colors.RED_500
            self.status_detail.value = "登录未完成"
        else:
            self.status_icon.name = ft.Icons.LOGOUT
            self.status_icon.color = ft.Colors.GREY_500
            self.status_detail.value = "登录后可使用账号状态访问需要登录的直播间"
        try:
            self.content_area.update()
        except (AssertionError, RuntimeError):
            await asyncio.sleep(0)
