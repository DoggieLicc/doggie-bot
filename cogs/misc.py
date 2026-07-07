import inspect
from io import StringIO

from discord import app_commands, Permissions, User, File
from discord.ext import commands
from discord.utils import oauth_url

import utils
from utils import CustomBot, CustomContext

CHANGELOG = """### 7/6/2026 - Slash Commands Update!
The bot has gone through a rewrite, and now most commands are usuable through Discord's slash commands system!
* Most commands are usable as both slash commands and text commands
* Bot can be installed as an user app! Note that commands that require server-specific info won't work as an user app.
    - Slash commands' responses will be ephermeral if ran as an user app, or if the bot member doesn't have permissions to send messages in the channel normally.
* New config slash commands
* All `random` commands need to be ran as `random cmd`  when using text commands
* All `image` commands need to be ran as `random cmd`  when using text commands, pride specific commands as `image pride cmd`
* New system for image commands - You can use the `Select Image` message menu command, to use that image as the default
* `wikipedia` and `sendwebhook` commands removed.
* All menus now use components instead of reactions
* `timeout` and `remind` can now take `@time` timestamps
* `color` command will show all colors for multi-colored roles
* `saucenao` command set as NSFW-only
* Other general improvements"""

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
            description='This bot is a multi-purpose bot!\n\n[Terms of Service](https://gist.github.com/DoggieLicc/067c3a3b706ceb63906bc928d6e3b1bf) | [Privacy Policy](https://gist.github.com/DoggieLicc/92c14546f4da42e60969356fa3f97bdf)'
        )

        embed.add_field(
            name='Invite this bot!',
            value=f'[Invite]({invite_url})',
            inline=False
        )

        embed.add_field(
            name='Join support server!',
            value='[Support Server](https://discord.gg/d7dgReCnRR)',
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

        file = File(fp=buffer, filename=f'{command.replace(' ', '_').lower()}.py')

        await ctx.send(f'Here you go, {ctx.author.mention}. (You should view this on a PC)', file=file)


    @commands.hybrid_command()
    async def changelog(self, ctx: CustomContext):
        """Show changelogs for this bot!"""
        embed = utils.create_embed(
            ctx.author,
            title='Doggie Bot - Change Log:',
            description=CHANGELOG
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Misc(bot))
