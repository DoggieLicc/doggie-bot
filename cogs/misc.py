import base64
import inspect
import asyncio
from io import StringIO
from collections import Counter

from aiohttp import ClientSession
from discord import app_commands, Permissions, User, File
from discord.ext import commands
from discord.utils import oauth_url
from loguru import logger

import utils
from utils import CustomBot, CustomContext
from utils.classes import DoggieBotException

CHANGELOG = """
### 8/31/2026 - More API commands
* Added two statistic commands related to a certain furry website (NSFW)
* Lowered the amount of entries in some utility commands

### 7/6/2026 - Slash Commands Update!
The bot has gone through a rewrite, and now most commands are usuable through Discord's slash commands system!
* Most commands are usable as both slash commands and text commands
* Bot can be installed as an user app! Note that commands that require server-specific info/permissions won't work as an user app.
    - Slash commands' responses will be ephermeral if ran as an user app, or if the bot member doesn't have permissions to send messages in the channel normally.
* New config slash commands
* All `random` commands need to be ran as `random cmd`  when using text commands
* All `image` commands need to be ran as `image cmd`  when using text commands, pride specific commands as `image pride cmd`
* New system for image commands - You can use the `Select Image` message menu command, to use that image as the default
* `wikipedia` and `sendwebhook` commands removed.
* All menus now use components instead of reactions
* `timeout` and `remind` can now take `@time` timestamps
* `color` command will show all colors for multi-colored roles
* `saucenao` command set as NSFW-only
* Other general improvements"""

BASE_URL = 'https://e621.net'
PAGE_LIMIT = 200
FAV_LIMIT = 2000

class E621CounterMenu(utils.EntryMenu[tuple[str, int]]):
    def __init__(
        self,
        owner: User,
        items: list[tuple[str, int]],
        items_per_page: int,
        username: str,
        user_id: int,
        counted: str,
        total: int
    ):
        self.username = username
        self.user_id = user_id
        self.counted = counted
        self.total = total
        super().__init__(owner, items, items_per_page)

    async def get_page_contents(self):
        text_str_l = []
        for tag, count in self.get_page_items():
            text_str_l.append(
                f'`{tag}`: {count}'
            )

        embed = utils.create_embed(
            self.owner,
            title=f'Showing most common favorited {self.counted} for {self.username} (ID: {self.user_id}) '
                  f'({self.current_index}/{self.max_page}):',
            description=f'**\\# of Favorites: {self.total}**\n\n' + '\n'.join(text_str_l),
            url=BASE_URL + f'/users/{self.user_id}'
        )

        return {'embed': embed}


async def get_user_id(username: str, session: ClientSession) -> int:
    if (user_id := Misc.USER_CAHCE.get(username, None)):
        return user_id

    async with session.get(BASE_URL + f'/users/{username}.json', headers=Misc.HEADERS, timeout=10) as resp:
        if resp.status == 404:
            raise utils.DoggieBotException('User not found!', f'Unable to find e621 user "{username}"')
        if not resp.ok:
            raise DoggieBotException('e621 API Error', f'e621 API responded with code {resp.status}')
        if resp.content_type.lower() != 'application/json':
            raise DoggieBotException('e621 API Error', 'e621 API did not respond with valid JSON (Maybe you entered a bad name?)')

        await asyncio.sleep(1)
        user_id = (await resp.json())['id']
        Misc.USER_CAHCE[username] = user_id
        return user_id

async def get_user_faves(user: str, session: ClientSession) -> tuple[Counter, Counter, int]:
    gen_count = Counter()
    artist_count = Counter()
    total_posts = 0
    page_num = 1

    try:
        user_id = await get_user_id(user, session)

        while True:
            async with session.get(
                BASE_URL + '/favorites.json',
                headers=Misc.HEADERS,
                params={'user_id': user_id, 'limit': PAGE_LIMIT, 'page': page_num},
                timeout=10
            ) as resp:
                if resp.status == 403:
                    raise DoggieBotException('Favorites Hidden!', f'User `{user}` has their favorites set to hidden. (suspicious!)')
                if not resp.ok:
                    raise DoggieBotException('e621 API Error', f'e621 API responded with code {resp.status}')
                if resp.content_type.lower() != 'application/json':
                    raise DoggieBotException('e621 API Error', 'e621 API did not respond with valid JSON (Maybe you entered a bad name?)')

                posts = (await resp.json())['posts']

            page_num += 1
            total_posts += len(posts)

            for post in posts:
                for tag in post['tags']['general']:
                    gen_count[tag] += 1
                for tag in post['tags']['species']:
                    gen_count[tag] += 1
                for tag in post['tags']['character']:
                    gen_count[tag] += 1
                for tag in post['tags']['artist']:
                    artist_count[tag] += 1

            if not posts or total_posts >= FAV_LIMIT or len(posts) < PAGE_LIMIT:
                return gen_count, artist_count, total_posts

            await asyncio.sleep(1)
    except asyncio.TimeoutError as e:
        raise DoggieBotException('E621 API Error', 'The E621 API timed out.') from e


class Misc(commands.Cog, name='Misc'):
    """Commands that show info about the bot"""
    HEADERS = {}
    USER_CAHCE = {}

    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot
        if not bot.config['e621_username'] or not bot.config['e621_api_key']:
            # pylint: disable=comparison-with-callable
            self.__cog_commands__ = tuple(c for c in self.__cog_commands__ if c != self.e621)  # type: ignore
            logger.warning('E621_USERNAME or E621_API_KEY Environment variables missing. /e621 commands will not be registered')
        else:
            API_LOGIN = bot.config['e621_username']
            USER_AGENT = f'DoggieBot - (user: {API_LOGIN})'
            API_KEY = bot.config['e621_api_key']
            LOGIN_ENCODED = base64.b64encode(f'{API_LOGIN}:{API_KEY}'.encode('utf-8')).decode('utf-8')
            Misc.HEADERS = {
                'Authorization': f'Basic {LOGIN_ENCODED}',
                'User-Agent': USER_AGENT
            }

    @commands.hybrid_command(aliases=['i', 'ping', 'about'])
    async def info(self, ctx: CustomContext):
        """Shows information for the bot!"""

        invite_url = oauth_url(self.bot.application_id, permissions=Permissions(4513770781404358))

        embed = utils.create_embed(
            ctx.author,
            title='Info for Doggie Bot!',
            description='This bot is a multi-purpose bot!\n\n[Terms of Service](https://doggieli.cc/discord-bots/doggie-bots-tos.html) | [Privacy Policy](https://doggieli.cc/discord-bots/doggie-bot-privacy-policy.html)'
        )

        embed.add_field(
            name='Invite this bot!',
            value=f'[Invite]({invite_url})',
            inline=False
        )

        embed.add_field(
            name='Join support server!',
            value='[Support Server](https://discord.gg/d7dgReCnRR)',
            inline=False
        )

        embed.add_field(
            name='Bot Creator:',
            value='[@doggielicc](https://doggieli.cc/)',
            inline=True
        )

        embed.add_field(
            name='Source Code:',
            value='[Github Repo](https://github.com/DoggieLicc/doggie-bot) | [Repo Mirror](https://git.doggieli.cc/doggie/doggie-bot)'
        )

        embed.add_field(
            name='Bot Online Since:',
            value=utils.user_friendly_dt(self.bot.start_time),
            inline=False
        )

        embed.add_field(
            name='Ping:',
            value=f'{round(1000 * self.bot.latency)} ms',
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['report', 'bug', 'suggestion'])
    @commands.cooldown(3, 86_400, commands.BucketType.user)
    @app_commands.describe(suggestion='What you want to suggest!')
    async def suggest(self, ctx: CustomContext, suggestion: str):
        """Send a suggestion or bug report to the bot owner!"""

        owner: User = await self.bot.get_owner()

        owner_embed = utils.create_embed(
            ctx.author,
            title='New suggestion!:',
            description=suggestion
        )

        await owner.send(embed=owner_embed)

        user_embed = utils.create_embed(
            ctx.author,
            title=f'👍 Suggestion has been sent to {owner}! 💖'
        )

        await ctx.send(embed=user_embed)

    @commands.hybrid_command(aliases=['code'])
    @app_commands.describe(command='Specify a command to get the source code of that command')
    async def source(self, ctx: CustomContext, command: str | None = None):
        """Look at the code of this bot!"""

        if command is None:
            embed = utils.create_embed(
                ctx.author,
                title='Source Code:',
                description='[Github for **Doggie Bot**](https://github.com/DoggieLicc/doggie-bot)'
            )

            return await ctx.send(embed=embed)

        a_commands = command.lower().strip('/').split(maxsplit=2)

        obj = self.bot.tree.get_command(a_commands[0])

        if isinstance(obj, app_commands.Group) and len(a_commands) > 1:
            obj = obj.get_command(a_commands[1])

            if isinstance(obj, app_commands.Group) and len(a_commands) > 2:
                obj = obj.get_command(a_commands[2])

        if obj is None:
            raise utils.DoggieBotException('Command not found!', f'The command `{command}` wasn\'t found in this bot.')

        if isinstance(obj, app_commands.Group):
            raise utils.DoggieBotException('Not a command!', f'`/{obj.qualified_name}` is a command group, and doesn\'t have source code!')

        src = obj.callback.__code__

        lines, _ = inspect.getsourcelines(src)
        if lines[0].startswith(' '*4):
            src_code = ''.join([l[4:] if l.startswith(' '*4) else l for l in lines])
        else:
            src_code = ''.join(lines)

        buffer = StringIO(src_code)

        file = File(fp=buffer, filename=f'{command.replace(' ', '_').lower()}.py')

        await ctx.send(f'Here you go, {ctx.author.mention}. (You should view this on a PC)', file=file)

    @commands.hybrid_command()
    async def changelog(self, ctx: CustomContext):
        """Show changelogs for this bot!"""
        embed = utils.create_embed(
            ctx.author,
            title='Doggie Bot - Change Log:',
            description=CHANGELOG
        )
        await ctx.send(embed=embed)

    @commands.hybrid_group()
    @commands.is_nsfw()
    @commands.cooldown(2, 1, commands.BucketType.default)
    async def e621(self, ctx: CustomContext):
        """e621 related commands"""

    @e621.command()
    @commands.is_nsfw()
    @commands.cooldown(2, 1, commands.BucketType.default)
    @app_commands.describe(username='The e621 username of who you want to check')
    async def favoritetags(self, ctx: CustomContext, username: str):
        """Get the most common tags in an e621 user's favorites"""
        await ctx.defer()
        tags_count, _, total = await get_user_faves(username, self.bot.session)
        user_id = await get_user_id(username, self.bot.session)

        if total == 0:
            raise DoggieBotException('No favorites found!', f'User {username} has no favorites, or has favorites set to hidden.')

        if not tags_count:
            raise DoggieBotException('No tags found!', f'Somehow, there are no tags in user `{username}`\'s favorites')

        view = E621CounterMenu(ctx.author, tags_count.most_common(200), 20, username, user_id, 'tags', total)
        await ctx.send(view=view, **await view.get_page_contents())

    @e621.command()
    @commands.is_nsfw()
    @commands.cooldown(2, 1, commands.BucketType.default)
    @app_commands.describe(username='The e621 username of who you want to check')
    async def favoriteartists(self, ctx: CustomContext, username: str):
        """Get the most common artists in an e621 user's favorites"""
        await ctx.defer()
        _, artist_count, total = await get_user_faves(username, self.bot.session)
        user_id = await get_user_id(username, self.bot.session)

        if total == 0:
            raise DoggieBotException('No favorites found!', f'User {username} has no favorites, or has favorites set to hidden.')

        if not artist_count:
            raise DoggieBotException('No artists found!', f'Somehow, there are no artist tags in user `{username}`\'s favorites')

        view = E621CounterMenu(ctx.author, artist_count.most_common(300), 30, username, user_id, 'artists', total)
        await ctx.send(view=view, **await view.get_page_contents())

async def setup(bot):
    await bot.add_cog(Misc(bot))
