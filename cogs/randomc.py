import random

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from aiohttp import ClientError

from unsplash import Unsplash, Photo, UnsplashException
import utils

UTM_PARAMS = '?utm_source=discord_bot_doggie_bot&utm_medium=referral'

def check_unsplash():
    def predicate(interaction):
        if interaction.client.config['unsplash_api_key']:
            return True

        raise utils.MissingAPIKey(
            'The Unsplash API key is missing!'
            'The owner of this bot can add an API key in `config.yaml`'
        )

    return app_commands.check(predicate)


class RandomCog(commands.GroupCog, group_name='random'):
    """Commands to get something random, like colors or images!"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        if bot.config['unsplash_api_key']:
            self.unsplash = Unsplash(bot.config['unsplash_api_key'])
        else:
            self.unsplash = None

        self.cached_random_photos: list[Photo] = []

    @app_commands.command()
    @app_commands.describe(include_bots='Whether or not to include bots (Default: False)')
    async def member(self, interaction: Interaction, include_bots: bool = False):
        """Shows a random member from this server!"""

        member = random.choice([m for m in interaction.guild.members if not m.bot or m.bot == include_bots])

        embed = utils.create_embed(
            interaction.user,
            title='Random member from server!',
            description=f'{member.mention} - (ID: {member.id})',
            thumbnail=member.display_avatar
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def color(self, interaction: Interaction):
        """Shows a random color!"""
        color = discord.Color.random()

        buffer = await self.bot.loop.run_in_executor(None, utils.solid_color_image, color.to_rgb())
        file = discord.File(filename="color.png", fp=buffer)

        embed = utils.create_embed(
            interaction.user,
            title='Showing random color:',
            color=color,
            thumbnail="attachment://color.png"
        )

        embed.add_field(name='Hex:', value=f'`{color}`')
        embed.add_field(name='Int:', value=f'`{str(color.value).zfill(8)}`')
        embed.add_field(name='RGB:', value=f'`{color.to_rgb()}`')

        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name='unsplash')
    @check_unsplash()
    async def unsplash_cmd(self, interaction: Interaction):
        """Gets a random photo from the Unsplash API!"""

        if not self.cached_random_photos:
            self.cached_random_photos = await self.unsplash.random(content_filter='high', count=30)

        image: Photo = self.cached_random_photos.pop(0)

        description = f'"{image.description or image.alt_description}"\n\n' \
                      f'*Photo by [{image.user.name}](https://unsplash.com/@{image.user.username}{UTM_PARAMS}) on ' \
                      f'[Unsplash](https://unsplash.com/{UTM_PARAMS})*'

        embed = utils.create_embed(
            interaction.user,
            title='Unsplash Image',
            description=description,
            image=image.urls.regular,
            color=image.color,
            timestamp=image.created_at
        )

        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: Interaction, error: Exception) -> None:
        embed = None

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, utils.MissingAPIKey):
            embed = utils.create_embed(
                interaction.user,
                title='Bot missing API key!',
                description=str(error),
                color=discord.Color.red()
            )

        if isinstance(error, (UnsplashException, ClientError)):
            embed = utils.create_embed(
                interaction.user,
                title='Error while using api!',
                description='For some reason an error happened, maybe the API is down?',
                color=discord.Color.red()
            )

        if embed:
            await interaction.response.send_message(embed=embed)
            return

        await interaction.client.tree.on_error(interaction, error)

async def setup(bot):
    await bot.add_cog(RandomCog(bot))
