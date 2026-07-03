import io
import copy
import textwrap
import traceback
from contextlib import redirect_stdout

from discord import DMChannel, GroupChannel, PartialMessageable, User, Color, Embed, File, Asset, Member
from discord.ext import commands

import utils
from utils import CustomBot, CustomContext

def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def format_error(author: User, error: Exception) -> Embed:
    error_lines = traceback.format_exception(type(error), error, error.__traceback__)
    embed = utils.create_embed(
        author,
        title="Error!",
        description=f'```py\n{"".join(error_lines)}\n```',
        color=Color.red()
    )

    return embed

class Dev(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    async def cog_check(self, ctx: CustomContext):
        # pylint: disable=invalid-overridden-method
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner()

        return True

    @commands.command()
    async def load(self, ctx: CustomContext, *cogs: str):
        # pylint: disable=broad-exception-caught
        for cog in cogs:
            try:
                await self.bot.load_extension(f'cogs.{cog}')
            except Exception as e:
                embed = format_error(ctx.author, e)
                return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Success!',
            description=f'Cogs ``{", ".join(cogs)}`` has been loaded!',
            color=Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def unload(self, ctx: CustomContext, *cogs: str):
        # pylint: disable=broad-exception-caught
        for cog in cogs:
            try:
                await self.bot.unload_extension(f'cogs.{cog}')
            except Exception as e:
                embed = format_error(ctx.author, e)
                return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Success!',
            description=f'Cogs ``{", ".join(cogs)}`` has been unloaded!',
            color=Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def reload(self, ctx: CustomContext, *cogs: str):
        for cog in cogs:
            try:
                await self.bot.reload_extension(f'cogs.{cog}')
            except commands.ExtensionNotLoaded:
                try:
                    await self.bot.load_extension(f'cogs.{cog}')
                except (commands.NoEntryPointError, commands.ExtensionFailed) as e:
                    embed = format_error(ctx.author, e)
                    return await ctx.send(embed=embed)
            except (commands.NoEntryPointError, commands.ExtensionFailed) as e:
                embed = format_error(ctx.author, e)
                return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Success!',
            description=f'Cogs ``{", ".join(cogs)}`` has been reloaded!',
            color=Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=['ra'])
    async def reloadall(self, ctx: CustomContext):
        for cog in self.bot.cogs_list:
            try:
                await self.bot.reload_extension(cog)
            except commands.ExtensionNotLoaded:
                try:
                    await self.bot.load_extension(cog)
                except (commands.NoEntryPointError, commands.ExtensionFailed) as e:
                    embed = format_error(ctx.author, e)
                    return await ctx.send(embed=embed)
            except (commands.NoEntryPointError, commands.ExtensionFailed) as e:
                embed = format_error(ctx.author, e)
                return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Success!',
            description=f'Cogs ``{", ".join(self.bot.cogs_list)}`` has been reloaded!',
            color=Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def list_cogs(self, ctx: CustomContext):
        embed = utils.create_embed(
            ctx.author,
            title='Showing all loaded cogs...',
            description='\n'.join(self.bot.cogs),
            color=Color.green()
        )

        embed.add_field(name='Number of cogs loaded:', value=f'{len(self.bot.cogs)} cogs', inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def eval(self, ctx: CustomContext, *, code):
        # pylint: disable=broad-exception-caught,exec-used

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
        }

        env.update(globals())
        code = cleanup_code(code)
        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'
        stdout = io.StringIO()

        try:
            exec(to_compile, env)
        except BaseException as e:
            embed = format_error(ctx.author, e)
            return await ctx.send(embed=embed)

        func = env['func']

        try:
            with redirect_stdout(stdout):
                ret = await func()

        except BaseException as e:
            embed = format_error(ctx.author, e)
            return await ctx.send(embed=embed)

        value = stdout.getvalue()
        if ret is None:
            if value:
                if len(value) < 4000:
                    embed = utils.create_embed(
                        ctx.author,
                        title="Exec result:",
                        description=f'```py\n{value}\n```'
                    )

                    return await ctx.send(embed=embed)

                return await ctx.send(
                    f"Exec result too long ({len(value)} chars.):",
                    file=utils.str_to_file(value)
                )

            embed = utils.create_embed(ctx.author, title="Eval code executed!")
            return await ctx.send(embed=embed)

        if isinstance(ret, Embed):
            return await ctx.send(embed=ret)

        if isinstance(ret, File):
            return await ctx.send(file=ret)

        if isinstance(ret, Asset):
            embed = utils.create_embed(ctx.author, image=ret)
            return await ctx.send(embed=embed)

        ret = repr(ret)

        if len(ret) < 4000:
            embed = utils.create_embed(
                ctx.author,
                title="Exec result:",
                description=f'```py\n{ret}\n```'
            )

        else:
            return await ctx.send(f"Exec result too long ({len(ret)} chars.):",
                                  file=utils.str_to_file(ret))

        return await ctx.send(embed=embed)

    @commands.command(aliases=['clean'])
    async def cleanup(self, ctx: CustomContext, limit=100):
        if isinstance(ctx.channel, (DMChannel, PartialMessageable, GroupChannel)):
            return
        messages = await ctx.channel.purge(limit=limit, bulk=False, check=lambda m: m.author == ctx.me)
        await ctx.send(f'Deleted {len(messages)} message(s)', delete_after=3, reference=ctx.message)

    @commands.command()
    async def sudo(self, ctx: CustomContext, who: Member | User, *, command: str):
        msg = copy.copy(ctx.message)
        msg.channel = ctx.channel
        msg.author = who
        msg.content = (ctx.prefix or ctx.me.mention) + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)

    @commands.command()
    async def sync(self, ctx: CustomContext):
        app_commands = await self.bot.tree.sync()
        await ctx.send(f'Synced {len(app_commands)} app commands!')

async def setup(bot):
    await bot.add_cog(Dev(bot))
