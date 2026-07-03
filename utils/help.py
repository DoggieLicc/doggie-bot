import discord
from discord.ext import commands

import utils
from utils.menus import EntryMenu


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
              f'```\n'
              f'**This bot also supports slash commands, type `/` to view available commands**'
    )

    for cog in ctx.bot.cogs.values():
        if not any(command.hidden for command in cog.get_commands()) and cog.get_commands():
            embed.add_field(name=cog.qualified_name, value=cog.description or 'No description', inline=False)

    return embed


class HelpPageView(EntryMenu):
    def __init__(self, owner, items: list[commands.Cog | discord.Embed], help_instance: 'CustomHelp'):
        self.help: CustomHelp = help_instance
        super().__init__(owner, items, 1)
        self.cogs: list[commands.Cog] = [c for c in items if not isinstance(c, discord.Embed)]
        options = []
        category_counts = help_instance.category_counts
        for cog in self.cogs:
            options.append(
                discord.SelectOption(
                    label=f'{cog.qualified_name} - {category_counts[cog]} commands',
                    value=cog.qualified_name
                )
            )

        select = discord.ui.Select(
            custom_id=f'{help_instance.context.message.id}:help',
            placeholder='Select Category: ',
            options=options,
            row=-1
        )
        select.interaction_check = self.interaction_check
        select.callback = self.category_select_callback
        self.add_item(select)

    async def category_select_callback(self, interaction: discord.Interaction):
        select = [c for c in self.children if isinstance(c, discord.ui.Select)][0]
        option = select.values[0]
        selected_category: commands.Cog = [c for c in self.cogs if c.qualified_name == option][0]
        category_index = [i for i, val in enumerate(self.cogs) if val == selected_category][0]

        self.current_index = category_index + 2
        await self.update_page(interaction)

    async def get_page_contents(self):
        entry = self.get_page_items()[0]
        if isinstance(entry, discord.Embed):
            return {'embed': entry}

        embed = await self.help.get_cog_embed(
            entry,
            title=f'Showing {entry.qualified_name.lower()} commands ({self.current_index}/{self.max_page}):'
        )

        return {'embed': embed}


class CustomHelp(commands.HelpCommand):
    cached_category_counts: dict[commands.Cog, int] = {}

    # pylint: disable=arguments-differ,invalid-overridden-method
    async def strikethrough_if_invalid(self, command: commands.Command):
        try:
            for parent in command.parents:
                if not await parent.can_run(self.context):
                    return f'~~{self.get_command_signature(command)}~~'

            if not await command.can_run(self.context):
                return f'~~{self.get_command_signature(command)}~~'
        except commands.CommandError:
            return f'~~{self.get_command_signature(command)}~~'

        return self.get_command_signature(command)

    def get_command_signature(self, command):
        if not command.signature:
            return command.qualified_name

        return f'{command.qualified_name} - {command.signature}'

    async def send(self, *args, **kwargs):
        if not self.context.interaction:
            await self.get_destination().send(*args, **kwargs)
            return

        try:
            await self.context.send(*args, **kwargs, ephemeral=True)
        except discord.InteractionResponded:
            await self.context.interaction.edit_original_response(*args, **kwargs)
        except discord.NotFound:
            if self.context.interaction.app_permissions.send_messages:
                await self.get_destination().send(*args, **kwargs)


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

        await self.send(embed=embed)

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

        await self.send(embed=embed)

    async def send_bot_help(self, mapping):
        source = list(self.context.bot.cogs.values())
        source = [c for c in source if not any(command.hidden for command in c.get_commands()) if c.get_commands()]
        source[:0] = [format_first_message(self.context)]

        view = HelpPageView(self.context.author, source, self)
        await self.send(view=view, embed=format_first_message(self.context))

    async def send_cog_help(self, cog):
        embed = await self.get_cog_embed(cog)
        await self.send(embed=embed)

    async def command_not_found(self, string):
        embed = utils.create_embed(
            self.context.author,
            title='Command not found!',
            description=f'No command called "{string}" was found, use the `help` command to see all commands!',
            color=discord.Color.red()
        )

        await self.send(embed=embed)

    async def subcommand_not_found(self, command, string):
        embed = utils.create_embed(
            self.context.author,
            title='Subcommand not found!',
            description=f'{command.name} doesn\'t have a subcommand named "{string}", '
                        f'you can do `help {command.name}` to see all of its subcommands!',
            color=discord.Color.red()
        )

        await self.send(embed=embed)

    async def send_error_message(self, error):
        pass

    @property
    def category_counts(self) -> dict[commands.Cog, int]:
        if CustomHelp.cached_category_counts:
            return CustomHelp.cached_category_counts

        category_count = {}
        for cog in self.context.bot.cogs.values():
            cog_count = sum(1 for c in cog.walk_commands() if isinstance(c, (commands.Command, commands.HybridCommand)))
            category_count[cog] = cog_count

        CustomHelp.cached_category_counts = category_count
        return category_count

    async def get_cog_embed(self, cog: commands.Cog, title=None) -> discord.Embed:
        embed = utils.create_embed(
            self.context.author,
            title=title or f'Showing {cog.qualified_name.lower()} commands:',
            description=cog.description
        )

        for command in cog.get_commands():
            if isinstance(command, (commands.Group, commands.HybridGroup)):
                for subcommand in command.commands:
                    if isinstance(subcommand, (commands.Group, commands.HybridGroup)):
                        for subsubcommand in subcommand.commands:
                            embed.add_field(
                                name=await self.strikethrough_if_invalid(subsubcommand),
                                value=subsubcommand.short_doc,
                                inline=False
                        )
                    elif subcommand.short_doc:
                        embed.add_field(
                            name=await self.strikethrough_if_invalid(subcommand),
                            value=subcommand.short_doc,
                            inline=False
                        )
            elif command.short_doc:
                embed.add_field(
                    name=await self.strikethrough_if_invalid(command),
                    value=command.short_doc,
                    inline=False
                )

        return embed
