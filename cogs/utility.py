import discord
import asyncio
import time
import utils
import itertools

from discord.ext import commands, menus
from discord.ext.commands import Greedy

from datetime import timedelta
from typing import Union, List, Optional, Dict
from collections import Counter


def get_hoisters(members: List[discord.Member]):
    def check(member):
        value = ord(member.display_name[0])
        return 0 <= value <= 47 or 58 <= value <= 64

    members = sorted(members, key=lambda m: m.display_name)
    return list(itertools.takewhile(check, members))[:200]


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


class SauceMenu(menus.ListPageSource):
    async def format_page(self, menu, result):
        index = menu.current_page + 1

        if menu.ctx.guild and not menu.ctx.channel.is_nsfw() and result['header']['hidden']:
            embed = utils.create_embed(
                menu.ctx.author,
                title=f'Result {index}/{self._max_pages}:',
                description='Potentially explicit result in channel not marked as NSFW.',
                color=discord.Color.red()
            )

        else:
            embed = utils.create_embed(
                menu.ctx.author,
                title=f'Result {index}/{self._max_pages}:',
                thumbnail=result['header']['thumbnail']
            )

            if urls := result['data'].get('ext_urls'):
                embed.add_field(name='URL:', value=urls[0], inline=False)

            if title := result['data'].get('title'):
                embed.add_field(name='Title:', value=title, inline=False)

        if (author_name := result['data'].get('author_name')) or (result['data'].get('author_url')):
            author_url = result['data'].get('author_url')
            if author_name and author_url:
                author_str = f'[{author_name}]({author_url})'
            else:
                author_str = author_name or author_url

            embed.add_field(name='Author:', value=author_str, inline=False)

        embed.add_field(name='Index:', value=result['header']['index_name'].split(' - ')[0].split(': ')[1], inline=False)

        embed.add_field(name='Similarity:', value=result['header']['similarity'] + '%', inline=False)

        embed.add_field(name='Potentially explicit?', value='Yes' if result['header']['hidden'] else 'No', inline=False)

        return embed


class PollSelect(discord.ui.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_options: Dict[int, str] = {}

    async def callback(self, interaction: discord.Interaction):
        self.selected_options[interaction.user.id] = self.values[0]
        await interaction.response.defer()


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
        await self.bot.wait_for('finalize_menu', check=lambda c: c == ctx, timeout=360)

    @commands.max_concurrency(3, commands.BucketType.channel)
    @commands.guild_only()
    @commands.command(aliases=['bottest', 'selfbottest', 'bt', 'sbt', 'self'])
    async def selfbot(self, ctx: utils.CustomContext):
        """Creates a fake Nitro giveaway to catch a selfbot (Automated user accounts which auto-react to giveaways)
        When someone reacts with to the message, The user and the time to react will be sent."""

        selfbot_embed = discord.Embed(
            color=discord.Color.green(),
            title='Giveaway',
            description=f'**Prize:** Discord Nitro\n'
                        f'**Time left:** Infinity\n'
                        f'**Hosted by:** {ctx.guild.owner.mention}\n'
                        f'**React with :tada: to participate!**'
        )

        selfbot_embed.set_author(name='Discord Nitro')

        message = await ctx.send(
            ':tada: **GIVEAWAY** :tada: :yay:',
            embed=selfbot_embed
        )

        await message.add_reaction('\N{PARTY POPPER}')

        t = time.perf_counter()
        seen_users = set()
        users_message: Optional[discord.Message] = None

        def check(_reaction, _user):
            if _reaction.message == message and str(_reaction.emoji) == '\N{PARTY POPPER}' \
                    and not _user.bot and _user not in seen_users:
                seen_users.add(_user)
                return True

            return False

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=600, check=check)
            except asyncio.TimeoutError:

                if not seen_users:
                    embed = utils.create_embed(
                        ctx.author,
                        title='Test timed out!',
                        description=f'No one reacted within 10 minutes!',
                        color=discord.Color.red()
                    )

                    await message.reply(embed=embed)

                return

            else:
                if user == ctx.author:
                    embed = utils.create_embed(
                        ctx.author,
                        title='Test canceled!',
                        description=f'You reacted to your own test, so it was canceled.\nAnyways, '
                                    f'your time is {round(time.perf_counter() - t, 2)} seconds.',
                        color=discord.Color.red()
                    )

                    return await message.reply(embed=embed)

                else:
                    if not users_message:

                        embed = utils.create_embed(
                            ctx.author,
                            title='Reaction found!',
                            description=f'{user} (ID: {user.id})\nreacted with {reaction} in '
                                        f'{round(time.perf_counter() - t, 2)} seconds'
                        )

                        users_message = await message.reply(embed=embed)

                    else:

                        new_msg = f'\n\n{user} (ID: {user.id})\nreacted with {reaction} in ' \
                                  f'{round(time.perf_counter() - t, 2)} seconds'

                        embed = utils.create_embed(
                            ctx.author,
                            title='Reactions found!',
                            description=users_message.embeds[0].description + new_msg
                        )

                        users_message = await users_message.edit(embed=embed)

    @commands.guild_only()
    @commands.cooldown(5, 60)
    @commands.group(aliases=['hoist'], invoke_without_command=True)
    async def hoisters(self, ctx: utils.CustomContext):
        """Shows a list of members who have names made to 'hoist' themselves to the top of the member list!"""

        hoisters = get_hoisters(ctx.guild.members)

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

        hoisters: List[int] = [m.id for m in get_hoisters(ctx.guild.members)]

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
            raise commands.MissingRequiredArgument(ctx.command.params['emotes'])

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

    @commands.command(aliases=['sauce', 'saucenow'])
    @commands.cooldown(4, 30, commands.BucketType.default)
    @commands.cooldown(100, 60 * 60 * 24, commands.BucketType.default)  # api limits
    async def saucenao(self, ctx: utils.CustomContext, image: Optional[str]):
        """Gets the source of an image using SauceNAO, usually for art. Most anime databases are disabled. :3"""

        image_url = ctx.message.attachments[0].url if ctx.message.attachments else image

        if not image_url:
            raise commands.MissingRequiredArgument(ctx.command.params['image'])

        BASE_URL = 'https://saucenao.com/search.php'

        allowed_dbs = [23, 24, 29, 34, 39, 40, 41, 42]

        params = {
            'api_key': ctx.bot.config['saucenao_api_key'],  # key
            'output_type': 2,
            'numres': 10,
            'hide': 1,
            'dbs[]': allowed_dbs,
            'url': image_url
        }

        async with ctx.bot.session.get(BASE_URL, params=params) as resp:
            data = await resp.json()
            results = data['results']

        pages = utils.CustomMenu(source=SauceMenu(results, per_page=1), clear_reactions_after=True)

        await pages.start(ctx)


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
