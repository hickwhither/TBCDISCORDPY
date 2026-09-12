import discord
from discord.ext import commands

from features.serverlog import service


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerLog(bot))


class ServerLog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if before.guild is None:
            return
        await service.log_nickname_change(self.bot, before, after)
        await service.log_username_change(self.bot, before, after)
        await service.log_avatar_change(self.bot, before, after)
        await service.log_role_change(self.bot, before, after)
        await service.log_boost_change(self.bot, before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        await service.log_message_delete(self.bot, message)

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        await service.log_message_edit(self.bot, before, after)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages) -> None:
        await service.log_bulk_delete(self.bot, messages)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await service.log_member_join(self.bot, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await service.log_member_remove(self.bot, member)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        await service.log_member_ban(self.bot, guild, user)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        await service.log_member_unban(self.bot, guild, user)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        await service.log_audit_entry(self.bot, entry)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        await service.log_channel_create(self.bot, channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        await service.log_channel_delete(self.bot, channel)

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ) -> None:
        await service.log_channel_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        await service.log_role_create(self.bot, role)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await service.log_role_delete(self.bot, role)

    @commands.Cog.listener()
    async def on_guild_role_update(
        self, before: discord.Role, after: discord.Role
    ) -> None:
        await service.log_role_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_guild_update(
        self, before: discord.Guild, after: discord.Guild
    ) -> None:
        await service.log_guild_update(self.bot, before, after)
