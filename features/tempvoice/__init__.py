import discord
from discord.ext import commands

from features.tempvoice import repository, service
from features.tempvoice.views import ControlPanelView, refresh_panel


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))
    for row in await repository.get_all_tempvoice():
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
                await after.channel.send(f"⚠️ Không thể tạo phòng voice (lỗi API): {exc}")
            except Exception as exc:
                print(f"[tempvoice] create_room error: {exc!r}")

            return

        if before.channel:
            row = await repository.get_tempvoice(before.channel.id)
            if not row:
                return
            await refresh_panel(before.channel)
            if not before.channel.members:
                await service.delete_room(before.channel)

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
            return await ctx.reply(f"✅ Kênh này đã được setup trigger.", delete_after=5)
        await repository.create_createvoice(ctx.channel.id, ctx.guild.id)
        await ctx.reply(f"✅ Kênh này đã được setup trigger. Ai bấm vào sẽ được tạo phòng riêng.")
        await ctx.message.delete()

