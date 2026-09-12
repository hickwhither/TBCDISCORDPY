import asyncio

import discord
from discord.ext import commands

from features.tempvoice import repository, service
from features.tempvoice.views import ControlPanelView, refresh_panel


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))


class TempVoice(commands.Cog):
    """Phòng voice riêng được tạo từ kênh 'Create Voice'."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._views_registered = False
        self.bot.loop.create_task(self._sweep_loop())

    async def register_persistent_views(self) -> None:
        if self._views_registered:
            return
        self._views_registered = True
        for row in await repository.get_all_tempvoice():
            channel = self.bot.get_channel(row.channel_id)
            if not channel or not row.panel_message_id:
                continue
            try:
                await channel.fetch_message(row.panel_message_id)
            except discord.NotFound, discord.Forbidden, discord.HTTPException:
                continue
            self.bot.add_view(
                ControlPanelView(self.bot, row.channel_id),
                message_id=row.panel_message_id,
            )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.register_persistent_views()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after) -> None:
        if member.bot:
            return

        if before.channel == after.channel:
            return

        if after.channel and await repository.get_createvoice(after.channel.id):
            try:
                await service.create_room(self.bot, member, after.channel)
            except discord.Forbidden as exc:
                message = (
                    "⚠️ Không thể tạo phòng voice.\n"
                    f"Lỗi: {exc}\n"
                    "Bot cần quyền **Manage Channels** và **Move Members**."
                )
                await after.channel.send(message)
            except discord.HTTPException as exc:
                await after.channel.send(
                    f"⚠️ Không thể tạo phòng voice (lỗi API): {exc}"
                )
            except Exception as exc:
                print(f"[tempvoice] create_room error: {exc!r}")

            return

        if before.channel:
            row = await repository.get_tempvoice(before.channel.id)
            if not row:
                return
            if not before.channel.members:
                await service.delete_room(before.channel)
            else:
                await refresh_panel(before.channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel) -> None:
        if isinstance(channel, discord.VoiceChannel):
            await repository.delete_tempvoice(channel.id)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def createvoice(self, ctx: commands.Context):
        """Tạo kênh trigger 'Create Voice'."""
        existing = await repository.get_createvoice(ctx.channel.id)
        if existing:
            return await ctx.reply("✅ Kênh này đã được setup trigger.", delete_after=5)
        await repository.create_createvoice(ctx.channel.id, ctx.guild.id)
        await ctx.reply(
            "✅ Kênh này đã được setup trigger. Ai bấm vào sẽ được tạo phòng riêng."
        )
        await ctx.message.delete()

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

        row = await repository.get_tempvoice(channel_id)
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

    async def _sweep_loop(self) -> None:
        try:
            await self.bot.wait_until_ready()
            while not self.bot.is_closed():
                try:
                    await self._sweep_empty_rooms()
                except Exception as exc:
                    print(f"[tempvoice] sweep error: {exc!r}")
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def _sweep_empty_rooms(self) -> None:
        for row in await repository.get_all_tempvoice():
            channel = self.bot.get_channel(row.channel_id)
            if channel is None:
                await repository.delete_tempvoice(row.channel_id)
            elif isinstance(channel, discord.VoiceChannel) and not channel.members:
                await service.delete_room(channel)
