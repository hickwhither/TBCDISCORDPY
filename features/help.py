import discord
from discord.ext import commands


class CustomHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Show the help menu or info about a command/category.',
            'aliases': ['h']
        })

    async def send_bot_help(self, mapping):
        prefix = self.context.prefix
        embed = discord.Embed(
            title='Help Menu',
            color=discord.Color.blurple()
        )

        for cog, cmds in mapping.items():
            cmds.sort(key=lambda c: c.name)
            cmd_list = '\n'.join(
                f'`{prefix}{c.name}` — {c.short_doc or "No description"}'
                for c in cmds
            )
            embed.add_field(name=cog.qualified_name if cog else "Misc", value=cmd_list, inline=False)

        embed.set_footer(text=f'Type "{prefix}help <command>" for more info.')
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=cog.qualified_name,
            description=cog.description or 'No description.',
            color=discord.Color.green()
        )

        lines = []
        for cmd in cog.walk_commands():
            sig = self.get_command_signature(cmd)
            lines.append(f'`{sig}` — {cmd.short_doc or "No description"}')
        embed.add_field(name='Commands', value='\n'.join(lines), inline=False)

        embed.set_footer(text=f'Type "{self.context.prefix}help <command>" for more info.')
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        prefix = self.context.prefix
        embed = discord.Embed(
            title=self.get_command_signature(command),
            description=command.help or command.short_doc or 'No description.',
            color=discord.Color.blue()
        )

        if command.aliases:
            embed.add_field(
                name='Aliases',
                value=', '.join(f'`{a}`' for a in command.aliases),
                inline=False
            )

        usage = self.get_command_signature(command)
        embed.add_field(name='Usage', value=f'`{usage}`', inline=False)

        await self.get_destination().send(embed=embed)

    def command_not_found(self, string):
        if self.get_cog(string):
            return string
        return f'Command `{string}` not found.'


async def setup(bot: commands.Bot) -> None:
    bot.help_command = CustomHelp()
