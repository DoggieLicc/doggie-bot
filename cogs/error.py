import traceback

import discord
from discord.ext import commands

from utils import CustomBot, CustomContext, create_embed, str_to_file


class ErrorHandler(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: CustomContext, error):
        if ctx.command and ctx.command.has_error_handler():
            return

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return

        embed = create_embed(ctx.author, title='Error while running command!', color=discord.Color.red())

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
            embed.add_field(
                name='You don\'t have enough permissions to run that command!',
                value='You are missing: ' + ', '.join(error.missing_permissions)
            )

        if isinstance(error, commands.BotMissingPermissions):
            embed.add_field(
                name='The bot doesn\'t have enough permissions!',
                value='The bot is missing: ' + ', '.join(error.missing_permissions)
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
                name='YOu\'re on cooldown!',
                value=str(error)
            )

        if embed.fields:
            return await ctx.send(embed=embed)

        etype = type(error)
        trace = error.__traceback__
        lines = traceback.format_exception(etype, error, trace)
        traceback_t: str = ''.join(lines)

        file = str_to_file(traceback_t, filename='traceback.py')

        owner: discord.User = await self.bot.get_owner()

        embed.add_field(name="Unhandled Error!:", value=f"{error}", inline=False)
        embed.add_field(name="Message content:", value=ctx.message.content, inline=False)
        embed.add_field(name="Extra Info:", value=f"Guild: {ctx.guild}: {ctx.guild.id if ctx.guild else 'None'}\n"
                                                  f"Channel: {ctx.channel}:", inline=False)

        await owner.send(file=file, embed=embed)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
