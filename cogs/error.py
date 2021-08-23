import traceback

import discord
from discord.ext import commands

import utils


class ErrorHandler(commands.Cog):
    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: utils.CustomContext, error):
        if ctx.command and ctx.command.has_error_handler():
            return

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return

        embed = utils.create_embed(ctx.author, title='Error while running command!', color=discord.Color.red())

        if isinstance(error, commands.MissingRequiredArgument):
            embed.add_field(
                name='Missing arguments!',
                value='Some required arguments weren\'t passed in, use the help command to see what to pass in!'
            )

        if isinstance(error, commands.NoPrivateMessage):
            embed.add_field(
                name='Can\'t use this command!',
                value='This command must be used in a guild!'
            )

        if isinstance(error, commands.EmojiNotFound):
            embed.add_field(
                name='Emote not found!',
                value='You can post the emote directly or use its ID'
            )

        if isinstance(error, commands.RoleNotFound):
            embed.add_field(
                name='Role not found!',
                value='You can use the role mention, ID, or name!'
            )

        if isinstance(error, commands.BadInviteArgument):
            embed.add_field(
                name='Invite not found',
                value='Use the invite URL, or it\'s code!'
            )

        if isinstance(error, commands.NotOwner):
            embed.add_field(
                name='You\'re on cooldown!',
                value=str(error)
            )

        if isinstance(error, commands.BadUnionArgument):
            embed.add_field(
                name='Bad argument!',
                value='The given argument didn\'t match any valid values, use the help command to know what to pass in!'
            )

        if isinstance(error, commands.MissingPermissions):
            perms = [str(p).replace('_', ' ').title() for p in error.missing_permissions]

            embed.add_field(
                name='You don\'t have enough permissions to run that command!',
                value='You are missing: ' + ', '.join(perms)
            )

        if isinstance(error, commands.BotMissingPermissions):
            perms = [str(p).replace('_', ' ').title() for p in error.missing_permissions]
            embed.add_field(
                name='The bot doesn\'t have enough permissions!',
                value='The bot is missing: ' + ', '.join(perms)
            )

        if isinstance(error, commands.TooManyFlags):
            embed.add_field(
                name='Duplicate flags!',
                value='You duplicated a flag that wasn\'t meant to be duplicated!'
            )

        if isinstance(error, (commands.BadFlagArgument, commands.MissingFlagArgument)):
            embed.add_field(
                name='Flag argument is wrong or missing!',
                value='Use the help command to know what to pass in!'
            )

        if isinstance(error, (commands.UserNotFound, commands.MemberNotFound)):
            embed.add_field(
                name='User not found!',
                value='The bot couldn\'t find that user or member! You should use ID or mention!'
            )

        if isinstance(error, commands.CommandOnCooldown):
            embed.add_field(
                name='You\'re on cooldown!',
                value=str(error)
            )

        if isinstance(error, commands.ChannelNotFound):
            embed.add_field(
                name='The channel wasn\'t found!',
                value='You can specify a channel using it\'s name, mention, or ID'
            )

        if isinstance(error, (commands.MessageNotFound, commands.ChannelNotReadable)):
            embed.add_field(
                name='The message wasn\'t found!',
                value='You can specify a message using the message link or ID, make sure the bot has permissions to '
                      'read the message channel too'
            )

        if embed.fields:
            embed.add_field(
                name='Help:',
                value='If you need help, you can use the `help` command, or join the '
                      '[**support server**](https://discord.gg/Uk6fg39cWn).',
                inline=False
            )

            try:
                return await ctx.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                return

        etype = type(error)
        trace = error.__traceback__
        lines = traceback.format_exception(etype, error, trace)
        traceback_t: str = ''.join(lines)

        file = utils.str_to_file(traceback_t, filename='traceback.py')

        owner: discord.User = await self.bot.get_owner()

        embed.add_field(name="Unhandled Error!:", value=f"{error}", inline=False)
        embed.add_field(name="Message content:", value=ctx.message.content, inline=False)

        embed.add_field(
            name="Extra Info:",
            value=f"Guild: {ctx.guild}: {ctx.guild.id if ctx.guild else 'None'}\n"
                  f"Channel: {ctx.channel}:", inline=False
        )

        await owner.send(file=file, embed=embed)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
