import asyncio
import os
import re
from datetime import datetime, timezone

import discord
from discord import ButtonStyle, ui

from features.tickets import repository

AUTO_CLOSE_HOURS = float(os.environ.get("TICKET_AUTO_CLOSE_HOURS", "24"))
WARN_BEFORE_MINUTES = float(os.environ.get("TICKET_WARN_BEFORE_MINUTES", "30"))
STAFF_ROLE_NAME = os.environ.get("TICKET_STAFF_ROLE", "Staff")
MAX_TICKETS_PER_USER = int(os.environ.get("TICKET_MAX_PER_USER", "2"))

BOT_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
    manage_messages=True,
    manage_channels=True,
)

OWNER_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
)


def _owner_overwrite(*, send: bool) -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(
        view_channel=True,
        send_messages=send,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
        add_reactions=True,
    )


GUEST_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
)

STAFF_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
    manage_messages=True,
    manage_channels=True,
)


def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.name.casefold() == STAFF_ROLE_NAME.casefold() for role in member.roles)


def _utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _dt_to_unix(dt: datetime) -> int:
    return int(_utc_naive(dt).replace(tzinfo=timezone.utc).timestamp())


async def _unique_ticket_name(guild: discord.Guild) -> str:
    taken = {c.name for c in guild.text_channels}
    number = 1
    while f"ticket-{number}" in taken:
        number += 1
    return f"ticket-{number}"


async def _staff_overwrites(guild: discord.Guild) -> dict:
    overlords = [r for r in guild.roles if r.name.casefold() == STAFF_ROLE_NAME.casefold() or r.permissions.administrator]
    manageable = {r for r in overlords if r.is_assignable()}
    return {role: STAFF_PERMS for role in manageable}


class TicketLimitError(Exception):
    def __init__(self, open_count: int, limit: int) -> None:
        super().__init__(f"Đang mở {open_count}/{limit} ticket")
        self.open_count = open_count
        self.limit = limit


async def create_ticket(
    guild: discord.Guild, member: discord.Member, category_id: int | None = None
) -> discord.TextChannel:
    existing = await repository.list_open_by_owner(guild.id, member.id)
    if len(existing) >= MAX_TICKETS_PER_USER:
        raise TicketLimitError(len(existing), MAX_TICKETS_PER_USER)

    category = guild.get_channel(category_id) if category_id else None
    if not isinstance(category, discord.CategoryChannel):
        category = None

    name = await _unique_ticket_name(guild)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False, send_messages=False, read_message_history=False
        ),
        guild.me: BOT_PERMS,
        member: OWNER_PERMS,
    }
    overwrites.update(await _staff_overwrites(guild))

    channel = await guild.create_text_channel(
        name=name,
        category=category,
        overwrites=overwrites,
        reason=f"Ticket: tạo ticket cho {member}",
    )

    embed = build_embed(guild, channel, owner_id=member.id)
    view = TicketPanelView(guild, channel.id)
    panel_message_id = None
    try:
        panel = await channel.send(embed=embed, view=view)
        panel_message_id = panel.id
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(f"[tickets] không gửi được panel: {exc!r}")
    await repository.add(channel.id, guild.id, member.id, panel_message_id)
    return channel


async def _reply_ephemeral(
    interaction: discord.Interaction, content: str, *, delay: float = 5, **kwargs
) -> None:
    try:
        msg = await interaction.followup.send(content, **kwargs)
    except (discord.NotFound, discord.HTTPException):
        return
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except (discord.NotFound, discord.HTTPException):
        pass


def build_embed(
    guild: discord.Guild,
    channel: discord.TextChannel,
    *,
    owner_id: int,
    status: str = "open",
    created_at: datetime | None = None,
) -> discord.Embed:
    owner = guild.get_member(owner_id)
    status_text = "🟢 Đang mở" if status == "open" else "🔴 Đã đóng"
    opened = f"<t:{_dt_to_unix(created_at)}:R>" if created_at else "vừa mới"

    embed = discord.Embed(
        title=f"🎫 {channel.name}",
        description=(
            "**Hướng dẫn sử dụng:**\n"
            "• Mô tả rõ vấn đề/báo cáo của bạn ở bên dưới.\n"
            "• Đội ngũ hỗ trợ sẽ phản hồi trong ticket này.\n"
            "• Hãy tôn trọng, cẩn thận lời nói của nhau.\n"
            "• Bấm **🔒 Đóng Ticket** khi xong việc.\n"
            "• Bấm **🗑 Xóa Ticket** để xóa kênh (sẽ xác nhận lại).\n"
            f"• Ticket không hoạt động quá **{int(AUTO_CLOSE_HOURS)} giờ** sẽ tự động bị xóa."
        ),
        color=discord.Color.green() if status == "open" else discord.Color.red(),
    )
    embed.add_field(name="👤 Chủ ticket", value=owner.mention if owner else f"`{owner_id}`", inline=True)
    embed.add_field(name="📌 Trạng thái", value=status_text, inline=True)
    embed.add_field(name="📅 Mở lúc", value=opened, inline=True)
    embed.add_field(name="🔗 Kênh", value=channel.mention, inline=True)
    embed.set_footer(text=f"ID ticket: {channel.id}")
    return embed


async def refresh_panel(channel: discord.TextChannel) -> None:
    row = await repository.get_by_channel(channel.id)
    await _edit_panel(channel.guild, channel, row)


async def _edit_panel(guild: discord.Guild, channel: discord.TextChannel, row) -> None:
    if not row or not row.panel_message_id:
        return
    embed = build_embed(
        guild, channel, owner_id=row.owner_id, status=row.status, created_at=row.created_at
    )
    view = TicketPanelView(guild, channel.id, status=row.status)
    try:
        message = await channel.fetch_message(row.panel_message_id)
        await message.edit(embed=embed, view=view)
    except (discord.NotFound, discord.HTTPException):
        pass


class TicketCreateView(ui.View):
    def __init__(self, bot, category_id: int | None) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.category_id = category_id

    @ui.button(label="Tạo Ticket", emoji="🎫", style=ButtonStyle.primary, custom_id="ticket_create")
    async def create(self, interaction: discord.Interaction, _) -> None:
        guild = interaction.guild
        existing = await repository.list_open_by_owner(guild.id, interaction.user.id)
        if len(existing) >= MAX_TICKETS_PER_USER:
            lines = "\n".join(
                (guild.get_channel(t.channel_id).mention if guild.get_channel(t.channel_id) else f"`{t.channel_id}`")
                for t in existing[:MAX_TICKETS_PER_USER]
            )
            text = (
                f"❌ Bạn đang có **{len(existing)} ticket** đang mở (giới hạn tối đa "
                f"**{MAX_TICKETS_PER_USER}**).\n{lines}"
            )
            return await interaction.response.send_message(text, ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        try:
            channel = await create_ticket(guild, interaction.user, self.category_id)
        except TicketLimitError as exc:
            text = (
                f"❌ Bạn đang có **{exc.open_count} ticket** đang mở "
                f"(giới hạn tối đa **{exc.limit}**)."
            )
            return await _reply_ephemeral(interaction, text)
        except discord.Forbidden:
            text = "⚠️ Bot không đủ quyền **Manage Channels** để tạo kênh ticket."
            return await _reply_ephemeral(interaction, text)
        except discord.HTTPException as exc:
            return await _reply_ephemeral(interaction, f"⚠️ Không tạo được ticket (lỗi API): {exc}")
        await _reply_ephemeral(interaction, f"✅ Đã tạo ticket cho bạn: {channel.mention}", delay=8)


async def _allowed(interaction: discord.Interaction, row) -> bool:
    if not row:
        await interaction.response.send_message("❌ Ticket không còn tồn tại.", ephemeral=True)
        return False
    if interaction.user.id != row.owner_id and not is_staff(interaction.user):
        await interaction.response.send_message(
            "❌ Chỉ chủ ticket hoặc Staff mới được thực hiện hành động này.", ephemeral=True
        )
        return False
    return True


class _CloseButton(ui.Button):
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
        if not await _allowed(interaction, row):
            return
        if row.status != "open":
            return await interaction.response.send_message("ℹ️ Ticket này đã được đóng.", ephemeral=True)

        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Ticket đã bị xóa.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        owner = interaction.guild.get_member(row.owner_id)
        if owner:
            await channel.set_permissions(
                owner, overwrite=_owner_overwrite(send=False), reason="Ticket: đóng ticket"
            )
        await repository.set_status(self.channel_id, "closed")
        await refresh_panel(channel)
        await channel.send(
            f"🔒 **{interaction.user.mention} đã đóng ticket.**\n"
            "Kênh bị khóa chat nhưng chưa bị xóa. Staff có thể **🔓 Mở lại** hoặc **🗑 Xóa**."
        )
        await _reply_ephemeral(interaction, "🔒 Đã đóng ticket. Chat đã bị khóa.")


class _ReopenButton(ui.Button):
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
        if not await _allowed(interaction, row):
            return
        if row.status != "closed":
            return await interaction.response.send_message("ℹ️ Ticket này đang mở.", ephemeral=True)

        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Ticket đã bị xóa.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        owner = interaction.guild.get_member(row.owner_id)
        if owner:
            await channel.set_permissions(
                owner, overwrite=_owner_overwrite(send=True), reason="Ticket: mở lại ticket"
            )
        await repository.set_status(self.channel_id, "open")
        await refresh_panel(channel)
        await channel.send(f"🔓 **{interaction.user.mention} đã mở lại ticket.**")
        await _reply_ephemeral(interaction, "🔓 Đã mở lại ticket.")


class _DeleteButton(ui.Button):
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
            return await interaction.response.send_message("❌ Ticket không còn tồn tại.", ephemeral=True)
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Chỉ **Staff/Admin** mới được xóa ticket.", ephemeral=True
            )
        await interaction.response.send_message(
            "🗑 Bạn chắc chắn muốn **xóa ticket này**? Hành động không thể hoàn tác.",
            view=_ConfirmDeleteView(self.channel_id, interaction.user.id),
            ephemeral=True,
        )


class TicketPanelView(ui.View):
    def __init__(self, bot, channel_id: int, *, status: str = "open") -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.channel_id = channel_id
        self._status = status
        self.add_item(_CloseButton(channel_id, disabled=status != "open"))
        self.add_item(_ReopenButton(channel_id, disabled=status != "closed"))
        self.add_item(_DeleteButton(channel_id))


class _ConfirmDeleteView(ui.View):
    def __init__(self, channel_id: int, actor_id: int) -> None:
        super().__init__(timeout=60)
        self.channel_id = channel_id
        self.actor_id = actor_id

    @ui.button(label="Hủy", style=ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _) -> None:
        await interaction.response.edit_message(content="Đã hủy thao tác.", view=None)
        self.stop()

    @ui.button(label="Xác nhận xóa", style=ButtonStyle.danger, custom_id="tk_confirm_delete")
    async def confirm(self, interaction: discord.Interaction, _) -> None:
        if interaction.user.id != self.actor_id:
            return await interaction.response.send_message("❌ Không được phép.", ephemeral=True)
        await interaction.response.edit_message(content="🗑 Đang xóa ticket...", view=None)
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            text = "❌ Ticket đã bị xóa trước đó."
        else:
            try:
                await channel.delete(reason="Ticket: xóa ticket")
            except discord.Forbidden:
                text = "❌ Bot không đủ quyền xóa kênh (cần quyền Manage Channels)."
            except (discord.NotFound, discord.HTTPException):
                text = None
            else:
                await repository.remove(self.channel_id)
                text = "🗑 Đã xóa ticket."
        if text:
            await _reply_ephemeral(interaction, text)
        try:
            await interaction.delete_original_response()
        except (discord.NotFound, discord.HTTPException):
            pass
        self.stop()


async def _resolve_member(guild: discord.Guild, value: str) -> discord.Member | None:
    value = value.strip()
    if not value:
        return None

    match = re.fullmatch(r"<@!?(\d+)>", value)
    if match:
        user_id = int(match.group(1))
    elif value.isdigit():
        user_id = int(value)
    else:
        user_id = None

    if user_id:
        member = guild.get_member(user_id)
        if member:
            return member
        try:
            return await guild.fetch_member(user_id)
        except (discord.NotFound, discord.HTTPException):
            return None

    search = value.casefold()
    exact, prefix = [], []
    for m in guild.members:
        names = {m.name, m.display_name, m.global_name or "", m.nick or ""}
        folded = {c.casefold() for c in names if c}
        if search in folded:
            exact.append(m)
        elif any(c.startswith(search) for c in folded):
            prefix.append(m)

    if len(exact) == 1:
        return exact[0]
    if not exact and len(prefix) == 1:
        return prefix[0]
    return None


async def _apply_member_change(
    interaction: discord.Interaction, channel_id: int, action: str, member_ids: list[str]
) -> str | None:
    """Thêm/xóa thành viên khỏi ticket. Trả về text xác nhận, None nếu đã báo lỗi."""
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return "❌ Ticket đã bị xóa."
    row = await repository.get_by_channel(channel_id)
    if not row:
        return "❌ Ticket không còn tồn tại."

    members = [m for raw in member_ids if raw.isdigit() and (m := guild.get_member(int(raw))) is not None]
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
                    await channel.set_permissions(m, overwrite=GUEST_PERMS, reason="Ticket: thêm người vào ticket")
                    changed.append(m.mention)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send(
                "❌ Bot không có quyền cập nhật quyền kênh (cần Manage Channels).", ephemeral=True
            )
            return None
    else:
        removed, note = [], []
        try:
            for m in members:
                if channel.overwrites.get(m) is None:
                    note.append(f"{m.mention} không có quyền để xóa")
                else:
                    await channel.set_permissions(m, overwrite=None, reason="Ticket: xóa người khỏi ticket")
                    removed.append(m.mention)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.followup.send(
                "❌ Bot không có quyền cập nhật quyền kênh (cần Manage Channels).", ephemeral=True
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
    def __init__(self, channel_id: int, action: str, members: list[discord.Member]) -> None:
        self.channel_id = channel_id
        self.action = action
        self.members = members
        options = [
            discord.SelectOption(label=(m.display_name or m.name)[:100], value=str(m.id))
            for m in members[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="Không có ai trong danh sách", value="none")]
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
        text = await _apply_member_change(interaction, self.channel_id, self.action, self.values)
        if text:
            try:
                await interaction.message.edit(content=text, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
        self.view.stop()


class TicketMemberModal(ui.Modal, title="Nhập thành viên"):
    target = ui.TextInput(
        label="Mention / ID / Username",
        min_length=1,
        max_length=100,
        placeholder="@tên · 1234567890 · username",
    )

    def __init__(self, channel_id: int, action: str, source_message: discord.Message) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.action = action
        self.source_message = source_message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        member = await _resolve_member(interaction.guild, self.target.value)
        if not member:
            return await interaction.followup.send(
                "❌ Không tìm thấy người này. Hãy dùng mention `@tên` hoặc ID đầy đủ.", ephemeral=True
            )
        text = await _apply_member_change(interaction, self.channel_id, self.action, [str(member.id)])
        if text:
            try:
                await self.source_message.edit(content=text, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass


class TicketManualButton(ui.Button):
    def __init__(self, channel_id: int, action: str) -> None:
        super().__init__(label="Nhập ID/Username", emoji="✍️", style=ButtonStyle.secondary)
        self.channel_id = channel_id
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketMemberModal(self.channel_id, self.action, interaction.message))


class TicketMemberPickView(ui.View):
    def __init__(self, channel_id: int, action: str, members: list[discord.Member]) -> None:
        super().__init__(timeout=180)
        self.channel_id = channel_id
        self.action = action
        self.add_item(TicketMemberSelect(channel_id, action, members))
        self.add_item(TicketManualButton(channel_id, action))