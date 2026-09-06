import os

import discord
from discord.ext import commands, tasks

from features.tickets import repository, service
from features.tickets.views import TicketCreateView, TicketMemberPickView, TicketPanelView, is_staff

CHECK_INTERVAL_MINUTES = float(os.environ.get("TICKET_CHECK_INTERVAL_MINUTES", "15"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))

    for row in await repository.get_panels():
        channel = bot.get_channel(row.channel_id)
        if not channel:
            continue
        try:
            await channel.fetch_message(row.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue
        bot.add_view(TicketCreateView(bot, row.category_id), message_id=row.message_id)

    for row in await repository.get_all():
        channel = bot.get_channel(row.channel_id)
        if not channel or not row.panel_message_id:
            continue
        try:
            await channel.fetch_message(row.panel_message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue
        bot.add_view(TicketPanelView(bot, row.channel_id, status=row.status), message_id=row.panel_message_id)


class Tickets(commands.Cog):
    """Hệ thống ticket riêng tư."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.auto_check_task.start()

    def cog_unload(self) -> None:
        self.auto_check_task.cancel()

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            usage = {
                "ticketadd": ".ticketadd <username hoặc ID>",
                "ticketremove": ".ticketremove <username hoặc ID>",
            }.get(ctx.command.name)
            if usage:
                return await ctx.reply(f"❌ Cách dùng: `{usage}`")
        if isinstance(error, commands.BadArgument):
            return await ctx.reply("❌ Tham số không hợp lệ.")
        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.reply("❌ Lệnh này chỉ dùng trong server.")
        raise error from None

    @tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
    async def auto_check_task(self) -> None:
        await service.auto_check(self.bot)

    @auto_check_task.before_loop
    async def _before_auto_check(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        row = await repository.get_by_channel(message.channel.id)
        if not row or row.status != "open":
            return
        if message.author.id == row.owner_id:
            await repository.update_activity(message.channel.id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel) -> None:
        if isinstance(channel, discord.TextChannel):
            await repository.remove(channel.id)
            await repository.remove_panel(channel.id)

    @commands.command(name="ticketsetup")
    @commands.is_owner()
    async def ticketsetup(self, ctx: commands.Context):
        """Gửi panel tạo ticket vào kênh hiện tại."""
        await service.create_setup_panel(ctx)
        await ctx.reply("✅ Panel tạo ticket đã được gửi vào kênh này.", delete_after=5)

    @commands.command(name="ticketlist")
    @commands.guild_only()
    async def ticketlist(self, ctx: commands.Context):
        """Danh sách các ticket đang mở trong server."""
        rows = await repository.get_all()
        lines = []
        for row in rows:
            channel = ctx.guild.get_channel(row.channel_id)
            if not channel:
                continue
            owner = ctx.guild.get_member(row.owner_id)
            status = "🟢 mở" if row.status == "open" else "🔴 đóng"
            lines.append(f"{channel.mention} — {status} — {owner.mention if owner else row.owner_id}")
        if not lines:
            return await ctx.reply("Hiện không có ticket nào.")
        await ctx.reply("\n".join(lines))

    @commands.command(name="ticketadd")
    @commands.guild_only()
    async def ticketadd(self, ctx: commands.Context):
        """Thêm người vào ticket hiện tại (chọn từ danh sách hoặc nhập ID/username)."""
        row = await repository.get_by_channel(ctx.channel.id)
        if not row:
            return await ctx.reply("❌ Lệnh này chỉ dùng trong kênh ticket.")

        if ctx.author.id != row.owner_id and not is_staff(ctx.author):
            return await ctx.reply("❌ Chỉ chủ ticket hoặc Staff/Admin mới được dùng lệnh này.")

        members = sorted(
            (m for m in ctx.guild.members if not m.bot),
            key=lambda m: (m.display_name or m.name).casefold(),
        )
        candidates = [
            m
            for m in members
            if m.id != row.owner_id and not is_staff(m) and ctx.channel.overwrites.get(m) is None
        ]
        prompt = "👇 Chọn thành viên muốn **thêm** vào ticket, hoặc bấm **✍️ Nhập ID/Username**:"
        await ctx.reply(prompt, view=TicketMemberPickView(ctx.channel.id, "add", candidates))

    @commands.command(name="ticketremove")
    @commands.guild_only()
    async def ticketremove(self, ctx: commands.Context):
        """Xóa một người khỏi ticket hiện tại (chọn từ danh sách hoặc nhập ID/username)."""
        row = await repository.get_by_channel(ctx.channel.id)
        if not row:
            return await ctx.reply("❌ Lệnh này chỉ dùng trong kênh ticket.")

        if ctx.author.id != row.owner_id and not is_staff(ctx.author):
            return await ctx.reply("❌ Chỉ chủ ticket hoặc Staff/Admin mới được dùng lệnh này.")

        members = sorted(
            (m for m in ctx.guild.members if not m.bot),
            key=lambda m: (m.display_name or m.name).casefold(),
        )
        candidates = [
            m
            for m in members
            if m.id != row.owner_id and not is_staff(m) and ctx.channel.overwrites.get(m) is not None
        ]
        prompt = "👇 Chọn thành viên muốn **xóa** khỏi ticket, hoặc bấm **✍️ Nhập ID/Username**:"
        await ctx.reply(prompt, view=TicketMemberPickView(ctx.channel.id, "remove", candidates))