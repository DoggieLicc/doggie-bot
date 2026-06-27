from typing import Literal
from datetime import timedelta

from discord import app_commands, Interaction, Embed
from discord.utils import escape_markdown
from discord.ext.commands import GroupCog
from mojang import API as Mojang
from loguru import logger

from osu import OsuApi
import utils

mojang_api = Mojang()

def sync_minecraft(interaction: Interaction, account: str) -> Embed:
    try:
        if utils.is_uuid4(account):
            uuid = account
        else:
            uuid = mojang_api.get_uuid(account)

        profile = mojang_api.get_profile(str(uuid))
        if not profile:
            raise utils.DoggieBotException('Account not found!', 'Couldn\'t find a Minecraft account with this name.')

    # pylint: disable=broad-exception-caught
    except Exception as e:
        raise utils.DoggieBotException('Lookup error!', 'Lookup failed. (Mojang API down?)') from e

    embed = utils.create_embed(
        interaction.user,
        title='Minecraft account info:',
        thumbnail=f'https://mc-heads.net/body/{account}.png'
    )

    embed.add_field(name='Current Username:', value=escape_markdown(profile.name), inline=False)
    embed.add_field(name='Profile UUID:', value=profile.id, inline=False)

    embed.add_field(
        name='Skin:',
        value=f'[Download Skin ({"Steve Type" if profile.skin_variant != "slim" else "Alex Type"})]'
              f'({profile.skin_url})' if profile.skin_url else 'No skin',
        inline=False
    )

    # Dream's UUID
    if profile.id == 'ec70bcaf702f4bb8b48d276fa52a780c':
        embed.set_thumbnail(
            url='https://media.discordapp.net/attachments/632730054396215299/827393984875855982/ForsenCD-emote.jpg'
        )

    return embed


osu_modes = Literal['osu', 'taiko', 'fruits', 'mania']

class Games(GroupCog, group_name='game'):
    """Commands used to get info for video-game accounts"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        if bot.config['osu_client_id'] and bot.config['osu_client_secret']:
            self.osu_api = OsuApi(
                client_id=bot.config['osu_client_id'],
                client_secret=bot.config['osu_client_secret']
            )

            osu_group = app_commands.Group(name='osu', description='Commands for osu!', parent=self.app_command)

            osu_group.add_command(
                app_commands.Command(
                    name='account',
                    description=self.account.__doc__ or '…',
                    callback=self.account
                )
            )

            osu_group.add_command(
                app_commands.Command(
                    name='beatmap',
                    description=self.beatmap.__doc__ or '…',
                    callback=self.beatmap
                )
            )
        else:
            self.osu_api = None
            logger.warning('OSU_CLIENT_ID or OSU_CLIENT_SECRET environment variables missing. /game osu commands will not be registered.')


    @app_commands.command()
    @app_commands.describe(account='The username or UUID of the Java Minecraft account')
    async def minecraft(self, interaction: Interaction, account: str):
        """Get info of a Java Minecraft account using current username or their UUID"""

        await interaction.response.defer(thinking=True)

        embed = await self.bot.loop.run_in_executor(None, sync_minecraft, interaction, account)
        await interaction.edit_original_response(embed=embed)

    @app_commands.describe(account='The username of the osu! account to view')
    @app_commands.describe(gamemode='The gamemode to get gamestats for, defaults to regular osu')
    async def account(self, interaction: Interaction, account: str, gamemode: osu_modes | None = 'osu'):
        """Gets info of osu! accounts! You can also specify a gamemode to get stats for that gamemode!"""
        if not self.osu_api:
            raise utils.DoggieBotException('Unable to load osu! api!', 'The osu! api module wasn\'t loaded.')

        await interaction.response.defer(thinking=True)
        user = await self.osu_api.fetch_user(user=account, mode=gamemode)

        embed = utils.create_embed(
            interaction.user,
            title='Showing info for osu! account!',
            url=f'https://osu.ppy.sh/users/{user.id}',
            thumbnail=user.avatar_url,
            image=user.cover_url,
            description=f'**Username:** {user.username}\n'
                        f'**ID:** {user.id}\n'
                        f'**Supporter?:** {"Yes" if user.is_supporter else "No"}\n'
                        f'**Deleted?** {"Yes" if user.is_deleted else "No"}\n'
                        f'**Active?:** {"Yes" if user.is_active else "No"}\n'
                        f'**Country:** {user.country_code}\n'
                        f'**Joined at:** {utils.user_friendly_dt(user.join_date)}\n'
                        f'**Last seen:** {utils.user_friendly_dt(user.last_visit) if user.last_visit else "Unknown"}'
        )

        stats = user.statistics

        embed.add_field(
            inline=False,
            name=f'Statistics for osu!{gamemode if gamemode != "osu" else "standard"}:',
            value=f'**Level:** {stats.level.current} '
                f'({stats.level.progress}% progress to level {stats.level.current + 1})\n'
                f'**Hit accuracy:** {stats.hit_accuracy: .2f}%\n'
                f'**Max combo:** {stats.maximum_combo}x\n'
                f'**Performance points:** {stats.pp: .2f} pp\n'
                f'**Global rank:** {stats.global_rank}\n'
                f'**# of maps played:** {stats.play_count}\n'
                f'**Ranked score:** {stats.ranked_score / 1_000_000: .2f}m\n'
                f'**Total hits:** {stats.total_hits / 1000: .2f}k\n\n',
        )

        grade_counts = stats.grade_counts

        embed.add_field(
            inline=False,
            name=f'Grade counts for osu!{gamemode if gamemode != "osu" else "standard"}:',
            value=f'**# of A grades:** {grade_counts.a}\n'
                f'**# of S grades:** {grade_counts.s}\n'
                f'**# of SH grades:** {grade_counts.sh}\n'
                f'**# of SS grades:** {grade_counts.ss}\n'
                f'**# of SSH grades:** {grade_counts.ssh}\n'
        )

        await interaction.edit_original_response(embed=embed)

    @app_commands.describe(beatmap_id='The ID of the beatmap you want to view.')
    async def beatmap(self, interaction: Interaction, beatmap_id: int):
        """Gets a beatmap from a beatmap ID!"""
        if not self.osu_api:
            raise utils.DoggieBotException('Unable to load osu! api!', 'The osu! api module wasn\'t loaded.')

        await interaction.response.defer(thinking=True)
        beatmap = await self.osu_api.lookup_beatmap(beatmap_id=beatmap_id)
        beatmap_set = beatmap.beatmapset
        if not beatmap_set:
            raise utils.DoggieBotException('Beatmap has no set!', 'This beatmap doesn\'t seem to belong to a beatmap set')

        embed = utils.create_embed(
            interaction.user,
            image=beatmap_set.covers['cover'] or None,
            url=beatmap.url,
            title='Showing info for osu! beatmap set!:',
            description=f'**Title:** {beatmap_set.title}\n'
                        f'**Description:** {beatmap_set.description or "No description"}\n'
                        f'**Beatmap set ID:** {beatmap_set.id}\n'
                        f'**Artist:** {beatmap_set.artist}\n'
                        f'**Creator:** {beatmap_set.creator}\n'
                        f'**\\# of plays:** {beatmap_set.play_count}\n'
                        f'**\\# of favorites:** {beatmap_set.favourite_count}\n'
                        f'**Submitted at:** {utils.user_friendly_dt(beatmap_set.submitted_date)}'
        )

        embed.add_field(
            name='Beatmap info:',
            value=f'**ID:** {beatmap.id}\n'
                f'**Gamemode:** osu!{beatmap.mode.name.lower()}\n'
                f'**Length:** {timedelta(seconds=beatmap.total_length)}\n'
                f'**Last updated:** {utils.user_friendly_dt(beatmap.last_updated)}\n'
                f'**Ranked status:** {beatmap.ranked.name.title()}\n'
                f'**Max combo:** {str(beatmap.max_combo) + "x" or "N/A"}\n'
                f'**# of plays:** {beatmap.playcount}\n'
                f'**# of passes:** {beatmap.passcount}'
        )

        embed.add_field(
            name='Beatmap difficulty:',
            value=f'**Difficulty:** {beatmap.difficulty_rating: .2f} {"★" * int(beatmap.difficulty_rating)}\n'
                f'**Approach rate:** {beatmap.ar: .2f}\n'
                f'**Circle size:** {beatmap.cs: .2f}\n'
                f'**Drain:** {beatmap.drain: .2f}\n'
                f'**Accuracy:** {beatmap.accuracy}\n\n'
                f'**# of circles:** {beatmap.count_circles}\n'
                f'**# of sliders:** {beatmap.count_sliders}\n'
                f'**# of spinners:** {beatmap.count_spinners}'
        )

        await interaction.edit_original_response(embed=embed)


async def setup(bot):
    game_cog = Games(bot)
    await bot.add_cog(game_cog)
