import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord import Embed, User, Member, Color, Guild, AuditLogAction, Forbidden, NotFound, HTTPException, Message
from discord.ext.commands import Cog
from loguru import logger

import utils


async def ban_embed(guild: Guild, punished: User, action) -> Embed:
    mod, reason = None, "Unknown"
    emote = utils.Emotes.ban_create if action.name == 'ban' else utils.Emotes.ban_delete

    await asyncio.sleep(5)

    try:
        async for entry in guild.audit_logs(limit=10, action=action):
            if entry.target == punished:
                mod = entry.user
                reason = entry.reason

    except Forbidden:
        reason = '*Bot is missing Audit Log Permissions!*'

    embed = utils.create_embed(
        None,
        title=f'{emote} {punished} has been {action.name}ned! ({punished.id})',
        description=f'{action.name.title()}ned by: {mod.mention if mod else "Unknown"}'
                    f'\n\nReason: {reason or "No reason specified"}',
        thumbnail=punished.display_avatar,
        color=Color.red()
    )

    return embed


def format_log(ctx: utils.CustomContext, _list: list[Member], reason: str, punishment: str) -> Embed | None:
    if not ctx.logging_config.mute_channel:
        return None

    embed = Embed(
        title=f'{len(_list)} members {punishment}!',
        description=f'They were {punishment} by {ctx.author.mention} for "{reason}"',
        color=Color.red()
    )

    embed.add_field(
        name=f'{punishment.title()} members:',
        value=utils.shorten_below_number(list(map(str, _list))) or 'None'
    )

    return embed


class EventsCog(Cog):
    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @Cog.listener()
    async def on_fully_ready(self):
        logger.info(f'\nLogged in as: {self.bot.user.name} - {self.bot.user.id}\n'
              f'Version: {discord.__version__}\n'
              f'Successfully logged in and booted...!')

    @Cog.listener()
    async def on_command(self, ctx: utils.CustomContext):
        await ctx.typing()

    @Cog.listener()
    async def on_member_ban(self, guild: Guild, banned: Member | User):
        config = self.bot.logging_configs.get(guild.id)

        if not config or not config.ban_channel:
            return

        embed = await ban_embed(guild, banned, AuditLogAction.ban)

        try:
            await config.ban_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, unbanned: User):
        config = self.bot.logging_configs.get(guild.id)

        if not config or not config.ban_channel:
            return

        embed = await ban_embed(guild, unbanned, AuditLogAction.unban)

        try:
            await config.ban_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_member_remove(self, kicked: Member):
        config = self.bot.logging_configs.get(kicked.guild.id)

        if not config or not config.kick_channel:
            return

        mod, reason = None, "Unknown"
        await asyncio.sleep(5)
        d = datetime.now(timezone.utc) - timedelta(seconds=5)
        try:
            async for entry in kicked.guild.audit_logs(after=d, limit=10, action=AuditLogAction.kick):
                if entry.target == kicked:
                    mod = entry.user
                    reason = entry.reason
                    break

        except Forbidden:
            return
        if not mod:
            return

        embed = utils.create_embed(
            None,
            title=f'{utils.Emotes.member_leave} {kicked} has been kicked! ({kicked.id})',
            description=f'Kicked by: {mod.mention if mod else "Unknown"}\n\nReason: {reason or "No reason specified"}',
            thumbnail=kicked.display_avatar,
            color=Color.red())

        try:
            await config.kick_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        if message.author.bot or not message.guild:
            return

        config = self.bot.basic_configs.get(message.guild.id)
        log_config = self.bot.logging_configs.get(message.guild.id)

        if config and config.snipe:
            self.bot.sniped[:0] = [message]
            self.bot.sniped = self.bot.sniped[:10000]

        if not log_config or not log_config.delete_channel:
            return

        embed = utils.format_deleted_msg(message)

        try:
            await log_config.delete_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_mute(self, ctx: utils.CustomContext, muted: list[Member], reason: str):
        if not ctx.logging_config.mute_channel:
            return

        embed = format_log(ctx, muted, reason, 'muted')

        try:
            await ctx.logging_config.mute_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_unmute(self, ctx: utils.CustomContext, unmuted: list[Member], reason: str):
        if not ctx.logging_config.mute_channel:
            return

        embed = format_log(ctx, unmuted, reason, 'unmuted')

        try:
            await ctx.logging_config.mute_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_purge(self, ctx: utils.CustomContext, users: list[User], amount: int):
        if not ctx.logging_config.purge_channel:
            return

        embed = Embed(
            title=f'{amount} messages deleted!',
            description=f'{ctx.author.mention} deleted {amount} messages in {ctx.channel.mention}\n\n'
                        f'Deleted messages from:\n' +
                        ', '.join(map(str, users)),
            color=Color.red()
        )

        try:
            await ctx.logging_config.purge_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass


async def setup(bot):
    await bot.add_cog(EventsCog(bot))
