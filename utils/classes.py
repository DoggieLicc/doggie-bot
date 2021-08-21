import asyncio
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Union, Optional, Dict, List

import discord
import yaml
from discord import TextChannel, ChannelType, Message, User
from discord.ext import commands, menus

import asqlite

from utils import guess_user_nitro_status, user_friendly_dt, create_embed

__all__ = [
    'CustomContext',
    'CustomBot',
    'CustomMenu',
    'Emotes',
    'ReminderList',
    'Reminder',
    'BasicConfig',
    'LoggingConfig'
]


class CustomContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.bot: CustomBot = self.bot

    async def send(self, *args, **kwargs) -> Message:
        kwargs['reference'] = kwargs.get('reference', self.message.reference)

        return await super().send(*args, **kwargs)

    @property
    def basic_config(self):
        return self.bot.basic_configs.get(self.guild.id, BasicConfig(self.guild))

    @property
    def logging_config(self):
        return self.bot.logging_configs.get(self.guild.id, LoggingConfig(self.guild))


class CustomBot(commands.Bot):
    # noinspection PyTypeChecker
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with open('config.yaml', 'r') as file:
            self.config = yaml.safe_load(file)

        self.reminders: Dict[int, Reminder] = {}
        self.basic_configs: Dict[int, BasicConfig] = {}
        self.logging_configs: Dict[int, LoggingConfig] = {}
        self.sniped: List[Message] = []

        self.fully_ready = False
        self.start_time: datetime = None  # type: ignore
        self.db: asqlite.Connection = None  # type: ignore

        self.loop.create_task(self.startup())

    async def get_context(self, message: Message, *, cls=CustomContext) -> CustomContext:
        return await super().get_context(message, cls=cls)

    async def on_message(self, message):
        if not self.fully_ready:
            await self.wait_for('fully_ready')

        await self.process_commands(message)

    async def startup(self):
        await self.wait_until_ready()

        self.start_time: datetime = datetime.now(timezone.utc)

        self.db: asqlite.Connection = await asqlite.connect('data.db', check_same_thread=False)

        await self.load_reminders()
        await self.load_basic_config()
        await self.load_logging_config()

        self.fully_ready = True
        self.dispatch('fully_ready')

    async def close(self):
        await self.db.close()
        await super().close()

    async def get_owner(self) -> User:
        if not self.owner_id or self.owner_ids:
            app = await self.application_info()
            if app.team:
                self.owner_ids = {m.id for m in app.team.members}
            else:
                self.owner_id = app.owner.id

        return await self.fetch_user(self.owner_id or list(self.owner_ids)[0])

    async def load_reminders(self):
        async with self.db.cursor() as cursor:
            for row in await cursor.execute('SELECT * FROM reminders'):
                message_id: int = row['id']
                try:
                    user: User = await self.fetch_user(row['user_id'])
                except discord.NotFound:
                    user: None = None
                reminder: str = row['reminder']
                end_time: int = row['end_time']
                destination: Union[User, TextChannel] = self.get_channel(row['destination']) or user

                if destination is None or user is None:
                    await cursor.execute('DELETE FROM reminders WHERE id = (?)', (message_id,))
                    await self.db.commit()
                    continue

                _reminder = Reminder(
                    message_id=message_id,
                    user=user,
                    reminder=reminder,
                    destination=destination,
                    end_time=datetime.fromtimestamp(end_time, timezone.utc),
                    bot=self
                )

                self.reminders[_reminder.id] = _reminder

    async def load_basic_config(self):
        async with self.db.cursor() as cursor:
            for row in await cursor.execute('SELECT * FROM basic_config'):
                guild = self.get_guild(row['guild_id'])
                prefix = row['prefix']
                snipe = bool(row['snipe'])
                mute_role = guild.get_role(row['mute_role']) if guild else None

                if not guild:
                    await cursor.execute('DELETE FROM basic_config WHERE guild_id = (?)', (row['guild_id'],))
                    await self.db.commit()
                    continue

                config = BasicConfig(
                    guild=guild,
                    prefix=prefix,
                    snipe=snipe,
                    mute_role=mute_role
                )

                if row['mute_role'] and not mute_role:
                    await cursor.execute('UPDATE basic_config SET mute_role = ? WHERE guild_id = ?', (None, guild.id))
                    await self.db.commit()
                    continue

                self.basic_configs[config.guild.id] = config

    async def load_logging_config(self):
        async with self.db.cursor() as cursor:
            for row in await cursor.execute('SELECT * FROM logging_config'):
                guild: discord.Guild = self.get_guild(row['guild_id'])
                kick_channel = guild.get_channel(row['kick_channel'])
                ban_channel = guild.get_channel(row['ban_channel'])
                purge_channel = guild.get_channel(row['purge_channel'])
                delete_channel = guild.get_channel(row['delete_channel'])
                mute_channel = guild.get_channel(row['mute_channel'])

                if not guild:
                    await cursor.execute('DELETE FROM basic_config WHERE guild_id = (?)', (row['guild_id'],))
                    await self.db.commit()
                    continue

                config = LoggingConfig(
                    guild=guild,
                    kick_channel=kick_channel,
                    ban_channel=ban_channel,
                    purge_channel=purge_channel,
                    delete_channel=delete_channel,
                    mute_channel=mute_channel
                )

                self.logging_configs[config.guild.id] = config


class CustomMenu(menus.MenuPages):
    @menus.button('\N{WASTEBASKET}\ufe0f', position=menus.Last(3))
    async def do_trash(self, _):
        self.stop()
        await self.message.delete()

    def stop(self):
        self.call_end_event()
        super().stop()

    async def finalize(self, timed_out):
        self.call_end_event()

    def call_end_event(self):
        self.bot.dispatch('finalize_menu', self.ctx)


class Emotes:
    bot_tag = "<:botTag:230105988211015680>"
    discord = "<:discord:314003252830011395>"
    owner = "<:owner:585789630800986114>"
    slowmode = "<:slowmode:585790802979061760>"
    check = "<:check:314349398811475968>"
    xmark = "<:xmark:314349398824058880>"
    role = "<:role:808826577785716756>"
    text = "<:channel:585783907841212418>"
    nsfw = "<:channel_nsfw:585783907660857354>"
    voice = "<:voice:585783907673440266>"
    emoji = "<:emoji_ghost:658538492321595393>"
    store = "<:store_tag:658538492409806849>"
    invite = "<:invite:658538493949116428>"

    # Badges
    partner = "<:partner:314068430556758017>"
    hypesquad = "<:hypesquad:314068430854684672>"
    nitro = "<:nitro:314068430611415041>"
    staff = "<:staff:314068430787706880>"
    balance = "<:balance:585763004574859273>"
    bravery = "<:bravery:585763004218343426>"
    brilliance = "<:brilliance:585763004495298575>"
    bughunter = "<:bughunter:585765206769139723>"
    supporter = "<:supporter:585763690868113455>"

    # Boost levels
    level1 = "<:booster:585764032162562058>"
    level2 = "<:booster2:585764446253744128>"
    level3 = "<:booster3:585764446220189716>"
    level4 = "<:booster4:585764446178246657>"

    verified = "<:verified:585790522677919749>"
    partnered = "<:partnernew:754032603081998336>"
    members = "<:members:658538493470965787>"
    stage = "<:stagechannel:824240882793447444>"
    stafftools = "<:stafftools:314348604095594498>"
    thread = "<:threadchannel:824240882697633812>"
    mention = "<:mention:658538492019867683>"
    rules = "<:rules:781581022059692043>"
    news = "<:news:658522693058166804>"

    @staticmethod
    def channel(chann):
        if chann.type == ChannelType.text:
            if isinstance(chann, TextChannel):
                if chann.is_nsfw():
                    return Emotes.nsfw
            return Emotes.text
        if chann.type == ChannelType.news:
            return Emotes.news
        if chann.type == ChannelType.voice:
            return Emotes.voice
        if chann.type == ChannelType.store:
            return Emotes.store
        if chann.type == ChannelType.category:
            return ""
        if chann.type == ChannelType.private:
            return Emotes.thread
        if chann.type == ChannelType.stage_voice:
            return Emotes.stage

    @staticmethod
    def badges(user):
        badges = []
        flags = [name for name, value in dict.fromkeys(iter(user.public_flags)) if value]

        if user.bot:
            badges.append(Emotes.bot_tag)
        if "staff" in flags:
            badges.append(Emotes.staff)
        if "partner" in flags:
            badges.append(Emotes.partner)
        if "hypesquad" in flags:
            badges.append(Emotes.hypesquad)
        if "bug_hunter" in flags:
            badges.append(Emotes.bughunter)
        if "early_supporter" in flags:
            badges.append(Emotes.supporter)
        if "hypesquad_briliance" in flags:
            badges.append(Emotes.brilliance)
        if "hypesquad_bravery" in flags:
            badges.append(Emotes.bravery)
        if "hypesquad_balance" in flags:
            badges.append(Emotes.balance)
        if "hypesquad_brilliance" in flags:
            badges.append(Emotes.brilliance)
        if "verified_bot" in flags:
            badges.append(Emotes.verified)
        if "verified_bot_developer" in flags:
            badges.append(Emotes.verified)

        if guess_user_nitro_status(user):
            badges.append(Emotes.nitro)

        return " ".join(badges)


class ReminderList(menus.ListPageSource):
    async def format_page(self, menu, entries):
        index = menu.current_page + 1
        embed = create_embed(menu.ctx.author, title=f'Showing active reminders for {menu.ctx.author} '
                                                    f'({index}/{self._max_pages}):')

        for reminder in entries:
            channel = reminder.destination if isinstance(reminder.destination, TextChannel) else None

            embed.add_field(name=f'ID: {reminder.id}',
                            value=f'**Reminder:** {str(reminder)[:1100]}\n'
                                  f'**Ends at:** {user_friendly_dt(reminder.end_time)}\n'
                                  f'**Destination:** {channel.mention if channel else "Your DMS!"}\n',
                            inline=False)
        return embed


@dataclass
class Reminder:
    message_id: int
    user: User
    reminder: str
    destination: Union[User, TextChannel]
    end_time: datetime
    bot: CustomBot
    id: int = field(init=False)
    task: asyncio.Future = field(init=False)

    def __post_init__(self):
        self.id = len(self.bot.reminders) + 1
        self.task = asyncio.ensure_future(self.send_reminder())
        self.bot.reminders[self.id] = self

    async def send_reminder(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute('INSERT OR IGNORE INTO reminders VALUES (?, ?, ?, ?, ?)',
                                 (self.message_id,
                                  self.user.id,
                                  self.reminder,
                                  int(self.end_time.timestamp()),
                                  self.destination.id)
                                 )

        await self.bot.db.commit()
        await discord.utils.sleep_until(self.end_time)

        embed = discord.Embed(title='Reminder!',
                              description=self.reminder,
                              color=discord.Color.green())

        if isinstance(self.destination, TextChannel):
            embed.set_footer(icon_url=self.user.avatar.url,
                             text=f'Reminder sent by {self.user}')
        else:
            embed.set_footer(icon_url=self.user.avatar.url,
                             text=f'This reminder is sent by you!')

        try:
            await self.destination.send(
                f"**Hey {self.user.mention},**" if isinstance(self.destination, TextChannel) else None,
                embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

        await self.remove()

    async def remove(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute('DELETE FROM reminders WHERE id = (?)', (self.message_id,))
        await self.bot.db.commit()

        del self.bot.reminders[self.id]
        self.task.cancel()

    def __str__(self):
        return self.reminder


@dataclass(frozen=True)
class BasicConfig:
    guild: discord.Guild
    prefix: Optional[str] = None
    snipe: Optional[bool] = None
    mute_role: Optional[discord.Role] = None

    async def set_config(self, bot: CustomBot, **kwargs) -> 'BasicConfig':

        config = replace(self, **kwargs)

        async with bot.db.cursor() as cursor:
            await cursor.execute('REPLACE INTO basic_config VALUES(?, ?, ?, ?)',
                                 (
                                     config.guild.id,
                                     config.prefix,
                                     config.snipe,
                                     config.mute_role.id if config.mute_role else None
                                 ))

        await bot.db.commit()

        bot.basic_configs[config.guild.id] = config

        return config


@dataclass(frozen=True)
class LoggingConfig:
    guild: discord.Guild
    kick_channel: Optional[TextChannel] = None
    ban_channel: Optional[TextChannel] = None
    purge_channel: Optional[TextChannel] = None
    delete_channel: Optional[TextChannel] = None
    mute_channel: Optional[TextChannel] = None

    async def set_config(self, bot: CustomBot, **kwargs) -> 'LoggingConfig':

        config = replace(self, **kwargs)

        async with bot.db.cursor() as cursor:
            await cursor.execute('REPLACE INTO logging_config VALUES(?, ?, ?, ?, ?, ?)',
                                 (
                                     config.guild.id,
                                     config.kick_channel.id if config.kick_channel else None,
                                     config.ban_channel.id if config.ban_channel else None,
                                     config.purge_channel.id if config.purge_channel else None,
                                     config.delete_channel.id if config.delete_channel else None,
                                     config.mute_channel.id if config.mute_channel else None
                                 ))

        await bot.db.commit()

        bot.logging_configs[config.guild.id] = config

        return config
