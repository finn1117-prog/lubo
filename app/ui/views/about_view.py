import flet as ft

from ..base_page import PageBase
from ..components.dialogs.help_dialog import HelpDialog


class AboutPage(PageBase):
    def __init__(self, app):
        super().__init__(app)
        self.page_name = "about"
        self.about_config = {}
        self.app.language_manager.add_observer(self)
        self.load_language()
        self.page.on_keyboard_event = self.on_keyboard

    def load_language(self):
        self._ = self.app.language_manager.language.get("about_page", {})
        self.about_config = self.app.config_manager.load_about_config()

    async def load(self):
        self.content_area.controls.clear()
        mobile = self.app.is_mobile
        dark = self.page.theme_mode == ft.ThemeMode.DARK
        zh = self.app.language_code == "zh_CN"
        release = self.about_config["version_updates"][0]
        strong = ft.Colors.GREY_100 if dark else ft.Colors.GREY_900
        muted = ft.Colors.GREY_400 if dark else ft.Colors.GREY_600
        card_bg = ft.Colors.with_opacity(0.06, ft.Colors.WHITE) if dark else ft.Colors.WHITE
        border = ft.Border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.ON_SURFACE))

        def label(cn, en):
            return cn if zh else en

        def title(icon, text, color=ft.Colors.BLUE):
            return ft.Row(
                [
                    ft.Container(
                        ft.Icon(icon, size=19, color=color),
                        width=34,
                        height=34,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=ft.Colors.with_opacity(0.11, color),
                        border_radius=10,
                    ),
                    ft.Text(text, size=17, weight=ft.FontWeight.W_600, color=strong),
                ],
                spacing=10,
            )

        def card(content):
            return ft.Container(
                content,
                padding=20,
                bgcolor=card_bg,
                border=border,
                border_radius=16,
                shadow=None if dark else ft.BoxShadow(blur_radius=14, color="#100F172A", offset=ft.Offset(0, 4)),
            )

        hero = card(
            ft.ResponsiveRow(
                [
                    ft.Container(
                        ft.Row(
                            [
                                ft.Container(
                                    ft.Image(src="images/logo-mark.svg", width=66, height=66, fit=ft.BoxFit.CONTAIN),
                                    width=78,
                                    height=78,
                                    padding=6,
                                    bgcolor=ft.Colors.WHITE,
                                    border_radius=18,
                                    shadow=ft.BoxShadow(blur_radius=16, color="#332E6BE6", offset=ft.Offset(0, 5)),
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            label("录播达人", "LuboDaren"),
                                            size=27 if not mobile else 23,
                                            weight=ft.FontWeight.BOLD,
                                            color=strong,
                                        ),
                                        ft.Text(
                                            label("多平台直播录制，让精彩不再错过", "Multi-platform live recording"),
                                            size=14,
                                            color=muted,
                                        ),
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    f"{label('版本', 'Version')}：{release['version']}",
                                                    size=12,
                                                    color=muted,
                                                ),
                                                ft.Text("|", size=12, color=ft.Colors.GREY_400),
                                                ft.Text(
                                                    f"{label('发布日期', 'Released')}：{release['release_date']}",
                                                    size=12,
                                                    color=muted,
                                                ),
                                                ft.TextButton(
                                                    label("官方网站", "Official site"), on_click=self.open_official_site
                                                ),
                                            ],
                                            spacing=7,
                                            wrap=True,
                                        ),
                                    ],
                                    spacing=3,
                                    expand=True,
                                ),
                            ],
                            spacing=18,
                        ),
                        col={"xs": 12, "md": 8},
                    ),
                    ft.Container(
                        ft.Column(
                            [
                                ft.Icon(ft.Icons.VIDEO_CAMERA_FRONT, size=28, color=ft.Colors.PRIMARY),
                                ft.Text(
                                    label("记录每一个精彩瞬间！", "Capture every great moment!"),
                                    size=15,
                                    italic=True,
                                    color=ft.Colors.PRIMARY,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        col={"xs": 12, "md": 4},
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=18,
                run_spacing=16,
            )
        )
        hero.bgcolor = ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY) if dark else "#F5F7FF"

        intro_text = self.about_config["introduction"].get(self.app.language_code, "")
        intro = card(
            ft.Column(
                [
                    title(ft.Icons.DESCRIPTION_OUTLINED, label("软件简介", "Introduction")),
                    ft.Text(intro_text, size=14, color=muted),
                ],
                spacing=12,
            )
        )

        specs = [
            (
                ft.Icons.VIDEO_LIBRARY_OUTLINED,
                "多平台支持",
                "主流直播平台全覆盖",
                "Multi-platform",
                "Popular platforms covered",
                ft.Colors.BLUE,
            ),
            (
                ft.Icons.VIDEO_CAMERA_FRONT_OUTLINED,
                "自动监控录制",
                "开播自动录制",
                "Auto recording",
                "Records when streams start",
                ft.Colors.INDIGO,
            ),
            (
                ft.Icons.SETTINGS_OUTLINED,
                "自定义参数",
                "灵活设置，满足需求",
                "Custom options",
                "Flexible recording settings",
                ft.Colors.CYAN,
            ),
            (ft.Icons.SYNC, "自动转码", "多格式输出", "Auto transcode", "Multiple output formats", ft.Colors.PURPLE),
            (
                ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,
                "状态提醒",
                "直播状态实时推送",
                "Status alerts",
                "Real-time live updates",
                ft.Colors.ORANGE,
            ),
        ]
        items = []
        for icon, cn, cn_tip, en, en_tip, color in specs:
            items.append(
                ft.Container(
                    ft.Column(
                        [
                            ft.Container(
                                ft.Icon(icon, size=25, color=color),
                                width=48,
                                height=48,
                                alignment=ft.Alignment.CENTER,
                                bgcolor=ft.Colors.with_opacity(0.10, color),
                                border_radius=24,
                            ),
                            ft.Text(
                                label(cn, en),
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color=strong,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(label(cn_tip, en_tip), size=11, color=muted, text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    col={"xs": 6, "sm": 4, "md": 2.4},
                    padding=4,
                )
            )
        features = card(
            ft.Column(
                [
                    title(ft.Icons.STARS_OUTLINED, label("功能亮点", "Highlights")),
                    ft.ResponsiveRow(items, spacing=8, run_spacing=16, alignment=ft.MainAxisAlignment.CENTER),
                ],
                spacing=16,
            )
        )

        decision = self.app.license_decision
        plans = {
            "MONTHLY": label("月卡", "Monthly"),
            "QUARTERLY": label("季卡", "Quarterly"),
            "YEARLY": label("年卡", "Yearly"),
            "LIFETIME": label("终身", "Lifetime"),
        }
        plan = (
            plans.get(decision.claims.membership_plan, label("会员", "Member"))
            if decision.claims
            else label("会员", "Member")
        )
        license_name = (
            f"{plan}{'会员' if zh else ' member'}" if decision.allowed else label("免费版", "Free edition")
        )
        status_color = ft.Colors.GREEN if decision.allowed else ft.Colors.ORANGE
        license_description = (
            label("当前设备已激活", "This device is activated")
            if decision.allowed
            else label(
                "可录制 1 个直播间 · 不支持原画高清与 24 小时监控",
                "Record 1 live room · Original quality and 24/7 monitoring require membership",
            )
        )
        license_action = (
            label("管理授权", "Manage license")
            if decision.allowed
            else label("激活会员", "Activate membership")
        )

        version_card = card(
            ft.Column(
                [
                    title(ft.Icons.SYSTEM_UPDATE_ALT, label("当前版本", "Current version"), ft.Colors.TEAL),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(release["version"], size=24, weight=ft.FontWeight.BOLD, color=strong),
                                    ft.Text(label("已是最新版本", "Up to date"), size=12, color=ft.Colors.GREEN),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=24),
                        ]
                    ),
                    ft.Button(
                        label("检查更新", "Check for updates"),
                        icon=ft.Icons.REFRESH,
                        on_click=self._check_for_updates,
                        width=float("inf"),
                    ),
                ],
                spacing=13,
            )
        )
        license_card = card(
            ft.Column(
                [
                    title(
                        ft.Icons.VERIFIED_USER_OUTLINED,
                        label("会员与授权", "Membership and license"),
                        ft.Colors.AMBER,
                    ),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(license_name, size=19, weight=ft.FontWeight.BOLD, color=status_color),
                                    ft.Text(license_description, size=12, color=muted),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE if decision.allowed else ft.Icons.INFO_OUTLINE,
                                color=status_color,
                                size=24,
                            ),
                        ]
                    ),
                    ft.Button(
                        license_action,
                        icon=ft.Icons.PERSON_OUTLINE if decision.allowed else ft.Icons.VERIFIED_USER_OUTLINED,
                        on_click=self.open_activation,
                        width=float("inf"),
                        bgcolor=None if decision.allowed else "#6D4AFF",
                        color=None if decision.allowed else ft.Colors.WHITE,
                    ),
                ],
                spacing=13,
            )
        )

        footer = ft.ResponsiveRow(
            [
                ft.Container(
                    ft.Row(
                        [
                            ft.TextButton(
                                label("使用帮助", "Help"), icon=ft.Icons.HELP_OUTLINE, on_click=self.open_help
                            ),
                        ],
                        spacing=3,
                        wrap=True,
                    ),
                    col={"xs": 12, "md": 7},
                ),
                ft.Container(
                    ft.Text(
                        f"{label('基于', 'Based on')} StreamCap  ·  {self.about_config['open_source_license']}",
                        size=11,
                        color=muted,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                    alignment=ft.Alignment.CENTER_RIGHT,
                    col={"xs": 12, "md": 5},
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.content_area.controls.append(
            ft.Container(
                ft.Column(
                    [
                        hero,
                        intro,
                        features,
                        ft.ResponsiveRow(
                            [
                                ft.Container(version_card, col={"xs": 12, "md": 6}),
                                ft.Container(license_card, col={"xs": 12, "md": 6}),
                            ],
                            spacing=14,
                            run_spacing=14,
                        ),
                        footer,
                    ],
                    spacing=14,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.Padding.symmetric(horizontal=18 if not mobile else 10, vertical=14),
                expand=True,
            )
        )
        self.content_area.update()

    async def open_activation(self, _):
        await self.page.push_route("/activation")

    async def open_help(self, _):
        self.app.dialog_area.content = HelpDialog(self.app)
        self.app.dialog_area.content.open = True
        self.app.dialog_area.update()

    @staticmethod
    async def open_official_site(e):
        await e.page.launch_url("https://github.com/ihmily/StreamCap")

    async def on_keyboard(self, e: ft.KeyboardEvent):
        if e.alt and e.key == "H":
            await self.open_help(e)

    async def _check_for_updates(self, _):
        language = self.app.language_manager.language.get("update", {})
        await self.app.snack_bar.show_snack_bar(language.get("checking_update"))
        update_info = await self.app.update_checker.check_for_updates()
        if update_info.get("has_update", False):
            await self.app.update_checker.show_update_dialog(update_info)
        elif "error" in update_info:
            await self.app.snack_bar.show_snack_bar(
                f"{language.get('update_check_failed')}: {update_info.get('error', '')}"
            )
        else:
            await self.app.snack_bar.show_snack_bar(language.get("no_update_available"))
