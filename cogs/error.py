import traceback

from discord.abc import MISSING
from discord.ext import commands
from discord import CategoryChannel, Forbidden, ForumChannel, HTTPException, app_commands, Interaction, User, Color, DiscordException
from loguru import logger

import utils
from utils import CustomBot
from utils.classes import CustomContext
from osu import OsuApiException
from unsplash import UnsplashException

class ErrorHandler(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot
        self._old_tree_error = None

    async def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error

    async def cog_unload(self):
        if self._old_tree_error:
            tree = self.bot.tree
            tree.on_error = self._old_tree_error

    def get_error_message(self, ctx_i: CustomContext | Interaction, error) -> dict | None:
        error_message = None
        error_title = 'Error while running command!'
        error_view = MISSING

        while (o_error := getattr(error, 'original', None)):
            error = o_error

        if isinstance(error, commands.NSFWChannelRequired):
            error_title = 'NSFW Only Command!'
            error_message = 'This command can only be used in channels marked as NSFW!'

        if isinstance(error, commands.MissingRequiredArgument):
            error_title = 'Missing arguments!'
            error_message = 'Some required arguments weren\'t passed in, use the help command to see what to pass in!'

        if isinstance(error, commands.NoPrivateMessage):
            error_title = 'Can\'t use this command!'
            error_message = 'This command must be used in a guild!'

        if isinstance(error, commands.EmojiNotFound):
            error_title = 'Emote not found!'
            error_message = 'You can post the emote directly or use its ID'

        if isinstance(error, commands.RoleNotFound):
            error_title = 'Role not found!'
            error_message = 'You can use the role mention, ID, or name!'

        if isinstance(error, commands.BadInviteArgument):
            error_title = 'Invite not found'
            error_message = 'Use the invite URL, or it\'s code!'

        if isinstance(error, commands.BadUnionArgument):
            error_title = 'Bad argument!'
            error_message = 'The given argument didn\'t match any valid values, use the help command to know what to pass in!'

        if isinstance(error, commands.MissingPermissions):
            perms = [str(p).replace('_', ' ').title() for p in error.missing_permissions]

            error_title = 'You don\'t have enough permissions to run that command!'
            error_message = 'You are missing: ' + ', '.join(perms)

        if isinstance(error, commands.BotMissingPermissions):
            perms = [str(p).replace('_', ' ').title() for p in error.missing_permissions]
            error_title = 'The bot doesn\'t have enough permissions!'
            error_message = 'The bot is missing: ' + ', '.join(perms)

        if isinstance(error, (commands.UserNotFound, commands.MemberNotFound)):
            error_title = 'User not found!'
            error_message = 'The bot couldn\'t find that user or member! You should use ID or mention!'

        if isinstance(error, commands.CommandOnCooldown):
            error_title = 'You\'re on cooldown!'
            error_message = str(error)

        if isinstance(error, commands.ChannelNotFound):
            error_title = 'The channel wasn\'t found!'
            error_message = 'You can specify a channel using it\'s name, mention, or ID'

        if isinstance(error, (commands.MessageNotFound, commands.ChannelNotReadable)):
            error_title = 'The message wasn\'t found!'
            error_message = 'You can specify a message using the message link or ID, make sure the bot has permissions to read the message channel too'

        if isinstance(error, commands.MaxConcurrencyReached):
            error_title = 'Too many people using this command!'
            error_message = str(error)

        if isinstance(error, commands.UnexpectedQuoteError):
            error_title = 'Unexpected Quote!'
            error_message = str(error)

        if isinstance(error, commands.InvalidEndOfQuotedStringError):
            error_title = 'Invalid end of quoted string!'
            error_message = str(error)

        if isinstance(error, commands.ExpectedClosingQuoteError):
            error_title = 'Expected closing quote!'
            error_message = str(error)

        if isinstance(error, commands.BadArgument):
            if not error_message:
                error_title = 'Bad argument!'
                error_message = str(error)

        if isinstance(error, app_commands.TransformerError):
            transformer_class = type(error.transformer)
            transformer_name = transformer_class.__name__.replace('Transformer', '')
            error_message = f'Invalid option "{error.value}" for {transformer_name}!'
            error_title = 'Invalid option!'

        if isinstance(error, (app_commands.CheckFailure, commands.CheckFailure)) and not error_message:
            error_title = 'Checks failed!'
            error_message = 'Some checks failed... You can\'t use this command here.'
            check_names = [c.__qualname__ for c in getattr(ctx_i.command, 'checks', [])]
            if 'not_user_integration.<locals>.predicate' in check_names and ctx_i.guild is None:
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
            return None

        embed = utils.create_embed(
            ctx_i.user if isinstance(ctx_i, Interaction) else ctx_i.author,
            title=error_title,
            description=error_message[:4000],
            color=Color.brand_red()
        )

        return {'embed': embed, 'view': error_view}

    @commands.Cog.listener()
    async def on_command_error(self, ctx: utils.CustomContext, error):
        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return
        if ctx.error_handled:
            print('skipping handle')
            return
        error_message = self.get_error_message(ctx, error)
        ctx.error_handled = True
        if not error_message:
            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_t: str = ''.join(lines)

            logger.exception('{}: {}', etype.__name__, error)
            file = utils.str_to_file(traceback_t, filename = 'traceback.py')

            owner: User = await self.bot.get_owner()

            if owner:
                owner_embed = utils.create_embed(
                    ctx.author,
                    title='Unhandled error occurred!',
                    color=Color.red()
                )

                owner_embed.add_field(
                    name='Unhandled Error!:',
                    value=f'{etype.__name__}: {str(error)[:900]}',
                    inline=False
                )
                owner_embed.add_field(name='Command:', value=str(ctx.command)[:1000], inline=False)

                owner_embed.add_field(
                    name='Extra Info:',
                    value=f'Guild: {ctx.guild}: {getattr(ctx.guild, 'id', 'None')}\n'
                          f'Channel: {ctx.channel}:{getattr(ctx.channel, 'id', None)}', inline=False
                )

                await owner.send(embed=owner_embed, files=[file])

                embed = utils.create_embed(
                    ctx.author,
                    title='Unknown Error Occured!',
                    description=f'An unknown error occurred: {error}\n\nError info will be sent to owner'[:4000],
                    color=Color.brand_red()
                )

                error_message = {'embed': embed}

        try:
            await ctx.send(**error_message, ephemeral=True)
        except (Forbidden, HTTPException):
            logger.warning(
                'Unable to respond to exception in {}',
                ctx.channel
            )

    async def on_app_command_error(self, interaction: Interaction, error):
        if interaction.extras.get('error_handled', False):
            return
        error_message = self.get_error_message(interaction, error)
        interaction.extras['error_handled'] = True
        if not error_message:
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
                    value=f'{etype.__name__}: {str(error)[:900]}',
                    inline=False
                )
                owner_embed.add_field(name='Command:', value=str(interaction.command)[:1000], inline=False)

                owner_embed.add_field(
                    name='Extra Info:',
                    value=f'Guild: {interaction.guild}: {getattr(interaction.guild, 'id', 'None')}\n'
                          f'Channel: {interaction.channel}:{getattr(interaction.channel, 'id', None)}', inline=False
                )

                await owner.send(embed=owner_embed, files=[file])

                embed = utils.create_embed(
                    interaction.user,
                    title='Unknown Error Occured!',
                    description=f'An unknown error occurred: {error}\n\nError info will be sent to owner'[:4000],
                    color=Color.brand_red()
                )

                error_message = {'embed': embed}

        try:
            await interaction.response.send_message(ephemeral=True, **error_message)
            return
        except DiscordException:
            pass

        try:
            await interaction.edit_original_response(**error_message)
            return
        except DiscordException:
            pass

        if not isinstance(interaction.channel, (ForumChannel, CategoryChannel)) and interaction.channel:
            try:
                await interaction.channel.send(**error_message)
                return
            except DiscordException:
                pass

        logger.warning(
            'Unable to respond to exception in {}',
            interaction.channel
        )

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
