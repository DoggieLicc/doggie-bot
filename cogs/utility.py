from typing import Union

import discord
from discord.ext import commands, menus
from discord.ext.commands import Greedy

import asyncio
import string
import time

import utils


class RecentJoinsMenu(menus.ListPageSource):
    async def format_page(self, menu, entries):
        index = menu.current_page + 1
        embed = utils.create_embed(
            menu.ctx.author,
            title=f'Showing recent joins for {menu.ctx.guild} '
                  f'({index}/{self._max_pages}):'
        )
        for member in entries:
            joined_at = utils.user_friendly_dt(member.joined_at)
            created_at = utils.user_friendly_dt(member.created_at)
            embed.add_field(
                name=f'{member}',
                value=f'ID: {member.id}\n'
                      f'Joined at: {joined_at}\n'
                      f'Created at: {created_at}', inline=False
            )

        return embed


class RecentAccounts(menus.ListPageSource):
    async def format_page(self, menu, entries):
        index = menu.current_page + 1
        embed = utils.create_embed(
            menu.ctx.author,
            title=f'Showing newest accounts in {menu.ctx.guild} '
                  f'({index}/{self._max_pages}):'
        )
        for member in entries:
            joined_at = utils.user_friendly_dt(member.joined_at)
            created_at = utils.user_friendly_dt(member.created_at)
            embed.add_field(
                name=f'{member}',
                value=f'ID: {member.id}\n'
                      f'Joined at: {joined_at}\n'
                      f'Created at: {created_at}', inline=False
            )

        return embed


class HoistersMenu(menus.ListPageSource):
    async def format_page(self, menu, entries):
        index = menu.current_page + 1
        embed = utils.create_embed(
            menu.ctx.author,
            title=f'Showing potential hoisters for {menu.ctx.guild} '
                  f'({index}/{self._max_pages}):'
        )

        for member in entries:
            embed.add_field(
                name=f'{member.display_name}',
                value=f'Username: {member} ({member.mention})\n'
                      f'ID: {member.id}',
                inline=False
            )

        return embed


class HoistersIDMenu(menus.ListPageSource):
    async def format_page(self, menu, entries):
        return " ".join(map(str, entries))


class UtilityCog(commands.Cog, name="Utility"):
    """Utility commands that may be useful to you!"""

    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @commands.max_concurrency(5, commands.BucketType.user)
    @commands.guild_only()
    @commands.command(aliases=['recentusers', 'recent', 'newjoins', 'newusers', 'rj', 'joins'])
    async def recentjoins(self, ctx):
        """Shows the most recent joins in the current server"""

        async with ctx.channel.typing():
            members = sorted(ctx.guild.members, key=lambda m: m.joined_at, reverse=True)[:100]

            pages = utils.CustomMenu(source=RecentJoinsMenu(members, per_page=5), clear_reactions_after=True)

        await pages.start(ctx)
        await self.bot.wait_for('finalize_menu', check=lambda c: c == ctx)

    @commands.max_concurrency(3, commands.BucketType.channel)
    @commands.guild_only()
    @commands.command(aliases=['bottest', 'selfbottest', 'bt', 'sbt', 'self'])
    async def selfbot(self, ctx, users: Greedy[discord.Member]):
        """Creates a fake Nitro giveaway to catch a selfbot (Automated user accounts which auto-react to giveaways)
        When someone reacts with to the message, The user and the time will be sent.
        You can specify users so that the bot will only respond to their reactions."""

        if users: users.append(ctx.author)

        message = await ctx.send(
            ':tada: GIVEAWAY :tada:\n'
            'Prize: Discord Nitro\n'
            'Timeleft: Infinity\n'
            'React with :tada: to participate!'
        )

        await message.add_reaction('\N{PARTY POPPER}')
        t = time.perf_counter()

        def check(_reaction, _user):
            return _reaction.message == message and not (_user.bot and not users) or _user in users \
                   and str(_reaction.emoji) == '\N{PARTY POPPER}'

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=600, check=check)
        except asyncio.TimeoutError:

            embed = utils.create_embed(
                ctx.author,
                title='Test timed out!',
                description=f'No one reacted within 10 minutes!',
                color=discord.Color.red()
            )

        else:
            if user == ctx.author:
                embed = utils.create_embed(
                    ctx.author,
                    title='Test canceled!',
                    description=f'You reacted to your own test, so it was canceled.\nAnyways, '
                                f'your time is {round(time.perf_counter() - t, 2)} seconds.',
                    color=discord.Color.red()
                )

            else:
                embed = utils.create_embed(ctx.author,
                                           title='Reaction found!',
                                           description=f'{user} (ID: {user.id})\nreacted with {reaction} in '
                                                       f'{round(time.perf_counter() - t, 2)} seconds'
                                           )

        try:
            await message.reply(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.cooldown(5, 60)
    @commands.group(aliases=['hoist'], invoke_without_command=True)
    async def hoisters(self, ctx):
        """Shows a list of members who have names made to 'hoist' themselves to the top of the member list!"""

        ok_chars = list(string.ascii_letters + string.digits)
        members = sorted(ctx.guild.members, key=lambda m: m.display_name)[:200]

        hoisters: [discord.Member] = []

        for member in members:
            if member.display_name[0] in ok_chars:
                break
            hoisters.append(member)

        if not hoisters:
            embed = utils.create_embed(
                ctx.author,
                title="No hoisters found!",
                description="There weren't any members with odd characters found!",
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        pages = utils.CustomMenu(source=HoistersMenu(hoisters, per_page=10), clear_reactions_after=True)

        await pages.start(ctx)

    @commands.guild_only()
    @hoisters.command(aliases=['ids'])
    async def id(self, ctx):
        """Like `hoisters`, but only shows the ids to make it easy to use with commands"""
        ok_chars = list(string.ascii_letters + string.digits)
        members = sorted(ctx.guild.members, key=lambda m: m.display_name)[:200]

        hoisters: [int] = []

        for member in members:
            if member.display_name[0] in ok_chars:
                break
            hoisters.append(member.id)

        if not hoisters:
            embed = utils.create_embed(
                ctx.author,
                title="No hoisters found!",
                description="There weren't any members with odd characters found!",
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        pages = utils.CustomMenu(source=HoistersIDMenu(hoisters, per_page=100), clear_reactions_after=True)
        await pages.start(ctx)

    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    @commands.command(aliases=['steal_emote', 'steal_emoji', 'steal_emotes', 'add_emotes', 'add_emote'])
    async def steal(
            self,
            ctx: utils.CustomContext,
            emotes: Greedy[Union[discord.Emoji, discord.PartialEmoji, utils.NitrolessEmoteConverter]]):
        """Adds the specified emotes to your server!
        If you don\'t have nitro, you can replace the : in the emotes with ;

        Example:
        `doggie.steal <;botTag;230105988211015680>`
        """

        if not emotes:
            raise commands.MissingRequiredArgument(ctx.channel)

        added, not_added = [], []
        embed = discord.Embed()

        for emote in emotes:
            if isinstance(emote, discord.Emoji) and emote.guild == ctx.guild:
                not_added.append(emote)
                continue

            try:
                added.append(await ctx.guild.create_custom_emoji(
                    name=emote.name,
                    image=await emote.read(),
                    reason=f'Added by {ctx.author} ({ctx.author.id})')
                )
            except (discord.DiscordException, discord.HTTPException, discord.NotFound, discord.Forbidden):
                not_added.append(emote)

        if not added:
            embed = utils.create_embed(
                ctx.author,
                title='Couldn\'t add any emotes!',
                description='Make sure they aren\'t already in this server, and that the bot has permissions!',
                color=discord.Color.red()
            )

        if added and not_added:
            embed = utils.create_embed(
                ctx.author,
                title='Some emotes couldn\'t be added!',
                description='Make sure they aren\'t already in this server, and that the bot has permissions!',
                color=discord.Color.orange()
            )

        if added and not not_added:
            embed = utils.create_embed(
                ctx.author,
                title='Emotes successfully added!'
            )

        if added:
            embed.add_field(
                name='Emotes added:',
                value=' '.join(map(str, added)),
                inline=False
            )

        if not_added:
            embed.add_field(
                name='Emotes not added:',
                value=' '.join(map(str, not_added)),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(aliases=['newaccount', 'new', 'newaccs', 'new_account', 'new_accounts'])
    async def newacc(self, ctx: utils.CustomContext):
        """Shows the newest accounts in this server!"""

        members = sorted(ctx.guild.members, key=lambda m: m.created_at, reverse=True)[:200]

        pages = utils.CustomMenu(source=RecentAccounts(members, per_page=10), clear_reactions_after=True)

        await pages.start(ctx)

    @selfbot.error
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MaxConcurrencyReached):
            embed = utils.create_embed(ctx.author, title=f'Error!', color=discord.Color.red())
            embed.add_field(
                name='Too many tests running!',
                value=f'You can only have {error.number} tests running at the same time in this channel!'
            )

            await ctx.send(embed=embed)

    @recentjoins.error
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MaxConcurrencyReached):
            embed = utils.create_embed(ctx.author, title=f'Error!', color=discord.Color.red())
            embed.add_field(
                name='Menu already open!',
                value=f'You can only have {error.number} menu running at once, '
                      f'use the ⏹ or 🗑 buttons to close the current menu!'
            )

            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(UtilityCog(bot))
