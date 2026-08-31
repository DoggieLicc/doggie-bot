import asyncio
from datetime import datetime, timedelta, timezone
import itertools

from discord import AllowedMentions, ButtonStyle, User, app_commands, Interaction, Attachment, Member, Embed, Color, DiscordException, HTTPException, NotFound, Forbidden, Emoji, ui

from discord.ext import commands
from discord.utils import format_dt
from loguru import logger

import utils
from utils import CustomBot, CustomContext
from utils.menus import CustomView


def get_hoisters(members: list[Member]):
    def check(member):
        value = ord(member.display_name[0])
        return 0 <= value <= 47 or 58 <= value <= 64

    members = sorted(members, key=lambda m: m.display_name)
    return list(itertools.takewhile(check, members))[:200]


class RecentJoinsMenu(utils.EntryMenu[Member]):
    async def get_page_contents(self):
        entries = self.get_page_items()
        embed = utils.create_embed(
            self.owner,
            title=f'Showing recent joins for this server'
                  f'({self.current_index}/{self.max_page}):'
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

        return {'embed': embed}


class RecentAccounts(utils.EntryMenu[Member]):
    async def get_page_contents(self):
        embed = utils.create_embed(
            self.owner,
            title=f'Showing newest accounts in this server '
                  f'({self.current_index}/{self.max_page}):'
        )
        for member in self.get_page_items():
            joined_at = utils.user_friendly_dt(member.joined_at)
            created_at = utils.user_friendly_dt(member.created_at)
            embed.add_field(
                name=f'{member}',
                value=f'ID: {member.id}\n'
                      f'Joined at: {joined_at}\n'
                      f'Created at: {created_at}', inline=False
            )

        return {'embed': embed}


class HoistersMenu(utils.EntryMenu[Member]):
    async def get_page_contents(self):
        embed = utils.create_embed(
            self.owner,
            title=f'Showing potential hoisters for this server '
                  f'({self.current_index}/{self.max_page}):'
        )

        for member in self.get_page_items():
            embed.add_field(
                name=f'{member.display_name}',
                value=f'Username: {member} ({member.mention})\n'
                      f'ID: {member.id}',
                inline=False
            )

        return {'embed': embed}


class SauceMenu(utils.EntryMenu[dict[str, dict]]):
    async def get_page_contents(self):
        result = self.get_page_items()[0]

        embed = utils.create_embed(
            self.owner,
            title=f'Result {self.current_index}/{self.max_page}:',
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

        embed.color = Color.orange() if result['header']['hidden'] else embed.color

        return {'embed': embed}


class SelfbotView(CustomView):
    def __init__(self, owner: User):
        super().__init__(owner)
        self.seen_users: list[User] = []
        self.start_time = datetime.now(timezone.utc)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        self.message = interaction.message
        return True

    @ui.button(label='Enter Giveaway', emoji='\N{PARTY POPPER}', style=ButtonStyle.blurple)
    async def fake_giveaway(self, interaction: Interaction, _):
        if interaction.user in self.seen_users:
            return await interaction.response.defer()

        td = interaction.created_at - self.start_time
        self.seen_users.append(interaction.user)

        if interaction.user == self.owner:
            return await interaction.response.send_message(
                f'{interaction.user.mention}: You have reacted to your own test in {td.total_seconds():.3f} seconds.',
                allowed_mentions=AllowedMentions.none()
            )

        await interaction.response.send_message(
            f'User {interaction.user.mention} (ID: {interaction.user.id}) joined fake giveaway in {td.total_seconds():.3f} seconds.',
            allowed_mentions=AllowedMentions.none()
        )

class UtilityCog(commands.Cog, name='Utility'):
    """Utility commands that may be useful to you!"""

    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot
        if not self.bot.config['saucenao_api_key']:
            # pylint: disable=comparison-with-callable
            self.__cog_commands__ = tuple(c for c in self.__cog_commands__ if c != self.saucenao)  # type: ignore
            logger.warning('SAUCENAO_API_KEY Environment variable missing. /saucenao will not be registered')

    @commands.hybrid_command(aliases=['recentusers', 'recent', 'newjoins', 'newusers', 'rj', 'joins'])
    @commands.max_concurrency(2, commands.BucketType.user)
    @app_commands.allowed_installs(users=False)
    @commands.guild_only()
    async def recentjoins(self, ctx: CustomContext):
        """Shows the most recent joins in the current server"""

        if not ctx.guild:
            return

        await ctx.defer(ephemeral=True)

        members = sorted(ctx.guild.members, key=lambda m: m.joined_at, reverse=True)[:100]
        view = RecentJoinsMenu(ctx.author, members, 5)

        await ctx.send(view=view, **await view.get_page_contents())

    @commands.hybrid_command(aliases=['bottest', 'selfbottest', 'bt', 'sbt', 'self'])
    @commands.max_concurrency(3, commands.BucketType.channel)
    @app_commands.allowed_installs(users=False)
    @commands.guild_only()
    async def selfbot(self, ctx: CustomContext):
        """Creates a fake Nitro giveaway to catch selfbots!"""

        if not ctx.guild or not ctx.guild.owner:
            return

        embed = Embed(
            color=Color.blurple(),
            title='Discord Nitro Giveaway',
            description='Click the button below to join the giveaway!'
        )

        embed.set_author(name='Discord Nitro')

        embed.add_field(
            name='Ends',
            value=format_dt(datetime.now(timezone.utc) + timedelta(hours=2))
        )

        embed.add_field(name='Hosts', value=ctx.guild.owner.mention)

        embed.add_field(name='Winners', value='3')

        view = SelfbotView(ctx.author)

        await ctx.send(
            ':tada: **GIVEAWAY** :tada: :yay:',
            ephemeral=False,
            embed=embed,
            view=view
        )

        await asyncio.sleep(view.timeout)  # For max_concurrency to work


    @commands.hybrid_command(aliases=['hoist'])
    @app_commands.allowed_installs(users=False)
    @commands.guild_only()
    async def hoisters(self, ctx: CustomContext):
        """Shows a list of members who have names made to 'hoist' themselves to the top of the member list!"""

        if not ctx.guild:
            return None

        hoisters = get_hoisters(ctx.guild.members)

        if not hoisters:
            raise utils.DoggieBotException('No hoisters found!', 'There weren\'t any members with odd starting characters found!')

        view = HoistersMenu(ctx.author, hoisters, 5)

        await ctx.send(view=view, **await view.get_page_contents(), ephemeral=True)

    @commands.hybrid_command(aliases=['steal_emote', 'steal_emoji', 'steal_emotes', 'add_emotes', 'add_emote'])
    @app_commands.allowed_installs(users=False)
    @app_commands.default_permissions(create_expressions=True)
    @commands.guild_only()
    @commands.has_guild_permissions(create_expressions=True)
    @commands.bot_has_guild_permissions(create_expressions=True)
    @app_commands.describe(emotes='The custom emotes you want to add to this server')
    async def stealemote(
        self,
        ctx: CustomContext,
        emotes: utils.MultiplePartialEmoteConverter
    ):
        """Adds the specified emotes to your server!"""

        if not ctx.guild:
            return None

        added, not_added = [], []
        embed = Embed()

        await ctx.defer()

        for emote in emotes:
            if isinstance(emote, Emoji) and emote.guild == ctx.guild:
                not_added.append(emote)
                continue

            try:
                added.append(await ctx.guild.create_custom_emoji(
                    name=emote.name,
                    image=await emote.read(),
                    reason=f'Added by {ctx.author} ({ctx.author.id})')
                )
            except (DiscordException, HTTPException, NotFound, Forbidden):
                not_added.append(emote)

        if not added:
            embed = utils.create_embed(
                ctx.author,
                title='Couldn\'t add any emotes!',
                description='Make sure they aren\'t already in this server, and that the bot has permissions!',
                color=Color.red()
            )

        if added and not_added:
            embed = utils.create_embed(
                ctx.author,
                title='Some emotes couldn\'t be added!',
                description='Make sure they aren\'t already in this server, and that the bot has permissions!',
                color=Color.orange()
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

    @commands.hybrid_command(aliases=['newaccount', 'new', 'newaccs', 'new_account', 'new_accounts'])
    @app_commands.allowed_installs(users=False)
    @commands.guild_only()
    async def newaccounts(self, ctx: CustomContext):
        """Shows the newest accounts in this server!"""
        if not ctx.guild:
            return None

        members = sorted(ctx.guild.members, key=lambda m: m.created_at, reverse=True)[:200]
        view = RecentAccounts(ctx.author, members, 5)
        await ctx.send(view=view, **await view.get_page_contents(), ephemeral=True)

    @commands.hybrid_command(aliases=['sauce', 'saucenow'])
    @commands.cooldown(4, 30, commands.BucketType.default)
    @commands.cooldown(100, 60 * 60 * 24, commands.BucketType.default)  # api limits
    @commands.is_nsfw()
    @app_commands.describe(image='Attach an image to get its source...')
    @app_commands.describe(image_url='... or the URL of the image to get the source of')
    async def saucenao(
        self,
        ctx: CustomContext,
        image: Attachment | None = None,
        image_url: str | None = None
    ):
        """Gets the source of an image using SauceNAO, usually for art. Most anime databases are disabled. :3"""

        if not self.bot.session:
            return

        if not image_url and not image:
            raise utils.DoggieBotException('No image Specified!', 'You must specify either `image` or `image_url`')

        await ctx.defer()

        image_url = image_url or (image.proxy_url if image else None)

        BASE_URL = 'https://saucenao.com/search.php'

        allowed_dbs = [23, 24, 29, 34, 39, 40, 41, 42]

        params = {
            'api_key': self.bot.config['saucenao_api_key'],  # key
            'output_type': 2,
            'numres': 10,
            'hide': 1,
            'dbs[]': allowed_dbs,
            'url': image_url
        }

        async with self.bot.session.get(BASE_URL, params=params) as resp:
            data = await resp.json()
            results = data['results']

        view = SauceMenu(ctx.author, results, 1)

        await ctx.send(view=view, **await view.get_page_contents())

    @app_commands.command()
    async def help(self, interaction: Interaction):
        """Show help page for this bot!"""
        ctx = await commands.Context.from_interaction(interaction)
        await ctx.send_help()

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
