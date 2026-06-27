import random
from dataclasses import dataclass
from typing import Callable
from inspect import Parameter, Signature

from discord import app_commands, Interaction, Color, File, User
from discord.ext import commands
from loguru import logger

from unsplash import Unsplash, Photo
import utils
from utils import CustomBot

UTM_PARAMS = '?utm_source=discord_bot_doggie_bot&utm_medium=referral'

async def get_pic(url: str, interaction: Interaction[CustomBot], key: str) -> str:
    if not interaction.client.session:
        return ''

    async with interaction.client.session.get(url) as resp:
        data = await resp.json()

    return data[key]


async def furry_image(interaction: Interaction[CustomBot], user: User | None, endpoint: str, action: str, a2: str = None):
    if not user or user == interaction.user:
        msg = f'{interaction.user.mention} has no one to {action} :('
    elif user.bot:
        msg = f'{interaction.user.mention} tries to {action} a bot... sad :('
    else:
        msg = f'{interaction.user.mention} {action + "s" if not a2 else a2} {user.mention}!'

    url = await get_pic(f'https://v2.yiff.rest/furry/{endpoint}', interaction, key='images')
    return utils.create_embed(interaction.user, title=f'Furry {action}!', description=msg, image=url[0]['url'])


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
            Parameter(
                "interaction",
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Interaction,
            ),
            Parameter(
                "user",
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=User | None,
                default=None
            )
        ]

        async def callback(*args, **kwargs):
            bound = callback.__signature__.bind(*args, **kwargs)  # type: ignore

            interaction: Interaction[CustomBot] = bound.arguments["interaction"]
            user: User | None = bound.arguments["user"]

            embed = await furry_image(interaction, user, self.action1, self.action2)

            await interaction.response.send_message(embed=embed)

        callback.__name__ = str(self.action1)
        callback.__signature__ = Signature(params)  # type: ignore
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
    FurryCommand('lick')
]


class RandomCog(commands.GroupCog, group_name='random'):
    """Commands to get something random, like colors or images!"""
    def __init__(self, bot):
        self.bot: CustomBot = bot

        if bot.config['unsplash_api_key'] and self.app_command:
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

        furry_group = app_commands.Group(name='furry', description='Get random furry images! (SFW)', parent=self.app_command)

        for furry_command in FURRY_COMMANDS:
            furry_group.add_command(
                app_commands.Command(
                    name=furry_command.action1,
                    description=furry_command.description,
                    callback=furry_command.get_callback()
                )
            )

    @utils.not_user_integration()
    @app_commands.command()
    @app_commands.describe(include_bots='Whether or not to include bots (Default: False)')
    async def member(self, interaction: Interaction[CustomBot], include_bots: bool = False):
        """Shows a random member from this server!"""

        if not interaction.guild:
            return

        member = random.choice([m for m in interaction.guild.members if not m.bot or m.bot == include_bots])

        embed = utils.create_embed(
            interaction.user,
            title='Random member from server!',
            description=f'{member.mention} - (ID: {member.id})',
            thumbnail=member.display_avatar
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def color(self, interaction: Interaction[CustomBot]):
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

    @app_commands.command()
    async def duck(self, interaction: Interaction[CustomBot]):
        """Gets a random duck from random-d.uk"""

        url = await get_pic('https://random-d.uk/api/v2/quack', interaction, key='url')
        embed = utils.create_embed(interaction.user, title='Random duck picture!:', image=url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def dog(self, interaction: Interaction[CustomBot]):
        """Gets a random dog from random.dog"""

        url = await get_pic('https://random.dog/woof.json?filter=mp4', interaction, key='url')
        embed = utils.create_embed(interaction.user, title='Random dog picture!:', image=url)

        await interaction.response.send_message(embed=embed)

    async def unsplash_cmd(self, interaction: Interaction[CustomBot]):
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
