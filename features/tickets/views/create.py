import discord
from discord import ButtonStyle, ui

from core.utils import reply_ephemeral
from features.tickets import repository
from features.tickets.views.config import MAX_TICKETS_PER_USER
from features.tickets.views.embed import build_embed
from features.tickets.views.panel import TicketPanelView
from features.tickets.views.permissions import BOT_PERMS, OWNER_PERMS, staff_overwrites


class TicketLimitError(Exception):
    def __init__(self, open_count: int, limit: int) -> None:
        super().__init__(f"Đang mở {open_count}/{limit} ticket")
        self.open_count = open_count
        self.limit = limit


async def unique_ticket_name(guild: discord.Guild) -> str:
    taken = {c.name for c in guild.text_channels}
    number = 1
    while f"ticket-{number}" in taken:
        number += 1
    return f"ticket-{number}"


async def create_ticket(
    guild: discord.Guild, member: discord.Member, category_id: int | None = None
) -> discord.TextChannel:
    existing = await repository.list_open_by_owner(guild.id, member.id)
    if len(existing) >= MAX_TICKETS_PER_USER:
        raise TicketLimitError(len(existing), MAX_TICKETS_PER_USER)

    category = guild.get_channel(category_id) if category_id else None
    if not isinstance(category, discord.CategoryChannel):
        category = None

    name = await unique_ticket_name(guild)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False, send_messages=False, read_message_history=False
        ),
        guild.me: BOT_PERMS,
        member: OWNER_PERMS,
    }
    overwrites.update(await staff_overwrites(guild))

    channel = await guild.create_text_channel(
        name=name,
        category=category,
        overwrites=overwrites,
        reason=f"Ticket: tạo ticket cho {member}",
    )

    embed = build_embed(guild, channel, owner_id=member.id)
    view = TicketPanelView(guild, channel.id)
    panel_message_id = None
    try:
        panel = await channel.send(embed=embed, view=view)
        panel_message_id = panel.id
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(f"[tickets] không gửi được panel: {exc!r}")
    await repository.add(channel.id, guild.id, member.id, panel_message_id)
    return channel


class TicketCreateView(ui.View):
    def __init__(self, bot, category_id: int | None) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.category_id = category_id

    @ui.button(
        label="Tạo Ticket",
        emoji="🎫",
        style=ButtonStyle.primary,
        custom_id="ticket_create",
    )
    async def create(self, interaction: discord.Interaction, _) -> None:
        guild = interaction.guild
        existing = await repository.list_open_by_owner(guild.id, interaction.user.id)
        if len(existing) >= MAX_TICKETS_PER_USER:
            lines = "\n".join(
                (
                    guild.get_channel(t.channel_id).mention
                    if guild.get_channel(t.channel_id)
                    else f"`{t.channel_id}`"
                )
                for t in existing[:MAX_TICKETS_PER_USER]
            )
            text = (
                f"❌ Bạn đang có **{len(existing)} ticket** đang mở (giới hạn tối đa "
                f"**{MAX_TICKETS_PER_USER}**).\n{lines}"
            )
            return await interaction.response.send_message(text, ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        try:
            channel = await create_ticket(guild, interaction.user, self.category_id)
        except TicketLimitError as exc:
            text = (
                f"❌ Bạn đang có **{exc.open_count} ticket** đang mở "
                f"(giới hạn tối đa **{exc.limit}**)."
            )
            return await reply_ephemeral(interaction, text)
        except discord.Forbidden:
            text = "⚠️ Bot không đủ quyền **Manage Channels** để tạo kênh ticket."
            return await reply_ephemeral(interaction, text)
        except discord.HTTPException as exc:
            return await reply_ephemeral(
                interaction, f"⚠️ Không tạo được ticket (lỗi API): {exc}"
            )
        await reply_ephemeral(
            interaction, f"✅ Đã tạo ticket cho bạn: {channel.mention}", delay=8
        )
