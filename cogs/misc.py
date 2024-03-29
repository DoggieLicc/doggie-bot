import discord
import utils
import inspect

from discord.ext import commands
from io import StringIO


class Misc(commands.Cog):
    """Commands that show info about the bot"""

    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @commands.command(aliases=['i', 'ping'])
    async def info(self, ctx: utils.CustomContext):
        """Shows information for the bot!"""

        invite_url = discord.utils.oauth_url(ctx.me.id, permissions=discord.Permissions(1375866285270))

        embed = utils.create_embed(
            ctx.author,
            title='Info for Doggie Bot!',
            description='This bot is a multi-purpose bot!'
        )

        embed.add_field(
            name="Invite this bot!",
            value=f"[Invite]({invite_url})",
            inline=False
        )

        embed.add_field(
            name="Join support server!",
            value="[Support Server](https://discord.gg/fzzeScC6XC)",
            inline=False
        )

        embed.add_field(
            name='Bot Creator:',
            value='[@doggielicc](https://github.com/DoggieLicc/)',
            inline=True
        )

        embed.add_field(
            name='Source Code:',
            value='[Github Repo](https://github.com/DoggieLicc/doggie-bot)'
        )

        embed.add_field(
            name='Bot Online Since:',
            value=utils.user_friendly_dt(self.bot.start_time),
            inline=False
        )

        embed.add_field(
            name='Ping:',
            value='{} ms'.format(round(1000 * self.bot.latency)),
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.cooldown(3, 86_400, commands.BucketType.user)
    @commands.command(aliases=['report', 'bug'])
    async def suggest(self, ctx: utils.CustomContext, *, suggestion):
        """Send a suggestion or bug report to the bot owner!"""

        owner: discord.User = await self.bot.get_owner()

        owner_embed = utils.create_embed(
            ctx.author,
            title='New suggestion!:',
            description=suggestion
        )

        await owner.send(embed=owner_embed)

        user_embed = utils.create_embed(
            ctx.author,
            title=f'👍 Suggestion has been sent to {owner}! 💖'
        )

        await ctx.send(embed=user_embed)

    @commands.command(aliases=['code'])
    async def source(self, ctx, *, command: str = None):
        """Look at the code of this bot!"""

        if command is None:
            embed = utils.create_embed(
                ctx.author,
                title='Source Code:',
                description='[Github for **Doggie Bot**](https://github.com/DoggieLicc/doggie-bot)'
            )

            return await ctx.send(embed=embed)

        if command == 'help':
            src = type(self.bot.help_command)
        else:
            obj = self.bot.get_command(command.replace('.', ' ').lower())
            if obj is None:
                embed = utils.create_embed(
                    ctx.author,
                    title='Command not found!',
                    description='This command wasn\'t found in this bot.',
                    color=discord.Color.red()
                )

                return await ctx.send(embed=embed)

            src = obj.callback.__code__

        lines, _ = inspect.getsourcelines(src)
        src_code = ''.join(lines)

        buffer = StringIO(src_code)

        file = discord.File(fp=buffer, filename=f'{command.replace(" ", "_").lower()}.py')

        await ctx.send(f'Here you go, {ctx.author.mention}. (You should view this on a PC)', file=file)


async def setup(bot):
    await bot.add_cog(Misc(bot))
