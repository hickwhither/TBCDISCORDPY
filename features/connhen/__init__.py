import discord
from discord.ext import commands

from . import service


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Connhen(bot))


class Connhen(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(aliases=["wallet", "money", "balance", "bal"])
    async def connhen(
        self, ctx: commands.Context, member: discord.Member | None = None
    ):
        """Xem ví connhen của bạn (hoặc người khác)."""
        member = member or ctx.author
        amount = await service.balance(member.id)

        embed = discord.Embed(
            title=f"Ví của {member.display_name}",
            description=f"**{service.format_amount(amount)}**",
            color=discord.Color.gold(),
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def daily(self, ctx: commands.Context):
        """Nhận connhen miễn phí mỗi 24 giờ."""
        result = await service.daily(ctx.author.id)

        if result.claimed:
            embed = discord.Embed(
                title="Nhận daily thành công!",
                description=f"+ **{service.format_amount(result.amount)}**",
                color=discord.Color.green(),
            )
        else:
            remaining = int(result.cooldown_remaining.total_seconds())
            hours, rem = divmod(remaining, 3600)
            minutes, _ = divmod(rem, 60)
            embed = discord.Embed(
                title="Chưa được nhận!",
                description=f"Hãy quay lại sau **{hours}h {minutes}m**.",
                color=discord.Color.red(),
            )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["bet"])
    async def gamble(self, ctx: commands.Context, amount: str = "all"):
        """Đặt cược connhen (coinfly x2). Dùng 'all' để chơi hết ví."""
        if amount.lower() == "all":
            stake = await service.balance(ctx.author.id)
        else:
            if not amount.isdigit():
                return await ctx.reply(
                    "Sai cú pháp. Ví dụ: `!gamble 50` hoặc `!gamble all`."
                )
            stake = int(amount)

        if stake <= 0:
            return await ctx.reply("Tiền cược phải lớn hơn 0.")

        if stake > await service.balance(ctx.author.id):
            return await ctx.reply("Bạn không đủ connhen để cược.")

        result = await service.gamble(ctx.author.id, stake)

        if result.win:
            embed = discord.Embed(
                title="🎉 BẠN THẮNG!",
                description=f"Cược **{service.format_amount(result.stake)}** -> +**{service.format_amount(result.stake)}**\n"
                f"Số dư: **{service.format_amount(result.new_balance)}**",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="💀 BẠN THUA!",
                description=f"Mất **{service.format_amount(result.stake)}**.\n"
                f"Số dư: **{service.format_amount(result.new_balance)}**",
                color=discord.Color.red(),
            )
        await ctx.reply(embed=embed)

    @commands.command()
    async def pay(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Chuyển connhen cho người khác. Ví dụ: !pay @user 50"""
        if member.bot:
            return await ctx.reply("Không thể chuyển tiền cho bot.")

        result = await service.pay(ctx.author.id, member.id, amount)

        if result is service.PayError.OK:
            embed = discord.Embed(
                title="Chuyển tiền thành công!",
                description=f"Đã chuyển **{service.format_amount(amount)}** cho {member.mention}.",
                color=discord.Color.green(),
            )
        elif result is service.PayError.SELF:
            embed = discord.Embed(
                title="Không thể chuyển cho chính mình!",
                color=discord.Color.red(),
            )
        elif result is service.PayError.INSUFFICIENT:
            embed = discord.Embed(
                title="Không đủ connhen!",
                description=f"Bạn chỉ có **{service.format_amount(await service.balance(ctx.author.id))}**.",
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title="Số tiền không hợp lệ!",
                description="Số tiền phải lớn hơn 0.",
                color=discord.Color.red(),
            )
        await ctx.reply(embed=embed)
