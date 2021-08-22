import copy
import io
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import Union

import discord
from discord.ext import commands

import utils


def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def format_error(author: discord.User, error: Exception) -> discord.Embed:
    error_lines = traceback.format_exception(type(error), error, error.__traceback__)
    embed = utils.create_embed(
        author,
        title="Error!",
        description=f'```py\n{"".join(error_lines)}\n```',
        color=discord.Color.red()
    )

    return embed


class Dev(commands.Cog):
    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    async def cog_check(self, ctx: utils.CustomContext):
        return await self.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def load(self, ctx: utils.CustomContext, *cogs: str):
        for cog in cogs:
            try:
                self.bot.load_extension(f'cogs.{cog}')
            except Exception as e:
                embed = format_error(ctx.author, e)
                return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Success!',
            description=f'Cogs ``{", ".join(cogs)}`` has been loaded!',
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def unload(self, ctx: utils.CustomContext, *cogs: str):
        for cog in cogs:
            try:
                self.bot.unload_extension(f'cogs.{cog}')
            except Exception as e:
                embed = format_error(ctx.author, e)
                return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Success!',
            description=f'Cogs ``{", ".join(cogs)}`` has been unloaded!',
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def reload(self, ctx: utils.CustomContext, *cogs: str):
        for cog in cogs:
            try:
                self.bot.reload_extension(f'cogs.{cog}')
            except Exception as e:
                embed = format_error(ctx.author, e)
                return await ctx.send(embed=embed)

        embed = utils.create_embed(
            ctx.author,
            title='Success!',
            description=f'Cogs ``{", ".join(cogs)}`` has been reloaded!',
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def list_cogs(self, ctx: utils.CustomContext):
        embed = utils.create_embed(
            ctx.author,
            title='Showing all loaded cogs...',
            description='\n'.join(self.bot.cogs),
            color=discord.Color.green()
        )

        embed.add_field(name='Number of cogs loaded:', value=f'{len(self.bot.cogs)} cogs', inline=False)
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def eval(self, ctx: utils.CustomContext, *, code):
        await ctx.channel.trigger_typing()

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
        except Exception as e:
            embed = format_error(ctx.author, e)
            return await ctx.send(embed=embed)

        func = env['func']

        try:
            with redirect_stdout(stdout):
                ret = await func()

        except Exception as e:
            embed = format_error(ctx.author, e)
            return await ctx.send(embed=embed)

        else:
            value = stdout.getvalue()
            if ret is None:
                if value:
                    if len(value) < 4000:
                        embed = utils.create_embed(
                            ctx.author,
                            title="Exec result:",
                            description=f'```py\n{value}\n```'
                        )

                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(
                            f"Exec result too long ({len(value)} chars.):",
                            file=utils.str_to_file(value)
                        )

                    return

                else:
                    embed = utils.create_embed(ctx.author, title="Eval code executed!")
                    return await ctx.send(embed=embed)

            else:
                if isinstance(ret, discord.Embed):
                    return await ctx.send(embed=ret)

                if isinstance(ret, discord.File):
                    return await ctx.send(file=ret)

                else:
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

    @commands.command(hidden=True)
    async def sudo(self, ctx: utils.CustomContext, who: Union[discord.Member, discord.User], *, command: str):

        msg = copy.copy(ctx.message)
        msg.channel = ctx.channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)


def setup(bot):
    bot.add_cog(Dev(bot))
