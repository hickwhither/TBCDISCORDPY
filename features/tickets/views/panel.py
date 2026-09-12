import discord
from discord import ButtonStyle, ui

from core.utils import reply_ephemeral
from features.tickets import repository
from features.tickets.views.embed import build_embed
from features.tickets.views.permissions import is_staff, owner_overwrite


async def refresh_panel(channel: discord.TextChannel) -> None:
    row = await repository.get_by_channel(channel.id)
    await edit_panel(channel.guild, channel, row)


async def edit_panel(guild: discord.Guild, channel: discord.TextChannel, row) -> None:
    if not row or not row.panel_message_id:
        return
    embed = build_embed(
        guild,
        channel,
        owner_id=row.owner_id,
        status=row.status,
        created_at=row.created_at,
    )
    view = TicketPanelView(guild, channel.id, status=row.status)
    try:
        message = await channel.fetch_message(row.panel_message_id)
        await message.edit(embed=embed, view=view)
    except discord.NotFound, discord.HTTPException:
        pass


async def allowed(interaction: discord.Interaction, row) -> bool:
    if not row:
        await interaction.response.send_message(
            "❌ Ticket không còn tồn tại.", ephemeral=True
        )
        return False
    if interaction.user.id != row.owner_id and not is_staff(interaction.user):
        await interaction.response.send_message(
            "❌ Chỉ chủ ticket hoặc Staff mới được thực hiện hành động này.",
            ephemeral=True,
        )
        return False
    return True


class CloseButton(ui.Button):
    def __init__(self, channel_id: int, disabled: bool) -> None:
        super().__init__(
            label="Đóng Ticket",
            emoji="🔒",
            style=ButtonStyle.primary,
            custom_id="tk_close",
            disabled=disabled,
        )
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction) -> None:
        row = await repository.get_by_channel(self.channel_id)
        if not await allowed(interaction, row):
            return
        if row.status != "open":
            return await interaction.response.send_message(
                "ℹ️ Ticket này đã được đóng.", ephemeral=True
            )

        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ Ticket đã bị xóa.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        owner = interaction.guild.get_member(row.owner_id)
        if owner:
            await channel.set_permissions(
                owner,
                overwrite=owner_overwrite(send=False),
                reason="Ticket: đóng ticket",
            )
        await repository.set_status(self.channel_id, "closed")
        await refresh_panel(channel)
        await channel.send(
            f"🔒 **{interaction.user.mention} đã đóng ticket.**\n"
            "Kênh bị khóa chat nhưng chưa bị xóa. Staff có thể **🔓 Mở lại** hoặc **🗑 Xóa**."
        )
        await reply_ephemeral(interaction, "🔒 Đã đóng ticket. Chat đã bị khóa.")


class ReopenButton(ui.Button):
    def __init__(self, channel_id: int, disabled: bool) -> None:
        super().__init__(
            label="Mở lại",
            emoji="🔓",
            style=ButtonStyle.success,
            custom_id="tk_reopen",
            disabled=disabled,
        )
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction) -> None:
        row = await repository.get_by_channel(self.channel_id)
        if not await allowed(interaction, row):
            return
        if row.status != "closed":
            return await interaction.response.send_message(
                "ℹ️ Ticket này đang mở.", ephemeral=True
            )

        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ Ticket đã bị xóa.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        owner = interaction.guild.get_member(row.owner_id)
        if owner:
            await channel.set_permissions(
                owner,
                overwrite=owner_overwrite(send=True),
                reason="Ticket: mở lại ticket",
            )
        await repository.set_status(self.channel_id, "open")
        await refresh_panel(channel)
        await channel.send(f"🔓 **{interaction.user.mention} đã mở lại ticket.**")
        await reply_ephemeral(interaction, "🔓 Đã mở lại ticket.")


class DeleteButton(ui.Button):
    def __init__(self, channel_id: int) -> None:
        super().__init__(
            label="Xóa Ticket",
            emoji="🗑",
            style=ButtonStyle.danger,
            custom_id="tk_delete",
        )
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction) -> None:
        row = await repository.get_by_channel(self.channel_id)
        if not row:
            return await interaction.response.send_message(
                "❌ Ticket không còn tồn tại.", ephemeral=True
            )
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Chỉ **Staff/Admin** mới được xóa ticket.", ephemeral=True
            )
        await interaction.response.send_message(
            "🗑 Bạn chắc chắn muốn **xóa ticket này**? Hành động không thể hoàn tác.",
            view=ConfirmDeleteView(self.channel_id, interaction.user.id),
            ephemeral=True,
        )


class TicketPanelView(ui.View):
    def __init__(self, bot, channel_id: int, *, status: str = "open") -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.channel_id = channel_id
        self._status = status
        self.add_item(CloseButton(channel_id, disabled=status != "open"))
        self.add_item(ReopenButton(channel_id, disabled=status != "closed"))
        self.add_item(DeleteButton(channel_id))


class ConfirmDeleteView(ui.View):
    def __init__(self, channel_id: int, actor_id: int) -> None:
        super().__init__(timeout=60)
        self.channel_id = channel_id
        self.actor_id = actor_id

    @ui.button(label="Hủy", style=ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _) -> None:
        await interaction.response.edit_message(content="Đã hủy thao tác.", view=None)
        self.stop()

    @ui.button(
        label="Xác nhận xóa", style=ButtonStyle.danger, custom_id="tk_confirm_delete"
    )
    async def confirm(self, interaction: discord.Interaction, _) -> None:
        if interaction.user.id != self.actor_id:
            return await interaction.response.send_message(
                "❌ Không được phép.", ephemeral=True
            )
        await interaction.response.edit_message(
            content="🗑 Đang xóa ticket...", view=None
        )
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            text = "❌ Ticket đã bị xóa trước đó."
        else:
            try:
                await channel.delete(reason="Ticket: xóa ticket")
            except discord.Forbidden:
                text = "❌ Bot không đủ quyền xóa kênh (cần quyền Manage Channels)."
            except discord.NotFound, discord.HTTPException:
                text = None
            else:
                await repository.remove(self.channel_id)
                text = "🗑 Đã xóa ticket."
        if text:
            await reply_ephemeral(interaction, text)
        try:
            await interaction.delete_original_response()
        except discord.NotFound, discord.HTTPException:
            pass
        self.stop()
