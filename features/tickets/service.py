import re
from datetime import datetime

import discord

from features.tickets import repository
from features.tickets.views import (
    AUTO_CLOSE_HOURS,
    GUEST_PERMS,
    MAX_TICKETS_PER_USER,
    WARN_BEFORE_MINUTES,
    _utc_naive,
    TicketCreateView,
)

DELETE_AFTER_MINUTES = AUTO_CLOSE_HOURS * 60
WARN_THRESHOLD_MINUTES = DELETE_AFTER_MINUTES - WARN_BEFORE_MINUTES


async def create_setup_panel(ctx: discord.ext.commands.Context) -> None:
    """Gửi panel tạo ticket vào kênh hiện tại."""
    category = ctx.channel.category
    category_id = category.id if category else None

    embed = discord.Embed(
        title="🎫 Create Ticket",
        description=(
            "Gặp vấn đề hoặc cần hỗ trợ? Bấm nút bên dưới để tạo một ticket riêng tư.\n\n"
            "**Hỗ trợ các vấn đề liên quan đến:.**\n"
            "• Tài khoản CKTOJ, TBCOJ.\n"
            "• Bug liên quan đến CKTOJ, TBCOJ\n"
            "• Lỗi/ Sai testcase, đề bài của TBC.\n"
            "• Khiếu Nại.\n"
            "• Tố cáo.\n"
            "• Góp ý.\n"
            "\n"
            "**Lưu ý:**\n"
            "• Chỉ bạn và Staff/Admin nhìn thấy kênh ticket của bạn.\n"
            "• Mỗi người chỉ được mở **2 ticket** cùng lúc.\n"
            "• Không spam ticket nhằm mục đích phá hoại.\n"
            "• Ticket không hoạt động quá **{hours} giờ** sẽ tự động bị xóa.".format(
                hours=int(AUTO_CLOSE_HOURS)
            )
        ),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="Nhấn nút bên dưới để tạo ticket của bạn.")

    view = TicketCreateView(ctx.bot, category_id)
    message = await ctx.send(embed=embed, view=view)
    await repository.remove_panel(ctx.channel.id)
    await repository.add_panel(ctx.channel.id, ctx.guild.id, message.id, category_id)
    try:
        await ctx.message.delete()
    except (discord.NotFound, discord.HTTPException):
        pass


async def auto_check(bot: discord.ext.commands.Bot) -> None:
    now = datetime.now().astimezone().replace(tzinfo=None)
    for row in await repository.get_all_open():
        channel = bot.get_channel(row.channel_id)
        if not isinstance(channel, discord.TextChannel):
            await repository.remove(row.channel_id)
            continue

        last = _utc_naive(row.last_activity_at)
        idle_minutes = (now - last).total_seconds() / 60

        if idle_minutes >= DELETE_AFTER_MINUTES:
            try:
                await channel.send(
                    "⏰ Ticket này không có phản hồi trong thời gian dài nên sẽ tự động bị xóa."
                )
                await channel.delete(reason="Ticket: tự động xóa do không hoạt động")
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass
            await repository.remove(row.channel_id)
            continue

        if idle_minutes >= WARN_THRESHOLD_MINUTES and not row.warned_at:
            remaining = int(DELETE_AFTER_MINUTES - idle_minutes)
            try:
                await channel.send(
                    f"⚠️ Ticket này không hoạt động. Ticket sẽ tự động bị xóa sau "
                    f"**{remaining} phút** nữa nếu không có phản hồi."
                )
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass
            await repository.set_warned(row.channel_id)