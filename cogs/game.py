import discord
import utils

from typing import Optional

from discord.ext import commands

from mojang import API as Mojang
from osu import OsuApi, OsuApiException
from datetime import timedelta

mojang_api = Mojang()

def sync_minecraft(ctx, account):
    try:
        if utils.is_uuid4(account):
            uuid = account
        else:
            uuid = mojang_api.get_uuid(account)

        profile = mojang_api.get_profile(uuid)
        if not profile:
            return utils.create_embed(
                ctx.author,
                title='Error!',
                description='Account not found!',
                color=discord.Color.red()
            )

    except Exception as e:
        return utils.create_embed(
            ctx.author,
            title='Error!',
            description=f'Can\'t lookup account! (API down?) ({e})',
            color=discord.Color.red()
        )

    embed = utils.create_embed(
        ctx.author,
        title='Minecraft account info:',
        thumbnail=f'https://mc-heads.net/body/{account}.png'
    )

    embed.add_field(name='Current Username:', value=discord.utils.escape_markdown(profile.name), inline=False)
    embed.add_field(name='Profile UUID:', value=profile.id, inline=False)

    embed.add_field(
        name='Skin:',
        value=f'[Download Skin ({"Steve Type" if not profile.skin_variant == "slim" else "Alex Type"})]'
              f'({profile.skin_url})' if profile.skin_url else 'No skin',
        inline=False
    )

    embed.add_field(name='Is legacy account?:', value='Yes' if profile.is_legacy_profile else 'No', inline=False)

    # Dream's UUID
    if profile.id == 'ec70bcaf702f4bb8b48d276fa52a780c':
        embed.set_thumbnail(
            url='https://media.discordapp.net/attachments/632730054396215299/827393984875855982/ForsenCD-emote.jpg'
        )

    return embed


class ModeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, mode: str):
        if not mode:
            return 'osu'

        mode = mode.lower()
        if mode in ['s', 'standard', 'osu', 'osu!', 'std', '0']:
            return 'osu'
        elif mode in ['taiko', 't', 'osu!taiko', '1']:
            return 'taiko'
        elif mode in ['c', 'catch', 'ctb', 'osu!catch', '2']:
            return 'fruits'
        elif mode in ['m', 'mania', 'osu!mania', '3']:
            return 'mania'
        else:
            return 'osu'


def check_osu():
    def predicate(ctx):
        if ctx.bot.config['osu_client_id'] and ctx.bot.config['osu_client_secret']:
            return True

        raise utils.MissingAPIKey(
            'The osu!api key is missing!'
            'The owner of this bot can add an API key in `config.yaml`'
        )

    return commands.check(predicate)


class Games(commands.Cog, name="Games"):
    """Commands used to get info for video-game accounts"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

        if bot.config['osu_client_id'] and bot.config['osu_client_secret']:
            self.osu_api = OsuApi(
                client_id=bot.config['osu_client_id'],
                client_secret=bot.config['osu_client_secret']
            )
        else:
            self.osu_api = None

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["mc"])
    async def minecraft(self, ctx: utils.CustomContext, account):
        """Gets info of minecraft accounts using current username or their UUID"""

        async with ctx.channel.typing():
            embed = await self.bot.loop.run_in_executor(None, sync_minecraft, ctx, account)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def osu(self, ctx: utils.CustomContext):
        await ctx.send_help(ctx.command)

    @osu.command(aliases=['user'])
    @check_osu()
    @commands.cooldown(15, 60, commands.BucketType.user)
    async def account(self, ctx: utils.CustomContext, account, gamemode: Optional[ModeConverter] = 'osu'):
        """Gets info of osu! accounts! You can also specify a gamemode to get stats for that gamemode!"""

        user = await self.osu_api.fetch_user(user=account, mode=gamemode)

        embed = utils.create_embed(
            ctx.author,
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
                  f'**# of SH grades:** {grade_counts.ssh}\n'
                  f'**# of SS grades:** {grade_counts.ss}\n'
                  f'**# of SSH grades:** {grade_counts.ssh}\n'
        )

        await ctx.send(embed=embed)

    @osu.command(aliases=['bm'])
    @check_osu()
    @commands.cooldown(15, 60, commands.BucketType.user)
    async def beatmap(self, ctx: utils.CustomContext, beatmap_id: int):
        """Gets a beatmap from a beatmap ID! (Not a beatmap set, an individual beatmap)"""

        beatmap = await self.osu_api.lookup_beatmap(beatmap_id=beatmap_id)
        beatmap_set = beatmap.beatmapset

        embed = utils.create_embed(
            ctx.author,
            image=beatmap_set.covers['cover'] or None,
            url=beatmap.url,
            title=f'Showing info for osu! beatmap set!:',
            description=f'**Title:** {beatmap_set.title}\n'
                        f'**Description:** {beatmap_set.description or "No description"}\n'
                        f'**Beatmap set ID:** {beatmap_set.id}\n'
                        f'**Artist:** {beatmap_set.artist}\n'
                        f'**Creator:** {beatmap_set.creator}\n'
                        fr'**\# of plays:** {beatmap_set.play_count}\n'
                        fr'**\# of favorites:** {beatmap_set.favourite_count}\n'
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

        await ctx.send(embed=embed)

    @beatmap.error
    @account.error
    @osu.error
    async def osu_error(self, ctx: utils.CustomContext, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, OsuApiException):
            embed = utils.create_embed(
                ctx.author,
                title='Error while getting from osu!api',
                description='Either the api is down, or you put invalid arguments!\n'
                            '[**osu!status**](https://status.ppy.sh/)',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        if isinstance(error, utils.MissingAPIKey):
            embed = utils.create_embed(
                ctx.author,
                title='Bot missing API key!',
                description=str(error),
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        ctx.uncaught_error = True


async def setup(bot):
    await bot.add_cog(Games(bot))
