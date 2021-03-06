import discord
import utils

from discord.ext import commands, menus


def format_first_message(ctx):
    embed = utils.create_embed(
        ctx.author,
        title='Help for this bot:',
        description='Thank you for using this bot! This is a multipurpose bot with moderation, logging, utility and '
                    'image commands!\n'
    )

    embed.add_field(
        name='How to use this bot:',
        value=f'Use `@{ctx.bot.user} command` to use a command, most commands also need you to put an argument after '
              f'the command, such as `@{ctx.bot.user} user {ctx.bot.user}`\n'
              f'You will know which arguments to put in a command by looking at it\'s command signature!\n'
              f'```py\n'
              f'<user> - User is a required argument\n'
              f'[user] - User is an optional argument\n'
              f'<users...> - You can specify more than one user\n'
              f'[amount=100] - Amount is optional, and 100 is the default\n'
              f'̶c̶o̶m̶m̶a̶n̶d - You can\'t run this command\n'
              f'```'
    )

    for cog in ctx.bot.cogs.values():
        if not any([command.hidden for command in cog.get_commands()]) and cog.get_commands():
            embed.add_field(name=cog.qualified_name, value=cog.description or 'No description', inline=False)

    return embed


class HelpPageSource(menus.ListPageSource):
    def __init__(self, source, help_instance):
        self.help: CustomHelp = help_instance
        super().__init__(source, per_page=1)

    async def format_page(self, menu, cog: commands.Cog):
        if isinstance(cog, discord.Embed):
            return cog

        index = menu.current_page

        embed = await self.help.get_cog_embed(
            cog,
            title=f'Showing {cog.qualified_name.lower()} commands ({index}/{self._max_pages - 1}):'
        )

        return embed


class CustomHelp(commands.HelpCommand):
    async def strikethrough_if_invalid(self, command: commands.Command):
        try:
            if await command.can_run(self.context):
                return self.get_command_signature(command)
        except commands.CommandError:
            pass

        return f'~~{self.get_command_signature(command)}~~'

    def get_command_signature(self, command):
        if not command.signature:
            return command.qualified_name

        return f'{command.qualified_name} - {command.signature}'

    async def prepare_help_command(self, ctx, command=None):
        if not self.cog:
            self.cog = ctx.bot.get_cog('Misc')

    async def send_command_help(self, command):
        command_help = command.help or 'No help set'
        embed = utils.create_embed(
            self.context.author,
            title=f'Showing help for "{command}":',
            description=f'**Signature:** {command.signature}\n\n'
                        f'{command_help}'
        )

        if command.aliases:
            embed.add_field(name='Aliases:', value=', '.join(command.aliases))

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = utils.create_embed(
            self.context.author,
            title=f'Showing help for {group} commands:',
            description='**Subcommands:**'
        )

        for subcommand in group.commands:
            embed.add_field(
                name=subcommand.name,
                value=subcommand.help or 'No description',
                inline=False
            )

        await self.get_destination().send(embed=embed)

    async def send_bot_help(self, mapping):
        source = list(self.context.bot.cogs.values())
        source = [c for c in source if not any([command.hidden for command in c.get_commands()]) if c.get_commands()]
        source[:0] = [format_first_message(self.context)]

        pages = utils.CustomMenu(source=HelpPageSource(source, self), clear_reactions_after=True)
        await pages.start(self.context)

    async def send_cog_help(self, cog):
        embed = await self.get_cog_embed(cog)
        await self.get_destination().send(embed=embed)

    async def command_not_found(self, string):
        embed = utils.create_embed(
            self.context.author,
            title='Command not found!',
            description=f'No command called "{string}" was found, use the `help` command to see all commands!',
            color=discord.Color.red()
        )

        await self.get_destination().send(embed=embed)

    async def subcommand_not_found(self, command, string):
        embed = utils.create_embed(
            self.context.author,
            title='Subcommand not found!',
            description=f'{command.name} doesn\'t have a subcommand named "{string}", '
                        f'you can do `help {command.name}` to see all of its subcommands!',
            color=discord.Color.red()
        )

        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error):
        pass

    async def get_cog_embed(self, cog: commands.Cog, title=None) -> discord.Embed:
        embed = utils.create_embed(
            self.context.author,
            title=title or f'Showing {cog.qualified_name.lower()} commands:',
            description=cog.description
        )

        for command in cog.get_commands():

            if command.short_doc:
                embed.add_field(
                    name=await self.strikethrough_if_invalid(command),
                    value=command.short_doc,
                    inline=False
                )

            if isinstance(command, commands.Group):
                for subcommand in command.commands:
                    embed.add_field(
                        name=await self.strikethrough_if_invalid(subcommand),
                        value=subcommand.short_doc,
                        inline=False
                    )

        return embed
