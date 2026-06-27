import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord import Embed, User, Member, Color, Guild, AuditLogAction, Forbidden, NotFound, HTTPException, Message, Interaction
from discord.ext.commands import Cog, Context
from loguru import logger

import utils
from utils import CustomBot


async def ban_embed(guild: Guild, punished: Member | User, action) -> Embed:
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
        title=f'{emote} An user has been {action.name}ned!',
        description=f'{punished.mention} (@{punished}) was {action.name}ned from this server.\n'
                    f'{action.name.title()}ned by: {mod.mention if mod else "Unknown"}'
                    f'\n\nReason: {reason or "No reason specified"}',
        thumbnail=punished.display_avatar,
        color=Color.red()
    )

    return embed


def format_log(interaction: Interaction[CustomBot], _list: list[Member], reason: str, punishment: str) -> Embed | None:
    embed = Embed(
        title=f'{len(_list)} members {punishment}!',
        description=f'They were {punishment} by {interaction.user.mention} (@{interaction.user}) for "{reason}"',
        color=Color.red()
    )

    embed.add_field(
        name=f'{punishment.title()} members:',
        value=utils.shorten_below_number(list(map(str, _list))) or 'None'
    )

    return embed


class EventsCog(Cog):
    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    @Cog.listener()
    async def on_fully_ready(self):
        if self.bot.user:
            logger.info(f'Logged in as: {self.bot.user.name} - {self.bot.user.id}')
        logger.info(f'Version: {discord.__version__}')
        logger.info('Successfully logged in and booted...!')

    @Cog.listener()
    async def on_command(self, ctx: Context):
        await ctx.typing()

    @Cog.listener()
    async def on_member_ban(self, guild: Guild, banned: Member | User):
        config = self.bot.get_logging_config(guild)

        if not config or not config.ban_channel:
            return

        embed = await ban_embed(guild, banned, AuditLogAction.ban)

        try:
            await config.ban_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        config = self.bot.get_logging_config(before.guild)

        if not config or not config.mute_channel:
            return

        if not after.timed_out_until or before.timed_out_until:
            return

        if before.timed_out_until == after.timed_out_until:
            return

        mod, reason = None, "Unknown"
        audit_failed = False

        await asyncio.sleep(5)
        d = datetime.now(timezone.utc) - timedelta(seconds=6)
        try:
            async for entry in before.guild.audit_logs(after=d, limit=10, action=AuditLogAction.member_update):
                if entry.target == before and entry.after.timed_out_until == after.timed_out_until:
                    mod = entry.user
                    reason = entry.reason or 'No reason specified'
                    break

        except Forbidden:
            audit_failed = True

        if mod is None:
            addit_desc = '\n\n**Moderator:** Unknown\n**Reason:** Unknown'
        else:
            addit_desc = f'\n\n**Moderator:** {mod.mention}\n**Reason:** {reason}'

        if audit_failed:
            addit_desc += '\n\n**Bot is missing Audit Log permissions! Some data will be unavailable**'

        embed = utils.create_embed(
            None,
            title=utils.Emotes.timeout + ' Member put in timeout!',
            description=f'Member {after.mention} (@{after}) was timed-out until {utils.user_friendly_dt(after.timed_out_until)}' + addit_desc,
            thumbnail=after.display_avatar,
            color=discord.Color.red()
        )

        try:
            await config.mute_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, unbanned: User):
        config = self.bot.get_logging_config(guild)

        if not config or not config.ban_channel:
            return

        embed = await ban_embed(guild, unbanned, AuditLogAction.unban)

        try:
            await config.ban_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_member_remove(self, kicked: Member):
        config = self.bot.get_logging_config(kicked.guild)

        if not config or not config.kick_channel:
            return

        mod, reason = None, "Unknown"
        audit_failed = False
        await asyncio.sleep(5)
        d = datetime.now(timezone.utc) - timedelta(seconds=6)
        try:
            async for entry in kicked.guild.audit_logs(after=d, limit=10, action=AuditLogAction.kick):
                if entry.target == kicked:
                    mod = entry.user
                    reason = entry.reason
                    break

        except Forbidden:
            audit_failed = True

        if mod is None:
            addit_desc = '\n\n**Moderator:** Unknown\n**Reason:** Unknown'
        else:
            addit_desc = f'\n\n**Moderator:** {mod.mention}\n**Reason:** {reason}'

        if audit_failed:
            addit_desc += '\n\n**Bot is missing Audit Log permissions! Some data will be unavailable**'

        embed = utils.create_embed(
            None,
            title=utils.Emotes.member_leave + ' Member kicked!',
            description=f'Member {kicked.mention} (@{kicked}) was kicked from this server.' + addit_desc,
            thumbnail=kicked.display_avatar,
            color=Color.red()
        )

        try:
            await config.kick_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        if message.author.bot or not message.guild:
            return

        config = self.bot.get_basic_config(message.guild)
        log_config = self.bot.get_logging_config(message.guild)

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
    async def on_mute(self, interaction: Interaction[CustomBot], muted: list[Member], reason: str):
        if not interaction.guild:
            return

        config = self.bot.get_logging_config(interaction.guild)
        if not config.mute_channel:
            return

        embed = format_log(interaction, muted, reason, 'muted')
        if not embed:
            return

        try:
            await config.mute_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_unmute(self, interaction: Interaction[CustomBot], unmuted: list[Member], reason: str):
        if not interaction.guild:
            return

        config = self.bot.get_logging_config(interaction.guild)
        if not config.mute_channel:
            return

        embed = format_log(interaction, unmuted, reason, 'unmuted')
        if not embed:
            return

        try:
            await config.mute_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_purge(self, interaction: Interaction[CustomBot], users: list[User], amount: int):
        if not interaction.guild or not interaction.channel:
            return

        config = self.bot.get_logging_config(interaction.guild)
        if not config.purge_channel:
            return

        embed = Embed(
            title=f'{amount} messages deleted!',
            description=f'{interaction.user.mention} deleted {amount} messages in <#{interaction.channel.id}>\n\n'
                        f'Deleted messages from:\n' +
                        ', '.join(map(str, users)),
            color=Color.red()
        )

        try:
            await config.purge_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        config = self.bot.get_logging_config(guild)
        if not config.purge_channel:
            return

        mod = None
        channel = None
        count = 0
        await asyncio.sleep(5)
        d = datetime.now(timezone.utc) - timedelta(seconds=6)
        try:
            async for entry in guild.audit_logs(after=d, limit=10, action=AuditLogAction.message_bulk_delete):
                if entry and entry.target and entry.target.id == payload.channel_id:
                    mod = entry.user
                    channel = entry.target
                    count = getattr(entry.extra, 'count', 0)
                    break
        except Forbidden:
            return

        if not mod or not channel or mod == guild.me:
            return

        embed = Embed(
            title='Multiple messages deleted!',
            description=f'{mod.mention} deleted {count} messages in <#{channel.id}>',
            color=discord.Color.red()
        )

        try:
            await config.purge_channel.send(embed=embed)
        except (Forbidden, NotFound, HTTPException):
            pass

async def setup(bot):
    await bot.add_cog(EventsCog(bot))
