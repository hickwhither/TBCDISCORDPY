import discord
from discord.ext import commands, tasks

from features.birthday import repository, service

CHECK_INTERVAL_HOURS = 1


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Birthday(bot))


class Birthday(commands.Cog):
    """🎂 Chúc mừng sinh nhật thành viên trong server."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check_task.start()

    def cog_unload(self) -> None:
        self.check_task.cancel()

    @tasks.loop(hours=CHECK_INTERVAL_HOURS)
    async def check_task(self) -> None:
        await service.run_celebration_check(self.bot)

    @check_task.before_loop
    async def _before_check(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel) -> None:
        if isinstance(channel, discord.TextChannel):
            row = await repository.get_channel(channel.guild.id)
            if row and row.channel_id == channel.id:
                await repository.remove_channel(channel.guild.id)

    @commands.command(name="birthday", aliases=["sinhnhat"])
    async def birthday(
        self, ctx: commands.Context, action: str = "view", *, value: str = ""
    ) -> None:
        """Xem, đặt hoặc xóa ngày sinh nhật của bạn."""
        action = action.casefold()
        if action == "set":
            return await self._set_birthday(ctx, value)
        if action == "remove":
            return await self._remove_birthday(ctx)
        if action != "view":
            return await ctx.reply(
                "❌ Hành động không hợp lệ. Dùng `set`, `remove` hoặc bỏ trống."
            )
        return await self._show_birthday(ctx)

    async def _set_birthday(self, ctx: commands.Context, value: str) -> None:
        if not value:
            return await ctx.reply("❌ Cách dùng: `birthday set DD/MM/YYYY`")
        birth_date = service.parse_date(value)
        if birth_date is None:
            return await ctx.reply(
                "❌ Ngày sinh không hợp lệ. Dùng định dạng `DD/MM/YYYY`."
            )
        if birth_date > service.today():
            return await ctx.reply("❌ Ngày sinh không thể nằm trong tương lai.")

        await repository.set_birthday(ctx.author.id, birth_date)
        embed = discord.Embed(
            title="🎂 Đã lưu sinh nhật!",
            description=(
                f"Ngày sinh của bạn: **{birth_date.strftime('%d/%m/%Y')}**\n"
                "Bot sẽ chúc mừng bạn trong các server có đặt kênh sinh nhật."
            ),
            color=discord.Color.green(),
        )
        await ctx.reply(embed=embed)

    async def _remove_birthday(self, ctx: commands.Context) -> None:
        row = await repository.remove_birthday(ctx.author.id)
        if not row:
            return await ctx.reply("Bạn chưa đặt ngày sinh nhật.")
        await ctx.reply("✅ Đã xóa ngày sinh nhật của bạn.")

    async def _show_birthday(self, ctx: commands.Context) -> None:
        row = await repository.get_birthday(ctx.author.id)
        if not row:
            return await ctx.reply(
                "Bạn chưa đặt ngày sinh nhật. Dùng `birthday set DD/MM/YYYY`."
            )
        embed = discord.Embed(title="🎂 Sinh nhật của bạn", color=discord.Color.pink())
        embed.add_field(
            name="Ngày sinh",
            value=f"**{row.birth_date.strftime('%d/%m/%Y')}**",
            inline=True,
        )
        await ctx.reply(embed=embed)

    @commands.guild_only()
    @commands.command(name="birthdaysetup")
    @commands.has_permissions(administrator=True)
    async def birthdaysetup(self, ctx: commands.Context) -> None:
        """(Admin) Đặt kênh hiện tại làm nơi chúc mừng sinh nhật."""
        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.reply("❌ Lệnh này chỉ dùng trong kênh text.")
        await repository.set_channel(ctx.guild.id, ctx.channel.id)
        await ctx.reply(
            "✅ Đã đặt kênh này làm nơi chúc mừng sinh nhật.",
            delete_after=5,
        )

    @commands.guild_only()
    @commands.command(name="birthdaychannel")
    @commands.has_permissions(administrator=True)
    async def birthdaychannel(self, ctx: commands.Context) -> None:
        """(Admin) Xem kênh chúc mừng sinh nhật của server."""
        row = await repository.get_channel(ctx.guild.id)
        if not row:
            return await ctx.reply("Server chưa đặt kênh chúc mừng sinh nhật.")
        channel = ctx.guild.get_channel(row.channel_id)
        mention = channel.mention if channel else str(row.channel_id)
        await ctx.reply(f"🎂 Kênh chúc mừng sinh nhật: {mention}")

    @commands.guild_only()
    @commands.command(name="birthdaychannelremove")
    @commands.has_permissions(administrator=True)
    async def birthdaychannelremove(self, ctx: commands.Context) -> None:
        """(Admin) Xóa kênh chúc mừng sinh nhật của server."""
        row = await repository.remove_channel(ctx.guild.id)
        if not row:
            return await ctx.reply("Server chưa đặt kênh chúc mừng sinh nhật.")
        await ctx.reply("✅ Đã xóa kênh chúc mừng sinh nhật.", delete_after=5)
