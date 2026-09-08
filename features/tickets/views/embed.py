from datetime import datetime, timezone

import discord

from features.tickets.views.config import AUTO_CLOSE_HOURS


def utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def dt_to_unix(dt: datetime) -> int:
    return int(utc_naive(dt).replace(tzinfo=timezone.utc).timestamp())


def build_embed(
    guild: discord.Guild,
    channel: discord.TextChannel,
    *,
    owner_id: int,
    status: str = "open",
    created_at: datetime | None = None,
) -> discord.Embed:
    owner = guild.get_member(owner_id)
    status_text = "🟢 Đang mở" if status == "open" else "🔴 Đã đóng"
    opened = f"<t:{dt_to_unix(created_at)}:R>" if created_at else "vừa mới"

    embed = discord.Embed(
        title=f"🎫 {channel.name}",
        description=(
            "**Hướng dẫn sử dụng:**\n"
            "• Mô tả rõ vấn đề/báo cáo của bạn ở bên dưới.\n"
            "• Đội ngũ hỗ trợ sẽ phản hồi trong ticket này.\n"
            "• Hãy tôn trọng, cẩn thận lời nói của nhau.\n"
            "• Bấm **🔒 Đóng Ticket** khi xong việc.\n"
            "• Bấm **🗑 Xóa Ticket** để xóa kênh (sẽ xác nhận lại).\n"
            f"• Ticket không hoạt động quá **{int(AUTO_CLOSE_HOURS)} giờ** sẽ tự động bị xóa."
        ),
        color=discord.Color.green() if status == "open" else discord.Color.red(),
    )
    embed.add_field(
        name="👤 Chủ ticket",
        value=owner.mention if owner else f"`{owner_id}`",
        inline=True,
    )
    embed.add_field(name="📌 Trạng thái", value=status_text, inline=True)
    embed.add_field(name="📅 Mở lúc", value=opened, inline=True)
    embed.add_field(name="🔗 Kênh", value=channel.mention, inline=True)
    embed.set_footer(text=f"ID ticket: {channel.id}")
    return embed
