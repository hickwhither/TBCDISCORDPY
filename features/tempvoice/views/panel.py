import discord
from discord import ui

from features.tempvoice import repository
from features.tempvoice.views.embed import _MISSING

from . import actions, modals

HANDLERS = {
    "rename": modals.rename,
    "status": modals.status,
    "limit": modals.limit,
    "lock": actions.lock,
    "hide": actions.hide,
    "invite": actions.invite,
    "kick": actions.kick,
    "transfer": actions.transfer,
    "delete": actions.delete,
}


class OwnerCheckView(ui.View):
    def __init__(self, channel_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.channel_id = channel_id

    async def owner_check(self, interaction: discord.Interaction) -> bool:
        row = await repository.get_tempvoice(self.channel_id)
        if not row:
            await interaction.response.send_message(
                "❌ Phòng này không còn tồn tại.", ephemeral=True
            )
            return False
        if interaction.user.id != row.owner_id:
            await interaction.response.send_message(
                "❌ Bạn không phải chủ phòng.", ephemeral=True
            )
            return False
        return True


class ControlPanelView(OwnerCheckView):
    def __init__(self, bot, channel_id: int) -> None:
        super().__init__(channel_id, timeout=None)
        self.bot = bot
        self.add_item(CommandSelect(channel_id))


class CommandSelect(ui.Select):
    OPTIONS = [
        ("rename", "Đổi tên", "📝"),
        ("status", "Đặt tên status", "📌"),
        ("limit", "Giới hạn người", "👥"),
        ("lock", "Khóa / Mở phòng", "🔒"),
        ("hide", "Ẩn / Hiện phòng", "🙈"),
        ("invite", "Mời người vào", "👋"),
        ("kick", "Đuổi người", "🚪"),
        ("transfer", "Chuyển chủ phòng", "🔄"),
        ("delete", "Xóa phòng", "❌"),
    ]

    def __init__(self, channel_id: int) -> None:
        self.channel_id = channel_id
        options = [
            discord.SelectOption(label=label, value=action, emoji=emoji)
            for action, label, emoji in self.OPTIONS
        ]
        super().__init__(
            custom_id="tv_menu",
            placeholder="Chọn lệnh cần thực hiện...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await self.view.owner_check(interaction):
            return
        await dispatch(interaction, self.channel_id, self.values[0], self.view)


async def dispatch(
    interaction: discord.Interaction,
    channel_id: int,
    action: str,
    panel_view=_MISSING,
) -> None:
    handler = HANDLERS.get(action)
    if handler:
        await handler(interaction, channel_id, panel_view)
