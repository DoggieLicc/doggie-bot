import asyncio
import utils
import discord

from discord.ext import commands

from typing import Union, List, Optional
from datetime import datetime, timedelta, timezone


async def ban_embed(guild: discord.Guild, punished: discord.User, action):
    mod, reason = None, "Unknown"
    emote = utils.Emotes.ban_create if action.name == 'ban' else utils.Emotes.ban_delete

    await asyncio.sleep(5)

    try:
        async for entry in guild.audit_logs(limit=10, action=action):
            if entry.target == punished:
                mod = entry.user
                reason = entry.reason

    except discord.Forbidden:
        reason = '*Bot is missing Audit Log Permissions!*'

    embed = utils.create_embed(
        None,
        title=f'{emote} {punished} has been {action.name}ned! ({punished.id})',
        description=f'{action.name.title()}ned by: {mod.mention if mod else "Unknown"}'
                    f'\n\nReason: {reason or "No reason specified"}',
        thumbnail=punished.display_avatar,
        color=discord.Color.red()
    )

    return embed


def format_log(ctx: utils.CustomContext, _list: List[discord.Member], reason: str, punishment: str):
    if not ctx.logging_config.mute_channel:
        return

    embed = discord.Embed(
        title=f'{len(_list)} members {punishment}!',
        description=f'They were {punishment} by {ctx.author.mention} for "{reason}"',
        color=discord.Color.red()
    )

    embed.add_field(
        name=f'{punishment.title()} members:',
        value=utils.shorten_below_number(list(map(str, _list))) or 'None'
    )

    return embed


class EventsCog(commands.Cog):
    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @commands.Cog.listener()
    async def on_fully_ready(self):
        print(f'\nLogged in as: {self.bot.user.name} - {self.bot.user.id}\n'
              f'Version: {discord.__version__}\n'
              f'Successfully logged in and booted...!')

    @commands.Cog.listener()
    async def on_command(self, ctx: utils.CustomContext):
        await ctx.trigger_typing()

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, banned: Union[discord.Member, discord.User]):

        config = self.bot.logging_configs.get(guild.id)

        if not config or not config.ban_channel:
            return

        embed = await ban_embed(guild, banned, discord.AuditLogAction.ban)

        try:
            await config.ban_channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, unbanned: discord.User):
        config = self.bot.logging_configs.get(guild.id)

        if not config or not config.ban_channel:
            return

        embed = await ban_embed(guild, unbanned, discord.AuditLogAction.unban)

        try:
            await config.ban_channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, kicked: discord.Member):
        config = self.bot.logging_configs.get(kicked.guild.id)

        if not config or not config.kick_channel:
            return

        mod, reason = None, "Unknown"
        await asyncio.sleep(5)
        d = datetime.now(timezone.utc) - timedelta(seconds=5)
        try:
            async for entry in kicked.guild.audit_logs(after=d, limit=10, action=discord.AuditLogAction.kick):
                if entry.target == kicked:
                    mod = entry.user
                    reason = entry.reason
                    break

        except discord.Forbidden:
            return
        if not mod:
            return

        embed = utils.create_embed(
            None,
            title=f'{utils.Emotes.member_leave} {kicked} has been kicked! ({kicked.id})',
            description=f'Kicked by: {mod.mention if mod else "Unknown"}\n\nReason: {reason or "No reason specified"}',
            thumbnail=kicked.display_avatar,
            color=discord.Color.red())

        try:
            await config.kick_channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        config = self.bot.basic_configs.get(message.guild.id)
        log_config = self.bot.logging_configs.get(message.guild.id)

        if config and config.snipe:
            self.bot.sniped[:0] = [message]
            self.bot.sniped = self.bot.sniped[:5000]

        if not log_config or not log_config.delete_channel:
            return

        embed = utils.format_deleted_msg(message)

        try:
            await log_config.delete_channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_mute(self, ctx: utils.CustomContext, muted: List[discord.Member], reason: str):
        if not ctx.logging_config.mute_channel:
            return

        embed = format_log(ctx, muted, reason, 'muted')

        try:
            await ctx.logging_config.mute_channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_unmute(self, ctx: utils.CustomContext, unmuted: List[discord.Member], reason: str):
        if not ctx.logging_config.mute_channel:
            return

        embed = format_log(ctx, unmuted, reason, 'unmuted')

        try:
            await ctx.logging_config.mute_channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_purge(self, ctx: utils.CustomContext, users: Optional[List[discord.User]], amount: int):
        if not ctx.logging_config.purge_channel:
            return

        embed = discord.Embed(
            title=f'{amount} messages deleted!',
            description=f'{ctx.author.mention} deleted {amount} messages in {ctx.channel.mention}\n\n'
                        f'Deleted messages from:\n' +
                        ', '.join(map(str, users)),
            color=discord.Color.red()
        )

        try:
            await ctx.logging_config.purge_channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass


def setup(bot):
    bot.add_cog(EventsCog(bot))
