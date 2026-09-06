import discord
from discord.ext import commands

from features.tempvoice import repository, service
from features.tempvoice.views import ControlPanelView

TARGET_GUILD_ID = 1275798785318064138


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))
    for row in await repository.get_all():
        channel = bot.get_channel(row.channel_id)
        if not channel or not row.panel_message_id:
            continue
        try:
            await channel.fetch_message(row.panel_message_id)
        except discord.NotFound, discord.Forbidden, discord.HTTPException:
            continue
        bot.add_view(
            ControlPanelView(bot, row.channel_id), message_id=row.panel_message_id
        )


class TempVoice(commands.Cog):
    """Phòng voice riêng được tạo từ kênh 'Create Voice'."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after) -> None:
        if member.bot:
            return

        leaving = before.channel
        joining = after.channel
        moved = leaving != joining

        if joining and moved and service.is_trigger_channel(joining):
            existing = await repository.get_by_channel(joining.id)
            if existing:
                await service.refresh_panel(joining)
            else:
                await self._create_room_for(member, joining)

        if leaving and (not joining or leaving.id != joining.id):
            row = await repository.get_by_channel(leaving.id)
            if row:
                await service.refresh_panel(leaving)
                if not leaving.members:
                    await service.delete_room(leaving)

        if joining and moved:
            row = await repository.get_by_channel(joining.id)
            if row:
                await service.refresh_panel(joining)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel) -> None:
        if isinstance(channel, discord.VoiceChannel):
            await repository.remove(channel.id)

    @commands.command(aliases=["tempvoice"], hidden=True)
    @commands.is_owner()
    async def voicelist(self, ctx: commands.Context):
        """Danh sách các phòng voice tạm đang hoạt động."""
        rows = await repository.get_all()
        if not rows:
            return await ctx.reply("Hiện không có phòng voice tạm nào.")

        lines = []
        for row in rows:
            channel = self.bot.get_channel(row.channel_id)
            if not channel:
                continue
            owner = ctx.guild.get_member(row.owner_id)
            lines.append(
                f"{channel.mention} — chủ: {owner.mention if owner else row.owner_id} "
                f"({len(channel.members)} người)"
            )
        if not lines:
            return await ctx.reply("Hiện không có phòng voice tạm nào.")
        await ctx.reply("\n".join(lines))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def createvoice(self, ctx: commands.Context):
        """Tạo kênh trigger 'Create Voice' (chỉ ở server chính)."""
        if ctx.guild.id != TARGET_GUILD_ID:
            return await ctx.reply(
                f"❌ Lệnh này chỉ chạy ở server `{TARGET_GUILD_ID}`."
            )

        existing = discord.utils.get(
            ctx.guild.voice_channels, name=service.TRIGGER_NAME
        )
        if existing:
            return await ctx.reply(
                f"✅ Kênh `{service.TRIGGER_NAME}` đã có sẵn ({existing.mention})."
            )

        await ctx.typing()
        try:
            channel = await ctx.guild.create_voice_channel(
                name=service.TRIGGER_NAME, reason="TempVoice: setup kênh trigger"
            )
        except discord.Forbidden:
            return await ctx.reply(
                "❌ Bot không có quyền Manage Channels trong server này."
            )
        await ctx.reply(
            f"✅ Đã tạo kênh trigger {channel.mention}. Ai bấm vào sẽ được tạo phòng riêng."
        )

    @commands.command(name="chaninfo")
    @commands.guild_only()
    async def chaninfo(self, ctx: commands.Context, channel_id: int):
        """Tra thông tin kênh theo ID."""
        channel = ctx.guild.get_channel(channel_id) or ctx.guild.get_channel_or_thread(
            channel_id
        )
        if not channel:
            return await ctx.reply(
                f"❌ Không tìm thấy kênh **{channel_id}** trong cache của server."
            )

        embed = discord.Embed(title="ℹ️ Thông tin kênh", color=discord.Color.blurple())
        embed.add_field(name="Tên", value=channel.mention, inline=True)
        embed.add_field(name="Loại", value=channel.type.name.capitalize(), inline=True)
        embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(
            name="Category",
            value=channel.category.mention
            if getattr(channel, "category", None)
            else "Không có",
            inline=True,
        )
        embed.add_field(
            name="Ngày tạo",
            value=discord.utils.format_dt(channel.created_at, "R"),
            inline=True,
        )

        if isinstance(channel, discord.VoiceChannel):
            embed.add_field(
                name="👥 Trong phòng", value=str(len(channel.members)), inline=True
            )
            embed.add_field(
                name="👤 Giới hạn",
                value=str(channel.user_limit)
                if channel.user_limit
                else "Không giới hạn",
                inline=True,
            )
            embed.add_field(
                name="📌 Status",
                value=getattr(channel, "status", None) or "Không có",
                inline=True,
            )

        row = await repository.get_by_channel(channel_id)
        if row:
            owner = ctx.guild.get_member(row.owner_id)
            embed.add_field(
                name="⚡ Phòng temp",
                value=(
                    f"Chủ phòng: {owner.mention if owner else row.owner_id}\n"
                    f"Panel message: `{row.panel_message_id}`"
                ),
                inline=False,
            )
        elif (
            isinstance(channel, discord.VoiceChannel)
            and channel.name == service.TRIGGER_NAME
        ):
            embed.add_field(
                name="ℹ️ Ghi chú",
                value="Đây là kênh **trigger** tạo phòng temp.",
                inline=False,
            )

        await ctx.reply(embed=embed)

    async def _create_room_for(
        self, member: discord.Member, trigger: discord.VoiceChannel
    ) -> None:
        try:
            await service.create_room(self.bot, member, trigger)
        except discord.Forbidden as exc:
            message = (
                "⚠️ Không thể tạo phòng voice.\n"
                f"Lỗi: {exc}\n"
                "Bot cần quyền **Manage Channels** và **Move Members**."
            )
            await self._try_dm(member, message)
        except discord.HTTPException as exc:
            await self._try_dm(member, f"⚠️ Không thể tạo phòng voice (lỗi API): {exc}")
        except Exception as exc:
            print(f"[tempvoice] create_room error: {exc!r}")

    async def _try_dm(self, member: discord.Member, content: str) -> None:
        try:
            await member.send(content)
        except discord.Forbidden, discord.HTTPException:
            pass
