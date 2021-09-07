import discord
from discord.ext import commands, menus
from discord.ext.commands import Greedy

import unicodedata
from typing import Union, Optional

import utils

GREEDY_INTENTIONAL = Greedy[Union[utils.IntentionalMember, utils.IntentionalUser]]


def maybe_first_snipe_msg(ctx):
    embed = utils.create_embed(
        ctx.author,
        title='⚠ Warning!',
        description='That channel seems to be locked, and this channel '
                    'isn\'t. You should move to a private channel to avoid leaking sensitive '
                    'information. However, you have permissions to snipe from that channel, '
                    'so you may proceed with caution.',
        color=discord.Color.orange()
    )

    return embed


async def add_mute(member: discord.Member, role: discord.Role, **kwargs):
    await member.add_roles(role, **kwargs)


async def remove_mute(member: discord.Member, role: discord.Role, **kwargs):
    await member.remove_roles(role, **kwargs)


class SnipeMenu(menus.ListPageSource):
    def __init__(self, entries, first_message: discord.Embed = None):
        if first_message:
            self.num_offset = 1
            entries[:0] = [first_message]
        else:
            self.num_offset = 0
        super().__init__(entries, per_page=1)

    async def format_page(self, menu, entries):
        if isinstance(entries, discord.Embed): return entries
        index = menu.current_page + 1 - self.num_offset

        embed = utils.format_deleted_msg(entries, title=f'Sniped message {index}/{self._max_pages - self.num_offset}:')

        embed.set_footer(
            text=f'Command sent by {menu.ctx.author}',
            icon_url=utils.fix_url(menu.ctx.author.display_avatar)
        )

        return embed


class Moderation(commands.Cog):
    """Commands to make moderation easier and simpler
    Note: To prevent accidental punishments, you must specify users using their mention, id, or name#tag"""

    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    async def cog_check(self, ctx: utils.CustomContext):
        if not ctx.guild:
            raise commands.NoPrivateMessage()

        return True

    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @commands.command(usage='<users>... [reason]')
    async def ban(
            self,
            ctx: utils.CustomContext,
            users: GREEDY_INTENTIONAL,
            *,
            reason: Optional[str] = "No reason specified"):

        """Ban members who broke the rules! You can specify multiple members in one command.
        You can also ban users not in the guild using their ID!, You and this bot needs the "Ban Members" permission."""

        if not users:
            raise commands.UserNotFound(reason)

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            lists = await utils.multi_punish(
                ctx.author,
                users,
                ctx.guild.ban,
                reason=f'{str(ctx.author)}: {reason}'
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'banned', reason, lists)

        await ctx.send(embed=embed)

    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @commands.command(usage='<users>... [reason]')
    async def unban(
            self,
            ctx: utils.CustomContext,
            users: Greedy[utils.IntentionalUser], *,
            reason: Optional[str] = "No reason specified"):

        """Unban banned users with their User ID, you can specify multiple people to be unbanned.
        You and this bot need the "Ban Members" permission!"""

        if not users:
            raise commands.UserNotFound(reason)

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            lists = await utils.multi_punish(
                ctx.author,
                users,
                ctx.guild.unban,
                reason=f'{str(ctx.author)}: {reason}'
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'unbanned', reason, lists)

        await ctx.send(embed=embed)

    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @commands.command(usage='<members>... [reason]')
    async def softban(
            self,
            ctx: utils.CustomContext,
            members: Greedy[utils.IntentionalMember], *,
            reason: Optional[str] = "No reason specified"):

        """Bans then unbans the specified users, which deletes their recent messages and 'kicks' them.
        You and this bot needs the "Ban Members" permission!"""

        if not members:
            raise commands.MemberNotFound(reason)

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            banned, not_banned = await utils.multi_punish(
                ctx.author,
                members,
                ctx.guild.ban,
                reason=f'(Softban) {str(ctx.author)}: {reason}'
            )  # type: ignore

            unbanned, _ = await utils.multi_punish(
                ctx.author,
                banned,
                ctx.guild.unban,
                reason=f'(Softban) {str(ctx.author)}: {reason}'
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'softbanned', reason, (unbanned, not_banned))

        await ctx.send(embed=embed)

    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    @commands.command(usage='<members>... [reason]')
    async def kick(
            self,
            ctx: utils.CustomContext,
            members: Greedy[utils.IntentionalMember],
            *,
            reason: Optional[str] = "No reason specified"):

        """Kick members who broke the rules! You can specify multiple members in one command.
        You and this bot needs the "Kick Members" permission!"""

        if not members:
            raise commands.MemberNotFound(reason)

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            lists = await utils.multi_punish(
                ctx.author,
                members,
                ctx.guild.kick,
                reason=f'{str(ctx.author)}: {reason}'
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'kicked', reason, lists)

        await ctx.send(embed=embed)

    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.has_permissions(manage_nicknames=True)
    @commands.command(aliases=['nick', 'nickname'])
    async def rename(self, ctx: utils.CustomContext, members: Greedy[utils.IntentionalMember], *, nickname):
        """Renames users to a specified name"""

        if not members:
            raise commands.MemberNotFound(nickname)

        if len(nickname) > 32:
            embed = utils.create_embed(
                ctx.author,
                title='Nickname too long!',
                description=f'The nickname {nickname[:100]} is too long! (32 chars max.)',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            lists = await utils.multi_punish(
                ctx.author,
                members,
                discord.Member.edit,
                nick=nickname,
                reason=f'Renamed by {ctx.author}'
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'renamed', nickname, lists)

        await ctx.send(embed=embed)

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.command(aliases=['silence'])
    async def mute(
            self,
            ctx: utils.CustomContext,
            members: Greedy[utils.IntentionalMember],
            *,
            reason: Optional[str] = "No reason specified"):

        """Gives the configured mute role to members!"""

        if not ctx.basic_config.mute_role:
            embed = utils.create_embed(
                ctx.author,
                title='Mute role not set!',
                description='You need to set a mute role with the command `config mute_role <role>`',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        if not members:
            raise commands.MemberNotFound(reason)

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            lists: tuple = await utils.multi_punish(
                ctx.author,
                members,
                add_mute,
                role=ctx.basic_config.mute_role,
                reason=f'{str(ctx.author)}: {reason}'
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'muted', reason, lists)

        await ctx.send(embed=embed)

        self.bot.dispatch('mute', ctx, lists[0], reason)

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.command(aliases=['unsilence'])
    async def unmute(
            self,
            ctx: utils.CustomContext,
            members: Greedy[utils.IntentionalMember],
            *,
            reason: Optional[str] = "No reason specified"):

        """Removes the configured mute role from members!"""

        if not ctx.basic_config.mute_role:
            embed = utils.create_embed(
                ctx.author,
                title='Mute role not set!',
                description='You need to set a mute role with the command `config mute_role <role>`',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        if not members:
            raise commands.MemberNotFound(reason)

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            lists = await utils.multi_punish(
                ctx.author,
                members,
                remove_mute,
                role=ctx.basic_config.mute_role,
                reason=f'{str(ctx.author)}: {reason}'
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'unmuted', reason, lists)

        self.bot.dispatch('unmute', ctx, lists[0], reason)

        await ctx.send(embed=embed)

    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=True)
    @commands.cooldown(5, 60, type=commands.BucketType.guild)
    @commands.command(aliases=['clear', 'delete'])
    async def purge(self, ctx: utils.CustomContext, users: GREEDY_INTENTIONAL, amount: Optional[int] = 20):
        """Deletes multiple messages from the current channel, you can specify users that it will delete messages from.
        You can also specify the amount of messages to check. You and this bot needs the "Manage Messages" permission"""

        amount = 200 if abs(amount) >= 200 else abs(amount) + 1

        async with ctx.channel.typing():
            messages_deleted = await ctx.channel.purge(limit=amount, check=lambda m: not users or (m.author in users))

        users = [user.mention for user in users] if users else ['anyone']
        embed = utils.create_embed(
            ctx.author,
            title=f'{len(messages_deleted)} messages deleted!',
            description='Deleted messages from ' + ', '.join(users)
        )

        await ctx.send(embed=embed, delete_after=10)

        self.bot.dispatch('purge', ctx, users, len(messages_deleted))

    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.command(aliases=['ascii'])
    async def asciify(self, ctx: utils.CustomContext, members: Greedy[discord.Member]):
        """Replace weird unicode letters in nicknames with normal ASCII text!"""

        if not members:
            raise commands.MemberNotFound('None')

        async def rename(member: discord.Member):
            ascii_text = unicodedata.normalize('NFKD', member.display_name).encode('ascii', 'ignore').decode()
            await member.edit(nick=ascii_text[:31] or 'Unreadable', reason=f'Asciified by {ctx.author}')

        async with ctx.channel.typing():
            # noinspection PyTypeChecker
            lists = await utils.multi_punish(
                ctx.author,
                members,
                rename
            )  # type: ignore

        embed = utils.punish_embed(ctx.author, 'asciified', 'Asciify strange characters', lists)

        await ctx.send(embed=embed)

    @commands.max_concurrency(5, commands.BucketType.user)
    @commands.guild_only()
    @commands.command(aliases=['snpied', 'deleted'])
    async def snipe(self, ctx: utils.CustomContext, channel: Optional[discord.TextChannel], *,
                    user: Optional[discord.User]):
        """Shows recent deleted messages! You can specify an user to get deleted messages from.
        If no channel is specified it will get messages from the current channel.
        You can only snipe messages from channels in which you have `Manage Messages` and `View Channel` in."""

        if not ctx.basic_config.snipe:
            embed = utils.create_embed(
                ctx.author,
                title='Snipe is disabled in this guild!',
                description='The snipe command is opt-in only, use `config snipe on` '
                            'to enable sniping in this guild!',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        channel = channel or ctx.channel

        if not (channel.permissions_for(ctx.author).manage_messages and
                channel.permissions_for(ctx.author).view_channel):
            embed = utils.create_embed(
                ctx.author,
                title='Can\'t snipe from that channel!',
                description='You need permissions to view and manage messages of that channel '
                            'before you can snipe messages from it!',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        async with ctx.channel.typing():
            filtered = [message for message in self.bot.sniped if (message.guild == ctx.guild)
                        and (user is None or user == message.author) and (channel == message.channel)][:100]

        if not filtered:
            embed = utils.create_embed(
                ctx.author,
                title='No messages found!',
                description=f'No sniped messages were found for {user or "this guild"}'
                            f'{f" in {channel.mention}" or ""}',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        pages = utils.CustomMenu(source=SnipeMenu(filtered), clear_reactions_after=True)
        if (channel.overwrites_for(ctx.guild.default_role).view_channel == False and
                ctx.channel.overwrites_for(ctx.guild.default_role).view_channel != False):
            pages = utils.CustomMenu(source=SnipeMenu(filtered, maybe_first_snipe_msg(ctx)), clear_reactions_after=True)

        await pages.start(ctx)

        if len(filtered) > 1:
            await self.bot.wait_for('finalize_menu', check=lambda c: c == ctx, timeout=360)


def setup(bot):
    bot.add_cog(Moderation(bot))
