import discord
from discord import ButtonStyle, ui

from core.utils import resolve_member
from features.tickets import repository
from features.tickets.views.permissions import GUEST_PERMS


async def apply_member_change(
    interaction: discord.Interaction,
    channel_id: int,
    action: str,
    member_ids: list[str],
) -> str | None:
    """Thêm/xóa thành viên khỏi ticket. Trả về text xác nhận, None nếu đã báo lỗi."""
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return "❌ Ticket đã bị xóa."
    row = await repository.get_by_channel(channel_id)
    if not row:
        return "❌ Ticket không còn tồn tại."

    members = [
        m
        for raw in member_ids
        if raw.isdigit() and (m := guild.get_member(int(raw))) is not None
    ]
    members = [m for m in members if m.id != row.owner_id]
    if not members:
        return "❌ Không tìm thấy thành viên."

    if action == "add":
        changed, note = [], []
        try:
            for m in members:
                if channel.overwrites.get(m) is not None:
                    note.append(f"{m.mention} đã có quyền")
                else:
                    await channel.set_permissions(
                        m,
                        overwrite=GUEST_PERMS,
                        reason="Ticket: thêm người vào ticket",
                    )
                    changed.append(m.mention)
        except discord.Forbidden, discord.HTTPException:
            await interaction.followup.send(
                "❌ Bot không có quyền cập nhật quyền kênh (cần Manage Channels).",
                ephemeral=True,
            )
            return None
    else:
        removed, note = [], []
        try:
            for m in members:
                if channel.overwrites.get(m) is None:
                    note.append(f"{m.mention} không có quyền để xóa")
                else:
                    await channel.set_permissions(
                        m,
                        overwrite=None,
                        reason="Ticket: xóa người khỏi ticket",
                    )
                    removed.append(m.mention)
        except discord.Forbidden, discord.HTTPException:
            await interaction.followup.send(
                "❌ Bot không có quyền cập nhật quyền kênh (cần Manage Channels).",
                ephemeral=True,
            )
            return None

    parts = []
    if action == "add":
        if changed:
            parts.append("✅ Đã thêm vào ticket: " + ", ".join(changed))
    elif removed:
        parts.append("✅ Đã xóa khỏi ticket: " + ", ".join(removed))
    if note:
        parts.append("ℹ️ " + "; ".join(note))
    return "\n".join(parts) or "❌ Không có thay đổi nào."


class TicketMemberSelect(ui.Select):
    def __init__(
        self, channel_id: int, action: str, members: list[discord.Member]
    ) -> None:
        self.channel_id = channel_id
        self.action = action
        self.members = members
        options = [
            discord.SelectOption(
                label=(m.display_name or m.name)[:100], value=str(m.id)
            )
            for m in members[:25]
        ]
        if not options:
            options = [
                discord.SelectOption(label="Không có ai trong danh sách", value="none")
            ]
        super().__init__(
            placeholder="Chọn thành viên...",
            min_values=1,
            max_values=len(options),
            options=options,
            disabled=options[0].value == "none",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "none":
            return await interaction.response.defer()
        await interaction.response.defer()
        text = await apply_member_change(
            interaction, self.channel_id, self.action, self.values
        )
        if text:
            try:
                await interaction.message.edit(content=text, view=None)
            except discord.NotFound, discord.HTTPException:
                pass
        self.view.stop()


class TicketMemberModal(ui.Modal, title="Nhập thành viên"):
    target = ui.TextInput(
        label="Mention / ID / Username",
        min_length=1,
        max_length=100,
        placeholder="@tên · 1234567890 · username",
    )

    def __init__(
        self, channel_id: int, action: str, source_message: discord.Message
    ) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.action = action
        self.source_message = source_message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        member = await resolve_member(interaction.guild, self.target.value)
        if not member:
            return await interaction.followup.send(
                "❌ Không tìm thấy người này. Hãy dùng mention `@tên` hoặc ID đầy đủ.",
                ephemeral=True,
            )
        text = await apply_member_change(
            interaction, self.channel_id, self.action, [str(member.id)]
        )
        if text:
            try:
                await self.source_message.edit(content=text, view=None)
            except discord.NotFound, discord.HTTPException:
                pass


class TicketManualButton(ui.Button):
    def __init__(self, channel_id: int, action: str) -> None:
        super().__init__(
            label="Nhập ID/Username", emoji="✍️", style=ButtonStyle.secondary
        )
        self.channel_id = channel_id
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            TicketMemberModal(self.channel_id, self.action, interaction.message)
        )


class TicketMemberPickView(ui.View):
    def __init__(
        self, channel_id: int, action: str, members: list[discord.Member]
    ) -> None:
        super().__init__(timeout=180)
        self.channel_id = channel_id
        self.action = action
        self.add_item(TicketMemberSelect(channel_id, action, members))
        self.add_item(TicketManualButton(channel_id, action))
