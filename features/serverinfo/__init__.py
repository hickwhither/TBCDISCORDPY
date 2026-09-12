import discord
from discord.ext import commands

from features.serverinfo import repository, service


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerInfo(bot))


class ServerInfo(commands.Cog):
    """📊 Panel thông tin server, tự động gửi và cập nhật."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._synced = False

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._synced:
            return
        self._synced = True
        for row in await repository.get_panels():
            guild = self.bot.get_guild(row.guild_id)
            if not guild:
                await repository.remove_panel(row.guild_id)
                continue
            channel = guild.get_channel(row.channel_id)
            if not isinstance(channel, discord.TextChannel):
                await repository.remove_panel(row.guild_id)
                continue
            await service.refresh_panel(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        guild = member.guild
        if await repository.get_panel(guild.id):
            await service.refresh_panel(guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        guild = member.guild
        if await repository.get_panel(guild.id):
            await service.refresh_panel(guild)

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if before.roles == after.roles:
            return
        guild = after.guild
        if await repository.get_panel(guild.id):
            await service.refresh_panel(guild)

    @commands.Cog.listener()
    async def on_guild_update(
        self, before: discord.Guild, after: discord.Guild
    ) -> None:
        if (
            before.premium_subscription_count == after.premium_subscription_count
            and before.premium_tier == after.premium_tier
        ):
            return
        if await repository.get_panel(after.id):
            await service.refresh_panel(after)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel) -> None:
        if isinstance(channel, discord.TextChannel):
            row = await repository.get_panel(channel.guild.id)
            if row and row.channel_id == channel.id:
                await repository.remove_panel(channel.guild.id)

    @commands.guild_only()
    @commands.command(hidden=True, aliases=["si", "server", "sv"])
    @commands.is_owner()
    async def serverinfo(self, ctx: commands.Context) -> None:
        """Xem thông tin server: owner, ngày tạo, avatar, thành viên, ..."""
        guild = ctx.guild
        assert guild is not None
        await ctx.reply(embed=service.build_embed(guild))

    @commands.command(name="serverinfosetup", hidden=True)
    @commands.is_owner()
    async def serverinfosetup(self, ctx: commands.Context) -> None:
        """Gửi panel thông tin server vào kênh hiện tại."""
        guild = ctx.guild
        assert guild is not None
        channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            return await ctx.reply("❌ Lệnh này chỉ dùng trong kênh text.")

        old_row = await repository.get_panel(guild.id)
        if old_row:
            old_channel = guild.get_channel(old_row.channel_id)
            if isinstance(old_channel, discord.TextChannel):
                try:
                    old_msg = await old_channel.fetch_message(old_row.message_id)
                    await old_msg.delete()
                except discord.NotFound, discord.HTTPException:
                    pass
            await repository.remove_panel(guild.id)

        message = await service.post_panel(channel, guild)
        if not message:
            return await ctx.reply("❌ Không gửi được panel (kiểm tra quyền bot).")
        await ctx.reply(
            "✅ Panel thông tin server đã được gửi vào kênh này.", delete_after=5
        )
        try:
            await ctx.message.delete()
        except discord.NotFound, discord.HTTPException:
            pass

    @commands.command(name="serverinfopanelremove", hidden=True)
    @commands.is_owner()
    async def serverinfopanelremove(self, ctx: commands.Context) -> None:
        """Xóa panel thông tin server."""
        guild = ctx.guild
        assert guild is not None
        row = await repository.get_panel(guild.id)
        if not row:
            return await ctx.reply("❌ Server chưa có panel thông tin.")
        channel = guild.get_channel(row.channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                message = await channel.fetch_message(row.message_id)
                await message.delete()
            except discord.NotFound, discord.HTTPException:
                pass
        await repository.remove_panel(guild.id)
        await ctx.reply("✅ Đã xóa panel thông tin server.", delete_after=5)
