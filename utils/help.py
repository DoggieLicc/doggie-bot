from discord.ext import commands
from utils.funcs import create_embed

class CustomHelp(commands.HelpCommand):
    # pylint: disable=arguments-differ,invalid-overridden-method

    async def send_generic_message(self):
        embed = create_embed(
            self.context.author,
            title='Migrated to slash commands!',
            description='This bot has been updated to use Discord\'s slash commands'
        )

        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        await self.send_generic_message()

    async def send_group_help(self, group):
        await self.send_generic_message()

    async def send_bot_help(self, mapping):
        await self.send_generic_message()

    async def send_cog_help(self, cog):
        await self.send_generic_message()

    async def command_not_found(self, string):
        await self.send_generic_message()

    async def subcommand_not_found(self, command, string):
        await self.send_generic_message()

    async def send_error_message(self, error):
        pass
