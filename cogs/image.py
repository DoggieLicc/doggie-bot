import discord
from discord.ext import commands

import aiohttp
from typing import List
from unsplash import Unsplash, Photo

import utils

utm_params = '?utm_source=discord_bot_doggie_bot&utm_medium=referral '


class Images(commands.Cog):
    """Commands that have to do with images!"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        self.unsplash = Unsplash(bot.config['unsplash_api_key'])

        self.cached_random_photos: List[Photo] = []

    @commands.group(invoke_without_command=True)
    async def unsplash(self, ctx: utils.CustomContext):
        await ctx.send_help(ctx.command)

    @unsplash.command()
    @commands.cooldown(10, 60, commands.BucketType.user)
    async def random(self, ctx: commands.Context):
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
    async def fox(self, ctx: commands.Context):
        """Gets a random fox from randomfox.ca"""

        async with aiohttp.ClientSession() as session:
            async with session.get('https://randomfox.ca/floof/') as resp:
                data = await resp.json()

        fox_url = data['image']

        embed = utils.create_embed(ctx.author, title='Random fox pic', image=fox_url, color=discord.Color.orange())

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Images(bot))
