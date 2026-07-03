import inspect
from io import StringIO

from discord import app_commands, Permissions, User, File
from discord.ext import commands
from discord.utils import oauth_url

import utils
from utils import CustomBot, CustomContext

class Misc(commands.Cog, name='Misc'):
    """Commands that show info about the bot"""

    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    @commands.hybrid_command(aliases=['i', 'ping', 'about'])
    async def info(self, ctx: CustomContext):
        """Shows information for the bot!"""

        invite_url = oauth_url(self.bot.application_id, permissions=Permissions(4513770781404358))

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
            value="[Support Server](https://discord.gg/d7dgReCnRR)",
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
            value=f'{round(1000 * self.bot.latency)} ms',
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['report', 'bug', 'suggestion'])
    @commands.cooldown(3, 86_400, commands.BucketType.user)
    @app_commands.describe(suggestion='What you want to suggest!')
    async def suggest(self, ctx: CustomContext, suggestion: str):
        """Send a suggestion or bug report to the bot owner!"""

        owner: User = await self.bot.get_owner()

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

    @commands.hybrid_command(aliases=['code'])
    @app_commands.describe(command='Specify a command to get the source code of that command')
    async def source(self, ctx: CustomContext, command: str | None = None):
        """Look at the code of this bot!"""

        if command is None:
            embed = utils.create_embed(
                ctx.author,
                title='Source Code:',
                description='[Github for **Doggie Bot**](https://github.com/DoggieLicc/doggie-bot)'
            )

            return await ctx.send(embed=embed)

        a_commands = command.lower().strip('/').split(maxsplit=2)

        obj = self.bot.tree.get_command(a_commands[0])

        if isinstance(obj, app_commands.Group) and len(a_commands) > 1:
            obj = obj.get_command(a_commands[1])

            if isinstance(obj, app_commands.Group) and len(a_commands) > 2:
                obj = obj.get_command(a_commands[2])

        if obj is None:
            raise utils.DoggieBotException('Command not found!', f'The command `{command}` wasn\'t found in this bot.')

        if isinstance(obj, app_commands.Group):
            raise utils.DoggieBotException('Not a command!', f'`/{obj.qualified_name}` is a command group, and doesn\'t have source code!')

        src = obj.callback.__code__

        lines, _ = inspect.getsourcelines(src)
        if lines[0].startswith(' '*4):
            src_code = ''.join([l[4:] if l.startswith(' '*4) else l for l in lines])
        else:
            src_code = ''.join(lines)

        buffer = StringIO(src_code)

        file = File(fp=buffer, filename=f'{command.replace(" ", "_").lower()}.py')

        await ctx.send(f'Here you go, {ctx.author.mention}. (You should view this on a PC)', file=file)


async def setup(bot):
    await bot.add_cog(Misc(bot))
