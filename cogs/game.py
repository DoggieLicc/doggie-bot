import pandas
import matplotlib
import matplotlib.pyplot as plt

from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from mojang import MojangAPI as Mojang
from io import BytesIO
from osu import OsuApi, OsuApiException

from utils import CustomBot, CustomContext, create_embed, is_uuid4, user_friendly_dt

from datetime import timedelta


matplotlib.use('Agg')
plt.style.use('dark_background')
plt.tight_layout()


def render_failtimes(data) -> discord.File:

    df = pandas.DataFrame(
        {
            'percent': range(0, 100),
            'Fail': data['fail'],
            'Retry': data['exit']
        },
        columns=['percent', 'Fail', 'Retry'],
    )

    df.set_index('percent', inplace=True)

    plot_bar = df.plot.bar(
        rot=0,
        color={
            'Retry': '#f2c323',
            'Fail': '#c1681c'
        },
        title='Where players failed on this beatmap:',
        xlabel='% of beatmap played',
        ylabel='Failure rate %',
        legend=True,
        xticks=range(0, 101, 10),
        width=1,
        stacked=True,
    )

    plot_bar.get_figure()
    plot_bar_img = BytesIO()
    plt.savefig(plot_bar_img)
    plot_bar_img.seek(0)

    return discord.File(plot_bar_img, filename='beatmapfails.png')


def sync_minecraft(ctx, account):
    try:
        if is_uuid4(account):
            uuid = account
        else:
            uuid = Mojang.get_uuid(account)

        profile = Mojang.get_profile(uuid)
        if not profile:
            return create_embed(ctx.author, title="Error!", description="Account not found!", color=0xeb4034)
        name_history = Mojang.get_name_history(uuid)
    except Exception:
        return create_embed(ctx.author, title="Error!", description="Can't lookup account! (API down?)", color=0xeb4034)

    past_names = [data['name'] for data in name_history if data['name'] != profile.name]

    embed = create_embed(
        ctx.author,
        title="Minecraft account info:",
        thumbnail="https://cdn.discordapp.com/attachments/632730054396215299/825080584451391529/grass.png")

    embed.add_field(name="Current Username:", value=discord.utils.escape_markdown(profile.name), inline=False)
    embed.add_field(name="Profile UUID:", value=profile.id, inline=False)
    embed.add_field(name="Past Usernames:",
                    value=(discord.utils.escape_markdown(", ".join(past_names)) if past_names else "No past usernames"),
                    inline=False)
    embed.add_field(name="Skin:",
                    value=f"[Download Skin ({'Steve Type' if not profile.skin_model == 'slim' else 'Alex Type'})]"
                          f"({profile.skin_url})" if profile.skin_url else "No skin",
                    inline=False)
    embed.add_field(name="Is legacy account?:", value="Yes" if profile.is_legacy_profile else "No", inline=False)

    # Dream's UUID
    if profile.id == 'ec70bcaf702f4bb8b48d276fa52a780c':
        embed.set_thumbnail(
            url="https://media.discordapp.net/attachments/632730054396215299/827393984875855982/ForsenCD-emote.jpg")
    return embed


class ModeConverter(commands.Converter):
    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    async def convert(self, ctx: commands.Context, mode: str):

        if not mode:
            return "osu"

        mode = mode.lower()
        if mode in ["s", "standard", "osu", "osu!", "std", "0"]:
            return "osu"
        elif mode in ["taiko", "t", "osu!taiko", "1"]:
            return "taiko"
        elif mode in ["c", "catch", "ctb", "osu!catch", "2"]:
            return "fruits"
        elif mode in ["m", "mania", "osu!mania", "3"]:
            return "mania"
        else:
            return "osu"


class GameCog(commands.Cog, name="Games"):
    """Commands used to get info for video-game accounts"""

    def __init__(self, bot):
        self.bot: CustomBot = bot

        self.osu_api = OsuApi(
            client_id=bot.config['osu_client_id'],
            client_secret=bot.config['osu_client_secret']
        )

    @commands.cooldown(1, 5, BucketType.user)
    @commands.command(aliases=["mc"])
    async def minecraft(self, ctx: CustomContext, account):
        """Gets info of minecraft accounts using current username or their UUID"""

        async with ctx.channel.typing():
            embed = await self.bot.loop.run_in_executor(None, sync_minecraft, ctx, account)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def osu(self, ctx: CustomContext):
        await ctx.send_help(ctx.command)

    @osu.command()
    @commands.cooldown(15, 60, BucketType.user)
    async def account(self, ctx: CustomContext, account, gamemode: Optional[ModeConverter] = 'osu'):
        """Gets info of osu! accounts! You can also specify a gamemode to get stats for that gamemode!"""

        user = await self.osu_api.fetch_user(user=account, mode=gamemode)

        embed = create_embed(
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
                        f'**Joined at:** {user_friendly_dt(user.join_date)}\n'
                        f'**Last seen:** {user_friendly_dt(user.last_visit)}'
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

    @osu.command()
    @commands.cooldown(15, 60, BucketType.user)
    async def beatmap(self, ctx: CustomContext, beatmap_id: int):
        """Gets a beatmap from a beatmap ID! (Not a beatmap set, an individual beatmap)"""

        beatmap = await self.osu_api.lookup_beatmap(beatmap_id=beatmap_id)
        beatmap_set = beatmap.beatmapset

        plot_img = await self.bot.loop.run_in_executor(None, render_failtimes, beatmap.failtimes)

        embed = create_embed(
            ctx.author,
            image=beatmap_set.covers['cover'] or discord.Embed.Empty,
            # url=beatmap.url,
            thumbnail='attachment://' + plot_img.filename,
            title=f'Showing info for osu! beatmap set!:',
            description=f'**Title:** {beatmap_set.title}\n'
                        f'**Description:** {beatmap_set.description or "No description"}\n'
                        f'**Beatmap set ID:** {beatmap_set.id}\n'
                        f'**Artist:** {beatmap_set.artist}\n'
                        f'**Creator:** {beatmap_set.creator}\n'
                        f'**# of plays:** {beatmap_set.play_count}\n'
                        f'**# of favorites:** {beatmap_set.favourite_count}\n'
                        f'**Submitted at:** {user_friendly_dt(beatmap_set.submitted_date)}'
        )

        embed.add_field(
            name='Beatmap info:',
            value=f'**ID:** {beatmap.id}\n'
                  f'**Gamemode:** osu!{beatmap.mode.name.lower()}\n'
                  f'**Length:** {timedelta(seconds=beatmap.total_length)}\n'
                  f'**Last updated:** {user_friendly_dt(beatmap.last_updated)}\n'
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

        await ctx.send(embed=embed, file=plot_img)

    @beatmap.error
    @account.error
    @osu.error
    async def osu_error(self, ctx: CustomContext, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, OsuApiException):
            embed = create_embed(
                ctx.author,
                title='Error while getting from osu!api',
                description='Either the api is down, or you put invalid arguments!\n'
                            '[**osu!status**](https://status.ppy.sh/)',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        raise error


def setup(bot):
    bot.add_cog(GameCog(bot))
