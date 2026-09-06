import asyncio
import os
import re

import discord
from discord import ButtonStyle, ui

from features.tempvoice import repository

THUMBNAIL_URL = os.environ.get("TEMP_VOICE_IMAGE", "")
_MISSING = discord.utils.MISSING


async def _reply_ephemeral(interaction: discord.Interaction, content: str, *, delay: float = 5, **kwargs) -> None:
    try:
        msg = await interaction.followup.send(content, **kwargs)
    except (discord.NotFound, discord.HTTPException):
        return
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except (discord.NotFound, discord.HTTPException):
        pass

OWNER_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    connect=True,
    speak=True,
    stream=True,
    use_voice_activation=True,
    use_embedded_activities=True,
    mute_members=True,
    deafen_members=True,
    move_members=True,
    manage_channels=True,
    manage_permissions=True,
)


def build_embed(guild: discord.Guild, channel: discord.VoiceChannel, owner: discord.Member) -> discord.Embed:
    everyone = channel.overwrites_for(guild.default_role)
    locked = everyone.connect is False
    hidden = everyone.view_channel is False
    limit = channel.user_limit if channel.user_limit else "Không giới hạn"

    embed = discord.Embed(
        title=f"🎙 {channel.name}",
        description="Chọn lệnh bên dưới để điều khiển phòng của bạn.",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="👑 Chủ phòng", value=owner.mention, inline=True)
    embed.add_field(name="👥 Trong phòng", value=str(len(channel.members)), inline=True)
    embed.add_field(name="👤 Giới hạn", value=str(limit), inline=True)
    embed.add_field(name="🔒 Khóa", value="Bật" if locked else "Tắt", inline=True)
    embed.add_field(name="👁 Ẩn", value="Bật" if hidden else "Tắt", inline=True)
    if THUMBNAIL_URL:
        embed.set_thumbnail(url=THUMBNAIL_URL)
    embed.set_footer(text=f"ID phòng: {channel.id}")
    return embed


async def refresh_panel(channel: discord.VoiceChannel) -> None:
    row = await repository.get_by_channel(channel.id)
    await _edit_panel(channel.guild, channel, row)


async def _edit_panel(guild: discord.Guild, channel: discord.VoiceChannel, row, view=_MISSING) -> None:
    if not row or not row.panel_message_id:
        return
    owner = guild.get_member(row.owner_id)
    if not owner:
        return
    try:
        message = await channel.fetch_message(row.panel_message_id)
        await message.edit(embed=build_embed(guild, channel, owner), view=view)
    except (discord.NotFound, discord.HTTPException):
        pass


class _OwnerCheckView(ui.View):
    def __init__(self, channel_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.channel_id = channel_id

    async def owner_check(self, interaction: discord.Interaction) -> bool:
        row = await repository.get_by_channel(self.channel_id)
        if not row:
            await interaction.response.send_message("❌ Phòng này không còn tồn tại.", ephemeral=True)
            return False
        if interaction.user.id != row.owner_id:
            await interaction.response.send_message("❌ Bạn không phải chủ phòng.", ephemeral=True)
            return False
        return True


class ControlPanelView(_OwnerCheckView):
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
        await _dispatch(interaction, self.channel_id, self.values[0], self.view)


async def _dispatch(interaction: discord.Interaction, channel_id: int, action: str, panel_view=_MISSING) -> None:
    guild = interaction.guild
    channel = guild.get_channel(channel_id)

    if action in ("rename", "limit", "status"):
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)
        modal = {"rename": RenameModal, "limit": LimitModal, "status": StatusModal}[action]
        await interaction.response.send_modal(modal(channel_id, panel_view))

    elif action == "lock":
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)
        locked = channel.overwrites_for(guild.default_role).connect is False
        await interaction.response.defer(ephemeral=True)
        await channel.set_permissions(guild.default_role, overwrite=discord.PermissionOverwrite(connect=locked))
        await _edit_panel(guild, channel, await repository.get_by_channel(channel_id), panel_view)
        text = "🔒 Đã khóa phòng, không ai vào được nữa." if not locked else "🔓 Đã mở phòng."
        await _reply_ephemeral(interaction, text)

    elif action == "hide":
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)
        hidden = channel.overwrites_for(guild.default_role).view_channel is False
        await interaction.response.defer(ephemeral=True)
        await channel.set_permissions(guild.default_role, overwrite=discord.PermissionOverwrite(view_channel=hidden))
        await _edit_panel(guild, channel, await repository.get_by_channel(channel_id), panel_view)
        text = "🙈 Đã ẩn phòng khỏi danh sách kênh." if not hidden else "👁 Đã hiện phòng."
        await _reply_ephemeral(interaction, text)

    elif action in ("invite", "kick", "transfer"):
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)
        row = await repository.get_by_channel(channel_id)
        if not row:
            return await interaction.response.send_message("❌ Phòng không còn tồn tại.", ephemeral=True)

        if action == "invite":
            candidates = [m for m in guild.members if not m.bot and m not in channel.members]
            placeholder = "Chọn người mời"
            prompt = "👇 Chọn người mời từ danh sách, hoặc bấm **✍️ Nhập ID/Username**:"
        else:
            candidates = [m for m in channel.members if m.id != row.owner_id and not m.bot]
            placeholder = "Chọn người đuổi" if action == "kick" else "Chọn chủ phòng mới"
            prompt = (
                "👇 Chọn người muốn đuổi, hoặc bấm **✍️ Nhập ID/Username**:"
                if action == "kick"
                else "🔄 Chọn người sẽ làm chủ phòng mới:"
            )

        candidates.sort(key=lambda m: m.display_name.lower())
        if not candidates:
            empty = (
                "Không còn ai để mời."
                if action == "invite"
                else "Không có ai trong phòng để đuổi."
                if action == "kick"
                else "Không có ai trong phòng để chuyển chủ."
            )
            return await interaction.response.send_message(empty, ephemeral=True)

        await interaction.response.send_message(
            content=prompt,
            view=PickMemberView(channel_id, action, placeholder, candidates, interaction.user.id, panel_view),
            ephemeral=True,
        )

    elif action == "delete":
        view = _ConfirmDeleteView(channel_id, interaction.user.id)
        await interaction.response.send_message(
            "❌ Bạn chắc chắn muốn xóa phòng này? Hành động không thể hoàn tác.",
            view=view,
            ephemeral=True,
        )


class RenameModal(ui.Modal, title="Đổi tên phòng"):
    name = ui.TextInput(label="Tên phòng mới", min_length=1, max_length=100, placeholder="Nhập tên phòng...")

    def __init__(self, channel_id: int, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await channel.edit(name=self.name.value)
        await _edit_panel(interaction.guild, channel, await repository.get_by_channel(self.channel_id), self.panel_view)
        await _reply_ephemeral(interaction, f"✅ Đã đổi tên thành: **{self.name.value}**")


class LimitModal(ui.Modal, title="Giới hạn người vào phòng"):
    limit = ui.TextInput(label="Số người tối đa (1-99, 0 = không giới hạn)", min_length=1, max_length=2, placeholder="0")

    def __init__(self, channel_id: int, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)
        raw = self.limit.value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message("❌ Vui lòng nhập số từ 0 đến 99.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        value = min(int(raw), 99)
        await channel.edit(user_limit=value)
        await _edit_panel(interaction.guild, channel, await repository.get_by_channel(self.channel_id), self.panel_view)
        text = "Không giới hạn" if value == 0 else f"{value} người"
        await _reply_ephemeral(interaction, f"✅ Đã đặt giới hạn: **{text}**.")


class StatusModal(ui.Modal, title="Đổi trạng thái kênh"):
    status = ui.TextInput(label="Trạng thái kênh (bỏ trống để xóa)", max_length=500, required=False, placeholder="Đang nghiên cứu...")

    def __init__(self, channel_id: int, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)
        value = self.status.value.strip() or None
        await interaction.response.defer(ephemeral=True)
        try:
            await channel.edit(status=value)
        except (discord.Forbidden, discord.HTTPException):
            text = (
                "❌ Không đặt được trạng thái kênh (server cần ít nhất 1 Level Boost "
                "và bot cần quyền Manage Channels)."
            )
        else:
            text = "✅ Đã cập nhật trạng thái kênh."
        await _edit_panel(interaction.guild, channel, await repository.get_by_channel(self.channel_id), self.panel_view)
        await _reply_ephemeral(interaction, text)


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


class MemberInputModal(ui.Modal, title="Nhập thành viên"):
    target = ui.TextInput(label="Mention / ID / Username", min_length=1, max_length=100, placeholder="@tên · 1234567890 · username")

    def __init__(self, channel_id: int, action: str, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.action = action
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        channel = guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        member = await _resolve_member(guild, self.target.value)
        if not member:
            return await _reply_ephemeral(
                interaction,
                "❌ Không tìm thấy người này. Hãy dùng mention `@tên` hoặc ID đầy đủ.",
            )

        if self.action == "invite":
            if member in channel.members:
                text = f"{member.mention} đã ở trong phòng rồi."
            else:
                await channel.set_permissions(member, view_channel=True, connect=True)
                text = f"✅ Đã cấp quyền vào phòng cho {member.mention}."

        elif self.action == "kick":
            row = await repository.get_by_channel(self.channel_id)
            if row and member.id == row.owner_id:
                return await _reply_ephemeral(interaction, "❌ Không thể đuổi chủ phòng.")
            if member not in channel.members:
                return await _reply_ephemeral(interaction, f"{member.mention} không có trong phòng.")
            try:
                await member.move_to(None)
            except (discord.Forbidden, discord.HTTPException):
                return await _reply_ephemeral(
                    interaction,
                    "❌ Không thể đuổi người này (kiểm tra quyền Move Members của bot).",
                )
            text = f"🚪 Đã đuổi {member.mention} khỏi phòng."

        await _edit_panel(guild, channel, await repository.get_by_channel(self.channel_id), self.panel_view)
        await _reply_ephemeral(interaction, text)


class MemberSelect(ui.Select):
    def __init__(self, channel_id: int, action: str, placeholder: str, members: list[discord.Member]) -> None:
        self.channel_id = channel_id
        self.action = action
        options = [
            discord.SelectOption(label=(m.display_name or m.name)[:100], value=str(m.id))
            for m in members[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="Không có ai", value="none")]
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=len(options),
            options=options,
            disabled=options[0].value == "none",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        channel = guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Phòng đã bị xóa.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        ids = [int(v) for v in self.values if v.isdigit()]
        members = [guild.get_member(i) for i in ids]
        members = [m for m in members if m]

        if self.action == "invite":
            added = []
            for m in members:
                if m not in channel.members:
                    await channel.set_permissions(m, view_channel=True, connect=True)
                    added.append(m.mention)
            text = f"✅ Đã cấp quyền vào phòng cho: {', '.join(added) if added else 'ai cả'}"
            await _edit_panel(guild, channel, await repository.get_by_channel(channel.id), getattr(self.view, "panel_view", _MISSING))

        elif self.action == "kick":
            kicked = 0
            for m in members:
                if m in channel.members:
                    try:
                        await m.move_to(None)
                        kicked += 1
                    except discord.HTTPException:
                        pass
            text = f"🚪 Đã đuổi {kicked} người khỏi phòng."
            await _edit_panel(guild, channel, await repository.get_by_channel(channel.id), getattr(self.view, "panel_view", _MISSING))

        elif self.action == "transfer":
            if not members:
                return await _reply_ephemeral(interaction, "❌ Không tìm thấy người đó.")
            target = members[0]
            row = await repository.get_by_channel(channel.id)
            if not row:
                return await _reply_ephemeral(interaction, "❌ Phòng không còn tồn tại.")
            old = guild.get_member(row.owner_id)
            await channel.set_permissions(target, overwrite=OWNER_PERMS)
            if old and old.id != target.id and old in channel.members:
                await channel.set_permissions(old, overwrite=None)
            await repository.set_owner(channel.id, target.id)
            await _edit_panel(guild, channel, await repository.get_by_channel(channel.id), getattr(self.view, "panel_view", _MISSING))
            text = f"🔄 Đã chuyển chủ phòng cho {target.mention}"

        await _reply_ephemeral(interaction, text)


class _ManualInputButton(ui.Button):
    def __init__(self, channel_id: int, action: str, owner_id: int) -> None:
        super().__init__(label="Nhập ID/Username", emoji="✍️", style=ButtonStyle.secondary)
        self.channel_id = channel_id
        self.action = action
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("❌ Bạn không phải chủ phòng.", ephemeral=True)
        await interaction.response.send_modal(
            MemberInputModal(self.channel_id, self.action, getattr(self.view, "panel_view", _MISSING))
        )


class PickMemberView(ui.View):
    def __init__(
        self, channel_id: int, action: str, placeholder: str, members: list[discord.Member], owner_id: int, panel_view=_MISSING
    ) -> None:
        super().__init__(timeout=180)
        self.panel_view = panel_view
        self.add_item(MemberSelect(channel_id, action, placeholder, members))
        if action in ("invite", "kick"):
            self.add_item(_ManualInputButton(channel_id, action, owner_id))


class _ConfirmDeleteView(ui.View):
    def __init__(self, channel_id: int, owner_id: int) -> None:
        super().__init__(timeout=60)
        self.channel_id = channel_id
        self.owner_id = owner_id

    @ui.button(label="Hủy", style=ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _) -> None:
        await interaction.response.edit_message(content="Đã hủy thao tác.", view=None)
        self.stop()

    @ui.button(label="Xóa phòng", style=ButtonStyle.danger, custom_id="tv_confirm_delete")
    async def confirm(self, interaction: discord.Interaction, _) -> None:
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("❌ Không được phép.", ephemeral=True)
        await interaction.response.edit_message(content="🗑 Đang xóa phòng...", view=None)
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            text = "❌ Phòng đã bị xóa trước đó."
        else:
            try:
                await channel.delete()
            except discord.Forbidden:
                text = "❌ Không đủ quyền xóa kênh (bot cần quyền Manage Channels)."
            except (discord.NotFound, discord.HTTPException):
                text = None
            else:
                await repository.remove(self.channel_id)
                text = "🗑 Đã xóa phòng."
        if text:
            await _reply_ephemeral(interaction, text)
        try:
            await interaction.delete_original_response()
        except (discord.NotFound, discord.HTTPException):
            pass
        self.stop()