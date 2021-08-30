import discord
from discord.ext import commands

from typing import List
from unsplash import Unsplash, Photo

import utils

utm_params = '?utm_source=discord_bot_doggie_bot&utm_medium=referral'


async def get_pic(url: str, ctx: utils.CustomContext, key: str, name: str) -> discord.Embed:
    async with ctx.bot.session.get(url) as resp:
        data = await resp.json()

    image_url = data[key]

    return utils.create_embed(ctx.author, title=f'Random {name} pic:', image=image_url)


def check_unsplash():
    def predicate(ctx):
        if ctx.bot.config['unsplash_api_key']:
            return True

        raise utils.MissingAPIKey(
            'The Unsplash API key is missing!'
            'The owner of this bot can add an API key in `config.yaml`'
        )

    return commands.check(predicate)


class Images(commands.Cog):
    """Commands that have to do with images!"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        if bot.config['unsplash_api_key']:
            self.unsplash = Unsplash(bot.config['unsplash_api_key'])
        else:
            self.unsplash = None

        self.cached_random_photos: List[Photo] = []

    @commands.group(invoke_without_command=True)
    async def unsplash(self, ctx: utils.CustomContext):
        await ctx.send_help(ctx.command)

    @check_unsplash()
    @unsplash.command(aliases=['rdm'])
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def random(self, ctx: utils.CustomContext):
        """Gets a random photo from the Unsplash API!"""

        if not self.cached_random_photos:
            self.cached_random_photos = await self.unsplash.random(content_filter='high', count=30)

        image: Photo = self.cached_random_photos.pop(0)

        print(len(self.cached_random_photos))

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

        embed = await get_pic('https://randomfox.ca/floof/', ctx, key='image', name='fox')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def duck(self, ctx: utils.CustomContext):
        """Gets a random duck from random-d.uk"""

        embed = await get_pic('https://random-d.uk/api/v2/quack', ctx, key='url', name='duck')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def dog(self, ctx: utils.CustomContext):
        """Gets a random dog from random.dog"""

        embed = await get_pic('https://random.dog/woof.json?filter=mp4', ctx, key='url', name='dog')

        await ctx.send(embed=embed)

    @dog.error
    @duck.error
    @fox.error
    @random.error
    @unsplash.error
    async def api_error(self, ctx: utils.CustomContext, error):
        if isinstance(error, utils.MissingAPIKey):
            embed = utils.create_embed(
                ctx.author,
                title='Bot missing API key!',
                description=str(error),
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Error while using api!',
            description='For some reason an error happened, maybe the API is down?',
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Images(bot))
