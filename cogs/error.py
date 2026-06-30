import traceback

from discord.abc import MISSING
from discord.ext.commands import Cog
from discord import CategoryChannel, ForumChannel, app_commands, Interaction, User, Color, InteractionResponded, NotFound, DiscordException
from loguru import logger

import utils
from utils import CustomBot
from osu import OsuApiException
from unsplash import UnsplashException

class ErrorHandler(Cog):
    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot
        self._old_tree_error = None

    async def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.error_handler

    async def cog_unload(self):
        if self._old_tree_error:
            tree = self.bot.tree
            tree.on_error = self._old_tree_error

    async def error_handler(self, interaction: Interaction[CustomBot], error: app_commands.AppCommandError | Exception):
        error_message = None
        error_title = 'Error while running command!'
        error_view = MISSING

        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        if isinstance(error, app_commands.TransformerError):
            transformer_class = type(error.transformer)
            transformer_name = transformer_class.__name__.replace('Transformer', '')
            error_message = f'Invalid option "{error.value}" for {transformer_name}!'
            error_title = 'Invalid option!'

        if isinstance(error, app_commands.CheckFailure):
            error_title = 'Checks failed!'
            error_message = 'Some checks failed... either you or this bot are missing permissions here.'
            check_names = [c.__qualname__ for c in getattr(interaction.command, 'checks', [])]
            if 'not_user_integration.<locals>.predicate' in check_names and interaction.is_user_integration():
                error_title = 'Invalid install!'
                error_message = 'Can\'t use this command as an user install. Get someone to install me to this server!'

        if isinstance(error, app_commands.MissingPermissions):
            error_message = f'You are missing the following permissions: {error.missing_permissions}'
            error_title = 'Missing Permissions!'

        if isinstance(error, app_commands.BotMissingPermissions):
            error_message = f'The bot is missing the following permissions: {error.missing_permissions}'
            error_title = 'Bot Missing Permissions!'

        if isinstance(error, utils.DoggieBotException):
            error_message = error.description
            error_title = error.title
            if error.view:
                error_view = error.view

        if isinstance(error, (OsuApiException, UnsplashException)):
            error_message = f'Error when doing API lookup! The API may be down, or the searched resource wasn\'t found: {str(error)}'
            error_title = 'API Error!'

        if not error_message:
            error_message = f'An unknown error occurred: {error}\n\nError info will be sent to owner'

            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_t: str = ''.join(lines)

            logger.exception('{}: {}', etype.__name__, error)
            file = utils.str_to_file(traceback_t, filename='traceback.py')

            owner: User = await self.bot.get_owner()

            if owner:
                owner_embed = utils.create_embed(
                    interaction.user,
                    title='Unhandled error occurred!',
                    color=Color.red()
                )

                owner_embed.add_field(
                    name='Unhandled Error!:',
                    value=f"{etype.__name__}: {str(error)[:900]}",
                    inline=False
                )
                owner_embed.add_field(name='Command:', value=str(interaction.data)[:1000], inline=False)

                owner_embed.add_field(
                    name='Extra Info:',
                    value=f'Guild: {interaction.guild}: {getattr(interaction.guild, "id", "None")}\n'
                          f'Channel: {interaction.channel}:{getattr(interaction.channel, "id", None)}', inline=False
                )

                await owner.send(embed=owner_embed, files=[file])

        embed = utils.create_embed(
            interaction.user,
            title=error_title,
            description=error_message[:4000],
            color=Color.brand_red()
        )

        try:
            await interaction.response.send_message(embed=embed, ephemeral=True, view=error_view)
        except (InteractionResponded, NotFound):
            try:
                await interaction.edit_original_response(embed=embed, view=error_view)
            except (InteractionResponded, NotFound):
                if not interaction.channel or isinstance(interaction.channel, (ForumChannel, CategoryChannel)):
                    return
                try:
                    await interaction.channel.send(embed=embed, view=error_view)
                except DiscordException:
                    logger.warning(
                        'Unable to respond to exception in {}',
                        interaction.channel
                    )


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
