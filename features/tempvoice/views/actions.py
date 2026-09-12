import discord
from discord import ButtonStyle, ui

from core.utils import reply_ephemeral, resolve_member
from features.tempvoice import repository
from features.tempvoice.views.embed import _MISSING, edit_panel
from features.tempvoice.views.permissions import OWNER_PERMS

# ---------------------------------------------------------------- hide / lock


async def hide(interaction, channel_id, panel_view):
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    hidden = channel.overwrites_for(guild.default_role).view_channel is False
    await interaction.response.defer(ephemeral=True)
    await channel.set_permissions(
        guild.default_role,
        overwrite=discord.PermissionOverwrite(view_channel=hidden),
    )
    await edit_panel(
        guild, channel, await repository.get_tempvoice(channel_id), panel_view
    )
    text = "🙈 Đã ẩn phòng khỏi danh sách kênh." if not hidden else "👁 Đã hiện phòng."
    await reply_ephemeral(interaction, text)


async def lock(interaction, channel_id, panel_view):
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    locked = channel.overwrites_for(guild.default_role).connect is False
    await interaction.response.defer(ephemeral=True)
    await channel.set_permissions(
        guild.default_role, overwrite=discord.PermissionOverwrite(connect=locked)
    )
    await edit_panel(
        guild, channel, await repository.get_tempvoice(channel_id), panel_view
    )
    text = (
        "🔒 Đã khóa phòng, không ai vào được nữa." if not locked else "🔓 Đã mở phòng."
    )
    await reply_ephemeral(interaction, text)


# ------------------------------------------------------------ member picking


class MemberInputModal(ui.Modal, title="Nhập thành viên"):
    target = ui.TextInput(
        label="Mention / ID / Username",
        min_length=1,
        max_length=100,
        placeholder="@tên · 1234567890 · username",
    )

    def __init__(self, channel_id: int, action: str, panel_view=_MISSING) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.action = action
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        channel = guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ Phòng đã bị xóa.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        member = await resolve_member(guild, self.target.value)
        if not member:
            return await reply_ephemeral(
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
            row = await repository.get_tempvoice(self.channel_id)
            if row and member.id == row.owner_id:
                return await reply_ephemeral(
                    interaction, "❌ Không thể đuổi chủ phòng."
                )
            if member not in channel.members:
                return await reply_ephemeral(
                    interaction, f"{member.mention} không có trong phòng."
                )
            try:
                await member.move_to(None)
            except discord.Forbidden, discord.HTTPException:
                return await reply_ephemeral(
                    interaction,
                    "❌ Không thể đuổi người này (kiểm tra quyền Move Members của bot).",
                )
            text = f"🚪 Đã đuổi {member.mention} khỏi phòng."

        await edit_panel(
            guild,
            channel,
            await repository.get_tempvoice(self.channel_id),
            self.panel_view,
        )
        await reply_ephemeral(interaction, text)


class MemberSelect(ui.Select):
    def __init__(
        self,
        channel_id: int,
        action: str,
        placeholder: str,
        members: list[discord.Member],
    ) -> None:
        self.channel_id = channel_id
        self.action = action
        options = [
            discord.SelectOption(
                label=(m.display_name or m.name)[:100], value=str(m.id)
            )
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
            return await interaction.response.send_message(
                "❌ Phòng đã bị xóa.", ephemeral=True
            )

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
            await edit_panel(
                guild,
                channel,
                await repository.get_tempvoice(channel.id),
                getattr(self.view, "panel_view", _MISSING),
            )

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
            await edit_panel(
                guild,
                channel,
                await repository.get_tempvoice(channel.id),
                getattr(self.view, "panel_view", _MISSING),
            )

        elif self.action == "transfer":
            if not members:
                return await reply_ephemeral(interaction, "❌ Không tìm thấy người đó.")
            target = members[0]
            row = await repository.get_tempvoice(channel.id)
            if not row:
                return await reply_ephemeral(interaction, "❌ Phòng không còn tồn tại.")
            old = guild.get_member(row.owner_id)
            await channel.set_permissions(target, overwrite=OWNER_PERMS)
            if old and old.id != target.id and old in channel.members:
                await channel.set_permissions(old, overwrite=None)
            await repository.update_tempvoice_owner(channel.id, target.id)
            await edit_panel(
                guild,
                channel,
                await repository.get_tempvoice(channel.id),
                getattr(self.view, "panel_view", _MISSING),
            )
            text = f"🔄 Đã chuyển chủ phòng cho {target.mention}"

        await reply_ephemeral(interaction, text)


class ManualInputButton(ui.Button):
    def __init__(self, channel_id: int, action: str, owner_id: int) -> None:
        super().__init__(
            label="Nhập ID/Username", emoji="✍️", style=ButtonStyle.secondary
        )
        self.channel_id = channel_id
        self.action = action
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "❌ Bạn không phải chủ phòng.", ephemeral=True
            )
        await interaction.response.send_modal(
            MemberInputModal(
                self.channel_id, self.action, getattr(self.view, "panel_view", _MISSING)
            )
        )


class PickMemberView(ui.View):
    def __init__(
        self,
        channel_id: int,
        action: str,
        placeholder: str,
        members: list[discord.Member],
        owner_id: int,
        panel_view=_MISSING,
    ) -> None:
        super().__init__(timeout=180)
        self.panel_view = panel_view
        self.add_item(MemberSelect(channel_id, action, placeholder, members))
        if action in ("invite", "kick"):
            self.add_item(ManualInputButton(channel_id, action, owner_id))


# --------------------------------------------------------------- invite/kick/transfer


async def invite(interaction, channel_id, panel_view):
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    row = await repository.get_tempvoice(channel_id)
    if not row:
        return await interaction.response.send_message(
            "❌ Phòng không còn tồn tại.", ephemeral=True
        )

    candidates = [m for m in guild.members if not m.bot and m not in channel.members]
    candidates.sort(key=lambda m: m.display_name.lower())
    if not candidates:
        return await interaction.response.send_message(
            "Không còn ai để mời.", ephemeral=True
        )

    await interaction.response.send_message(
        content="👇 Chọn người mời từ danh sách, hoặc bấm **✍️ Nhập ID/Username**:",
        view=PickMemberView(
            channel_id,
            "invite",
            "Chọn người mời",
            candidates,
            interaction.user.id,
            panel_view,
        ),
        ephemeral=True,
    )


async def kick(interaction, channel_id, panel_view):
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    row = await repository.get_tempvoice(channel_id)
    if not row:
        return await interaction.response.send_message(
            "❌ Phòng không còn tồn tại.", ephemeral=True
        )

    candidates = [m for m in channel.members if m.id != row.owner_id and not m.bot]
    candidates.sort(key=lambda m: m.display_name.lower())
    if not candidates:
        return await interaction.response.send_message(
            "Không có ai trong phòng để đuổi.", ephemeral=True
        )

    await interaction.response.send_message(
        content="👇 Chọn người muốn đuổi, hoặc bấm **✍️ Nhập ID/Username**:",
        view=PickMemberView(
            channel_id,
            "kick",
            "Chọn người đuổi",
            candidates,
            interaction.user.id,
            panel_view,
        ),
        ephemeral=True,
    )


async def transfer(interaction, channel_id, panel_view):
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not channel:
        return await interaction.response.send_message(
            "❌ Phòng đã bị xóa.", ephemeral=True
        )
    row = await repository.get_tempvoice(channel_id)
    if not row:
        return await interaction.response.send_message(
            "❌ Phòng không còn tồn tại.", ephemeral=True
        )

    candidates = [m for m in channel.members if m.id != row.owner_id and not m.bot]
    candidates.sort(key=lambda m: m.display_name.lower())
    if not candidates:
        return await interaction.response.send_message(
            "Không có ai trong phòng để chuyển chủ.", ephemeral=True
        )

    await interaction.response.send_message(
        content="🔄 Chọn người sẽ làm chủ phòng mới:",
        view=PickMemberView(
            channel_id,
            "transfer",
            "Chọn chủ phòng mới",
            candidates,
            interaction.user.id,
            panel_view,
        ),
        ephemeral=True,
    )


# --------------------------------------------------------------------- delete


class ConfirmDeleteView(ui.View):
    def __init__(self, channel_id: int, owner_id: int) -> None:
        super().__init__(timeout=60)
        self.channel_id = channel_id
        self.owner_id = owner_id

    @ui.button(label="Hủy", style=ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _) -> None:
        await interaction.response.edit_message(content="Đã hủy thao tác.", view=None)
        self.stop()

    @ui.button(
        label="Xóa phòng", style=ButtonStyle.danger, custom_id="tv_confirm_delete"
    )
    async def confirm(self, interaction: discord.Interaction, _) -> None:
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "❌ Không được phép.", ephemeral=True
            )
        await interaction.response.edit_message(
            content="🗑 Đang xóa phòng...", view=None
        )
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            text = "❌ Phòng đã bị xóa trước đó."
        else:
            try:
                await channel.delete()
            except discord.Forbidden:
                text = "❌ Không đủ quyền xóa kênh (bot cần quyền Manage Channels)."
            except discord.NotFound, discord.HTTPException:
                text = None
            else:
                await repository.delete_tempvoice(self.channel_id)
                text = "🗑 Đã xóa phòng."
        if text:
            await reply_ephemeral(interaction, text)
        try:
            await interaction.delete_original_response()
        except discord.NotFound, discord.HTTPException:
            pass
        self.stop()


async def delete(interaction, channel_id, panel_view):
    view = ConfirmDeleteView(channel_id, interaction.user.id)
    await interaction.response.send_message(
        "❌ Bạn chắc chắn muốn xóa phòng này? Hành động không thể hoàn tác.",
        view=view,
        ephemeral=True,
    )
