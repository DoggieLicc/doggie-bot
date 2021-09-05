import discord
import random

from discord.ext import commands
import utils


class Random(commands.Cog):
    """Let luck decide your fate"""

    def __init__(self, bot):
        self.bot: utils.CustomBot = bot

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


def setup(bot):
    bot.add_cog(Random(bot))
