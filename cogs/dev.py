import asyncio
import copy
import io
import textwrap
import traceback
import utils
import discord

from discord.ext import commands

from contextlib import redirect_stdout
from typing import Union, Optional, List


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


class SayFlags(commands.FlagConverter):
    content: Optional[str]
    embeds: List[utils.EmbedConverter] = commands.flag(name='embeds', aliases=['embed'], default=lambda ctx: [])


class Dev(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    async def cog_check(self, ctx: utils.CustomContext):
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner()

        return True

    @commands.command()
    async def load(self, ctx: utils.CustomContext, *cogs: str):
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
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def unload(self, ctx: utils.CustomContext, *cogs: str):
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
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def reload(self, ctx: utils.CustomContext, *cogs: str):
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
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=['ra'])
    async def reloadall(self, ctx):
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
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def list_cogs(self, ctx: utils.CustomContext):
        embed = utils.create_embed(
            ctx.author,
            title='Showing all loaded cogs...',
            description='\n'.join(self.bot.cogs),
            color=discord.Color.green()
        )

        embed.add_field(name='Number of cogs loaded:', value=f'{len(self.bot.cogs)} cogs', inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def eval(self, ctx: utils.CustomContext, *, code):

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

                if isinstance(ret, discord.Asset):
                    embed = utils.create_embed(ctx.author, image=ret)
                    return await ctx.send(embed=embed)

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

    @commands.command()
    async def sudo(self, ctx: utils.CustomContext, who: Union[discord.Member, discord.User], *, command: str):
        msg = copy.copy(ctx.message)
        msg.channel = ctx.channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)

    @commands.command()
    async def say(self, ctx: utils.CustomContext, *, flags: SayFlags):
        await ctx.send(
            **dict(flags),
            reference=ctx.message.reference,
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
            files=[await file.to_file() for file in ctx.message.attachments]
        )

    @commands.command(aliases=['gitpull'])
    async def pull(self, ctx: utils.CustomContext):
        cmd = 'git pull'

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await proc.communicate()

        embed = utils.create_embed(
            ctx.author,
            title='Pulled from GitHub successfully:',
            description=f'```wl\n'
                        f'{stdout.decode()}\n\n'
                        f'Return code {proc.returncode}'
                        f'```'
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=['clean'])
    async def cleanup(self, ctx: utils.CustomContext, limit=100):
        messages = await ctx.channel.purge(limit=limit, bulk=False, check=lambda m: m.author == ctx.me)
        await ctx.send(f'Deleted {len(messages)} message(s)', delete_after=3, reference=ctx.message)


async def setup(bot):
    await bot.add_cog(Dev(bot))
