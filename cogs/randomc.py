import discord
import random
import utils

from discord.ext import commands
from unsplash import Unsplash, Photo, UnsplashException
from typing import Optional, List
from aiohttp import ClientError

utm_params = '?utm_source=discord_bot_doggie_bot&utm_medium=referral'


async def get_pic(url: str, ctx: utils.CustomContext, key: str) -> str:
    async with ctx.bot.session.get(url) as resp:
        data = await resp.json()

    return data[key]


async def furry_image(ctx, user: Optional[discord.User], endpoint: str, action: str, a2: str = None):
    if not user or user == ctx.author:
        msg = f'{ctx.author.mention} has no one to {action} :('
    elif user.bot:
        msg = f'{ctx.author.mention} tries to {action} a bot... sad :('
    else:
        msg = f'{ctx.author.mention} {action + "s" if not a2 else a2} {user.mention}!'

    url = await get_pic(f'https://v2.yiff.rest/furry/{endpoint}', ctx, key='images')
    return utils.create_embed(ctx.author, title=f'Furry {action}!', description=msg, image=url[0]['url'])


def check_unsplash():
    def predicate(ctx):
        if ctx.bot.config['unsplash_api_key']:
            return True

        raise utils.MissingAPIKey(
            'The Unsplash API key is missing!'
            'The owner of this bot can add an API key in `config.yaml`'
        )

    return commands.check(predicate)


class Random(commands.Cog):
    """Commands to get something random, like colors or images!"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        if bot.config['unsplash_api_key']:
            self.unsplash = Unsplash(bot.config['unsplash_api_key'])
        else:
            self.unsplash = None

        self.cached_random_photos: List[Photo] = []

    @commands.group(invoke_without_command=True)
    async def random(self, ctx: utils.CustomContext):
        await ctx.send_help(ctx.command)

    @random.command(aliases=['user'])
    async def member(self, ctx: utils.CustomContext, include_bots=False):
        """Shows a random member from this server!"""

        member = random.choice([m for m in ctx.guild.members if not m.bot or m.bot == include_bots])

        embed = utils.create_embed(
            ctx.author,
            title='Random member from server!',
            description=f'{member.mention} - (ID: {member.id})',
            thumbnail=member.display_avatar
        )

        await ctx.send(embed=embed)

    @random.command(aliases=['colour'])
    async def color(self, ctx: utils.CustomContext):
        """Shows a random color!"""

        alias = ctx.invoked_with.lower()
        color = discord.Color.random()

        buffer = await self.bot.loop.run_in_executor(None, utils.solid_color_image, color.to_rgb())
        file = discord.File(filename="color.png", fp=buffer)

        embed = utils.create_embed(
            ctx.author,
            title=f'Showing random {alias}:',
            color=color,
            thumbnail="attachment://color.png"
        )

        embed.add_field(name='Hex:', value=f'`{color}`')
        embed.add_field(name='Int:', value=f'`{str(color.value).zfill(8)}`')
        embed.add_field(name='RGB:', value=f'`{color.to_rgb()}`')

        await ctx.send(file=file, embed=embed)

    @commands.group(invoke_without_command=True)
    async def unsplash(self, ctx: utils.CustomContext):
        await ctx.send_help(ctx.command)

    @check_unsplash()
    @unsplash.command(name='random', aliases=['rdm'])
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def rdm(self, ctx: utils.CustomContext):
        """Gets a random photo from the Unsplash API!"""

        if not self.cached_random_photos:
            self.cached_random_photos = await self.unsplash.random(content_filter='high', count=30)

        image: Photo = self.cached_random_photos.pop(0)

        description = f'"{image.description or image.alt_description}"\n\n' \
                      f'*Photo by [{image.user.name}](https://unsplash.com/@{image.user.username}{utm_params}) on ' \
                      f'[Unsplash](https://unsplash.com/{utm_params})*'

        embed = utils.create_embed(
            ctx.author,
            title='Unsplash Image',
            description=description,
            image=image.urls.regular,
            color=image.color,
            timestamp=image.created_at
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def fox(self, ctx: utils.CustomContext):
        """Gets a random fox from randomfox.ca"""

        url = await get_pic('https://randomfox.ca/floof/', ctx, key='image')
        embed = utils.create_embed(ctx.author, title=f'Random fox picture!:', image=url)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def duck(self, ctx: utils.CustomContext):
        """Gets a random duck from random-d.uk"""

        url = await get_pic('https://random-d.uk/api/v2/quack', ctx, key='url')
        embed = utils.create_embed(ctx.author, title=f'Random duck picture!:', image=url)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def dog(self, ctx: utils.CustomContext):
        """Gets a random dog from random.dog"""

        url = await get_pic('https://random.dog/woof.json?filter=mp4', ctx, key='url')
        embed = utils.create_embed(ctx.author, title=f'Random dog picture!:', image=url)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def hug(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries hugging, because why not?"""

        embed = await furry_image(ctx, user, 'hug', 'hug')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def boop(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries booping eachother, because why not?"""

        embed = await furry_image(ctx, user, 'boop', 'boop')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def hold(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries holding eachother, because why not?"""

        embed = await furry_image(ctx, user, 'hold', 'hold')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def kiss(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries kissing, because why not?"""

        embed = await furry_image(ctx, user, 'kiss', 'kiss', 'kisses')

        await ctx.send(embed=embed)

    @commands.command(aliases=['licc'])
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def lick(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Get picture of furries licking eachother, because why not?"""

        embed = await furry_image(ctx, user, 'lick', 'lick')

        await ctx.send(embed=embed)

    async def cog_command_error(self, ctx: utils.CustomContext, error: Exception) -> None:
        embed = None

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, utils.MissingAPIKey):
            embed = utils.create_embed(
                ctx.author,
                title='Bot missing API key!',
                description=str(error),
                color=discord.Color.red()
            )

        if isinstance(error, (UnsplashException, ClientError)):
            embed = utils.create_embed(
                ctx.author,
                title='Error while using api!',
                description='For some reason an error happened, maybe the API is down?',
                color=discord.Color.red()
            )

        if embed:
            return await ctx.send(embed=embed)

        ctx.uncaught_error = True


def setup(bot):
    bot.add_cog(Random(bot))
