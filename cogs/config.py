import discord

from discord.ext import commands

from typing import Optional, Union

from utils import CustomBot, CustomContext, create_embed

T = Optional[Union[discord.TextChannel, bool]]


class LoggingConverter(commands.FlagConverter):
    kick_channel: T = commands.flag(aliases=['kick', 'kickchannel'])
    ban_channel: T = commands.flag(aliases=['ban', 'banchannel'])
    purge_channel: T = commands.flag(aliases=['purge', 'purgechannel'])
    delete_channel: T = commands.flag(aliases=['delete', 'deletechannel'])
    mute_channel: T = commands.flag(aliases=['mute', 'mutechannel'])


class Configuration(commands.Cog):
    """Set the configuration for this server, you need the "Manage Server" permission to edit the configuration!"""

    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    async def cog_check(self, ctx: CustomContext):
        if not ctx.guild:
            raise commands.NoPrivateMessage()

        if ctx.author.guild_permissions.manage_guild:
            return True

        else:
            raise commands.MissingPermissions(['manage_guild'])

    @commands.group(invoke_without_command=True)
    async def config(self, ctx: CustomContext):
        """Shows the current configuration for this server!"""

        basic_config = ctx.basic_config
        logging_config = ctx.logging_config
        
        def maybe_mention(channel): return channel.mention if channel else "Not set"

        embed = create_embed(
            ctx.author,
            title='Showing current guild configuration:',
            description=f'**Guild:** {basic_config.guild} ({basic_config.guild.id})\n'
                        f'**Prefix:** "{basic_config.prefix or "doggie."}" and {ctx.me.mention}\n'
                        f'**Mute role:** {maybe_mention(basic_config.mute_role)}\n'
                        f'**Snipe command:** {"Enabled" if basic_config.snipe else "Disabled"}')

        embed.add_field(
            name='Logging configuration:',
            value=f'**Ban channel:** {maybe_mention(logging_config.ban_channel)}\n'
                  f'**Kick channel:** {maybe_mention(logging_config.kick_channel)}\n'
                  f'**Deleted messages channel:** {maybe_mention(logging_config.delete_channel)}\n'
                  f'**Mute channel:** {maybe_mention(logging_config.mute_channel)}\n'
                  f'**Purge channel:** {maybe_mention(logging_config.purge_channel)}'
        )

        await ctx.send(embed=embed)

    @config.command()
    async def prefix(self, ctx: CustomContext, *, prefix: str):
        """Sets a custom prefix for the current guild!"""

        if len(prefix) > 100:
            embed = create_embed(ctx.author,
                                 title='Prefix too long!',
                                 description='The prefix can\'t be longer than 100 characters!',
                                 color=discord.Color.red())

            return await ctx.send(embed=embed)

        await ctx.basic_config.set_config(self.bot, prefix=prefix)

        embed = create_embed(
            ctx.author,
            title='Prefix has been set!',
            description=f'The prefix has been set to "{prefix}" (You can still use the bot\'s mention as the prefix!)'
        )

        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @config.command(aliases=['mute', 'muterole'])
    async def mute_role(self, ctx: CustomContext, role: discord.Role):
        """Sets a role that will be given to members when the `mute` command is used!"""

        if not role.is_assignable():
            embed = create_embed(
                ctx.author,
                title='Invalid role!',
                description=f'The bot won\'t be able to manage that role, either it\'s higher than this bot\'s highest '
                            f'role, is the {ctx.guild.default_role} role, is a bot or integration specific role, '
                            f'or is the Nitro Booster role, or the bot is missing the "Manage Roles" permission.',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        await ctx.basic_config.set_config(self.bot, mute_role=role)

        embed = create_embed(
            ctx.author,
            title='Mute role has been set!',
            description=f'The mute role has been set to {role.mention}, this will be the role given to members when '
                        f'the `mute` command is used on them!'
        )

        await ctx.send(embed=embed)

    @config.command()
    async def snipe(self, ctx: CustomContext, option: bool):
        """Enables or disables the `snipe` command!"""

        await ctx.basic_config.set_config(self.bot, snipe=option)

        embed = create_embed(ctx.author, title="Snipe command " + ("enabled!" if option else "disabled!"),
                             description=f"The snipe feature has been " + ("enabled!" if option else "disabled!") +
                                         f" This will " + ("enable" if option else "disable") + " the `snipe` command!")

        if not option:
            self.bot.sniped = [msg for msg in self.bot.sniped if not msg.guild == ctx.guild]

        await ctx.send(embed=embed)

    @commands.command(usage='<flags>...')
    async def logging(self, ctx: CustomContext, *, config: LoggingConverter):
        """Sets the log channels for this server! `help logging` for help with flags format

        Available flags:

        All flags are optional

        ```
        kick - Channel where kick logs will be sent
        ban - Channel where ban logs will be sent
        purge - Channel where purge logs will be sent on "purge" command
        delete - Channel where deleted messages are sent
        mute - Channel where mute logs are sent on "mute" command
        ```

        You can pass "off" or "disable" to disable it!

        Usage:
        `flagname: argument`

        Example:

        `doggie.logging ban: #logs delete: #deletes`
        """

        if any([v for _, v in iter(config) if v == True]):
            raise commands.BadFlagArgument(config.get_flags()['ban_channel'])

        options = {k: v for k, v in iter(config) if v is not None}

        if not options:
            raise commands.BadFlagArgument(config.get_flags()['ban_channel'])

        msgs = [f'**{k.replace("_", " ").title()}:** {v.mention if v else "Disabled"}' for k, v in options.items()]

        await ctx.logging_config.set_config(self.bot, **options)

        embed = create_embed(
            ctx.author,
            title='Logging configuration set!',
            description='\n'.join(msgs)
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Configuration(bot))
