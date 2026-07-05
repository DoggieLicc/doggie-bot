import random
from dataclasses import dataclass
from typing import Callable
from inspect import Parameter, Signature

from discord import app_commands, Interaction, Color, File, User
from discord.ext import commands
from loguru import logger

from unsplash import Unsplash, Photo
import utils
from utils import CustomBot, CustomContext

UTM_PARAMS = '?utm_source=discord_bot_doggie_bot&utm_medium=referral'

async def get_pic(url: str, ctx_i: CustomContext | Interaction[CustomBot], key: str) -> str:
    bot = ctx_i.bot if isinstance(ctx_i, CustomContext) else ctx_i.client
    if not bot.session:
        return ''

    async with bot.session.get(url) as resp:
        data = await resp.json()

    return data[key]


async def furry_image(ctx_i: CustomContext | Interaction[CustomBot], user: User | None, endpoint: str, action: str, a2: str | None = None):
    author = ctx_i.author if isinstance(ctx_i, CustomContext) else ctx_i.user
    if not user or user == author:
        msg = f'{author.mention} has no one to {action} :('
    elif user.bot:
        msg = f'{author.mention} tries to {action} a bot... sad :('
    else:
        msg = f'{author.mention} {action + 's' if not a2 else a2} {user.mention}!'

    try:
        url = await get_pic(f'https://v2.yiff.rest/furry/{endpoint}', ctx_i, key='images')
    except Exception as e:
        raise utils.DoggieBotException('API Error!', 'Unable to get furry image from API. Try again later?') from e
    return utils.create_embed(author, title=f'Furry {action}!', description=msg, image=url[0]['url'])


@dataclass
class FurryCommand:
    action1: str
    action2: str | None = None
    action3: str | None = None

    def add_param_description(self, callback: Callable):
        deco = app_commands.describe(user=f'Specify someone to {self.action1} them!')
        return deco(callback)

    def get_callback(self) -> Callable:
        params = [
            commands.Parameter(
                'ctx',
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=CustomContext,
            ),
            commands.Parameter(
                'user',
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=User | None,
                default=None
            )
        ]

        async def callback(*args, **kwargs):
            bound = Signature(params).bind(*args, **kwargs)

            ctx: CustomContext = bound.arguments['ctx']
            user: User | None = bound.arguments['user']

            embed = await furry_image(ctx, user, self.action1, self.action1, self.action2)

            if isinstance(ctx, CustomContext):
                await ctx.send(embed=embed)

        callback.__name__ = str(self.action1)
        callback.__signature__ = Signature(params)  # type: ignore
        callback.__doc__ = self.description
        callback = self.add_param_description(callback)

        return callback

    @property
    def description(self) -> str:
        act = self.action3 if self.action3 else self.action1 + 'ing'
        return f'Get a picture of {act} eachother, because why not?'

FURRY_COMMANDS = [
    FurryCommand('hug', None, 'hugging'),
    FurryCommand('boop'),
    FurryCommand('hold'),
    FurryCommand('kiss', 'kisses'),
    FurryCommand('lick'),
    FurryCommand('cuddle', None, 'cuddling')
]


class RandomCog(commands.Cog, name='Random'):
    """Commands to get something random, like colors or images!"""
    def __init__(self, bot):
        self.bot: CustomBot = bot

        if not bot.config['unsplash_api_key']:
            self.random.remove_command('unsplash')
            self.unsplash = None
            logger.warning('UNSPLASH_API_KEY Environment variable missing. /unsplash command will not be registered')
        else:
            self.unsplash = Unsplash(bot.config['unsplash_api_key'])

        self.cached_random_photos: list[Photo] = []

        for furry_command in FURRY_COMMANDS:
            cmd = commands.HybridCommand(furry_command.get_callback(), name=furry_command.action1, description=furry_command.description)
            self.furry.add_command(cmd)

    @commands.hybrid_group()
    async def random(self, _):
        """Commands to get something random, like colors or images!"""

    @random.command(aliases=['user'])
    @commands.guild_only()
    @utils.not_user_integration()
    @app_commands.describe(include_bots='Whether or not to include bots (Default: False)')
    async def member(self, ctx: CustomContext, include_bots: bool = False):
        """Shows a random member from this server!"""

        if not ctx.guild:
            return

        member = random.choice([m for m in ctx.guild.members if not m.bot or m.bot == include_bots])

        embed = utils.create_embed(
            ctx.author,
            title='Random member from server!',
            description=f'{member.mention} - (ID: {member.id})',
            thumbnail=member.display_avatar
        )

        await ctx.send(embed=embed)

    @random.command(aliases=['colour'])
    async def color(self, ctx: CustomContext):
        """Shows a random color!"""
        color = Color.random()

        buffer = await self.bot.loop.run_in_executor(None, utils.solid_color_image, color.to_rgb())
        file = File(filename='color.png', fp=buffer)

        embed = utils.create_embed(
            ctx.author,
            title='Showing random color:',
            color=color,
            thumbnail='attachment://color.png'
        )

        embed.add_field(name='Hex:', value=f'`{color}`')
        embed.add_field(name='Int:', value=f'`{str(color.value).zfill(8)}`')
        embed.add_field(name='RGB:', value=f'`{color.to_rgb()}`')

        await ctx.send(file=file, embed=embed)

    @random.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def duck(self, ctx: CustomContext):
        """Gets a random duck from random-d.uk"""

        url = await get_pic('https://random-d.uk/api/v2/quack', ctx, key='url')
        embed = utils.create_embed(ctx.author, title='Random duck picture!:', image=url)

        await ctx.send(embed=embed)

    @random.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def dog(self, ctx: CustomContext):
        """Gets a random dog from random.dog"""

        url = await get_pic('https://random.dog/woof.json?filter=mp4', ctx, key='url')
        embed = utils.create_embed(ctx.author, title='Random dog picture!:', image=url)

        await ctx.send(embed=embed)

    @random.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def fox(self, ctx: utils.CustomContext):
        """Gets a random fox from randomfox.ca"""

        url = await get_pic('https://randomfox.ca/floof/', ctx, key='image')
        embed = utils.create_embed(ctx.author, title='Random fox picture!:', image=url)

        await ctx.send(embed=embed)

    @random.command(name='unsplash')
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def unsplash_cmd(self, ctx: CustomContext):
        """Gets a random photo from the Unsplash API!"""

        if not self.unsplash:
            return

        if not self.cached_random_photos:
            self.cached_random_photos = await self.unsplash.random(content_filter='high', count=30)

        image: Photo = self.cached_random_photos.pop(0)

        description = f'"{image.description or image.alt_description}"\n\n' \
                      f'*Photo by [{image.user.name}](https://unsplash.com/@{image.user.username}{UTM_PARAMS}) on ' \
                      f'[Unsplash](https://unsplash.com/{UTM_PARAMS})*'

        embed = utils.create_embed(
            ctx.author,
            title='Unsplash Image',
            description=description,
            image=image.urls.regular,
            color=image.color,
            timestamp=image.created_at
        )

        await ctx.send(embed=embed)

    @random.group()
    async def furry(self, _):
        pass

async def setup(bot: utils.CustomBot):
    await bot.add_cog(RandomCog(bot))
