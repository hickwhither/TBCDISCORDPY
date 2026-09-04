import discord
from discord.ext import commands
from features.antiraid import service


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntiRaid(bot))


class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def mark(self, ctx: commands.Context):
        """Đánh dấu channel anti-raid"""
        await service.mark_channel(ctx)

    @commands.command()
    @commands.is_owner()
    async def unmark(self, ctx: commands.Context):
        """Xóa đánh dấu channel anti-raid"""
        await service.unmark_channel(ctx)

    @commands.command()
    @commands.is_owner()
    async def antilist(self, ctx: commands.Context):
        """List all channels with anti-raid enabled."""
        lines = await service.get_marked_list(self.bot)
        if not lines:
            return await ctx.reply("No channels are currently marked.")

        embed = discord.Embed(
            title="Anti-Raid Channels",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await self.bot.is_owner(message.author):
            return
        await service.check_ban(message)
