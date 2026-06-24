import random

from discord import app_commands, Interaction, Color, File
from discord.ext import commands
from loguru import logger

from unsplash import Unsplash, Photo
import utils

UTM_PARAMS = '?utm_source=discord_bot_doggie_bot&utm_medium=referral'

class RandomCog(commands.GroupCog, group_name='random'):
    """Commands to get something random, like colors or images!"""
    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        if bot.config['unsplash_api_key']:
            self.unsplash = Unsplash(bot.config['unsplash_api_key'])
            self.app_command.add_command(
                app_commands.Command(
                    name='unsplash',
                    description=self.unsplash_cmd.__doc__,
                    callback=self.unsplash_cmd
                )
            )
        else:
            self.unsplash = None
            logger.warning('UNSPLASH_API_KEY Environment variable missing. /unsplash command will not be registered')

        self.cached_random_photos: list[Photo] = []

    @utils.not_user_integration()
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
        color = Color.random()

        buffer = await self.bot.loop.run_in_executor(None, utils.solid_color_image, color.to_rgb())
        file = File(filename="color.png", fp=buffer)

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

async def setup(bot):
    await bot.add_cog(RandomCog(bot))
