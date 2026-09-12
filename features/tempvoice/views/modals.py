import discord
from discord import ui

from core.utils import reply_ephemeral
from features.tempvoice import repository
from features.tempvoice.views.embed import _MISSING, edit_panel


class RenameModal(ui.Modal, title="Đổi tên phòng"):
    name = ui.TextInput(
        label="Tên phòng mới",
        min_length=1,
        max_length=100,
        placeholder="Nhập tên phòng...",
    )

    def __init__(self, channel_id: int, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ Phòng đã bị xóa.", ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        await channel.edit(name=self.name.value)
        await edit_panel(
            interaction.guild,
            channel,
            await repository.get_tempvoice(self.channel_id),
            self.panel_view,
        )
        await reply_ephemeral(
            interaction, f"✅ Đã đổi tên thành: **{self.name.value}**"
        )


class StatusModal(ui.Modal, title="Đổi trạng thái kênh"):
    status = ui.TextInput(
        label="Trạng thái kênh (bỏ trống để xóa)",
        max_length=500,
        required=False,
        placeholder="Đang nghiên cứu...",
    )

    def __init__(self, channel_id: int, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ Phòng đã bị xóa.", ephemeral=True
            )
        value = self.status.value.strip() or None
        await interaction.response.defer(ephemeral=True)
        try:
            await channel.edit(status=value)
        except discord.Forbidden, discord.HTTPException:
            text = (
                "❌ Không đặt được trạng thái kênh (server cần ít nhất 1 Level Boost "
                "và bot cần quyền Manage Channels)."
            )
        else:
            text = "✅ Đã cập nhật trạng thái kênh."
        await edit_panel(
            interaction.guild,
            channel,
            await repository.get_tempvoice(self.channel_id),
            self.panel_view,
        )
        await reply_ephemeral(interaction, text)


class LimitModal(ui.Modal, title="Giới hạn người vào phòng"):
    limit = ui.TextInput(
        label="Số người tối đa (1-99, 0 = không giới hạn)",
        min_length=1,
        max_length=2,
        placeholder="0",
    )

    def __init__(self, channel_id: int, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ Phòng đã bị xóa.", ephemeral=True
            )
        raw = self.limit.value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message(
                "❌ Vui lòng nhập số từ 0 đến 99.", ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        value = min(int(raw), 99)
        await channel.edit(user_limit=value)
        await edit_panel(
            interaction.guild,
            channel,
            await repository.get_tempvoice(self.channel_id),
            self.panel_view,
        )
        text = "Không giới hạn" if value == 0 else f"{value} người"
        await reply_ephemeral(interaction, f"✅ Đã đặt giới hạn: **{text}**.")


async def rename(interaction, channel_id, panel_view):
    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    await interaction.response.send_modal(RenameModal(channel_id, panel_view))


async def status(interaction, channel_id, panel_view):
    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    await interaction.response.send_modal(StatusModal(channel_id, panel_view))


async def limit(interaction, channel_id, panel_view):
    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    await interaction.response.send_modal(LimitModal(channel_id, panel_view))
