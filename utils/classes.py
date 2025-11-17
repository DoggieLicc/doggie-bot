import discord
import asyncio
import yaml
import asqlite
import os
import shutil
import logging

from discord import TextChannel, ChannelType, Message, User
from discord.ext import commands, menus

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Union, Optional, Dict, List

from utils.funcs import guess_user_nitro_status, user_friendly_dt, create_embed, fix_url

__all__ = [
    'CustomContext',
    'CustomBot',
    'CustomMenu',
    'Emotes',
    'ReminderList',
    'Reminder',
    'BasicConfig',
    'LoggingConfig',
    'MissingAPIKey'
]

logger = logging.getLogger(__name__)

dirname = os.getcwd()
config_file = os.path.join(dirname, 'config.yaml')

class CustomContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.bot: CustomBot = self.bot
        self.uncaught_error = False

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

        yaml_config = dict()
        if os.path.exists(config_file):
            with open(config_file, 'r') as file:
                yaml_config = yaml.safe_load(file)

        self.config = dict()

        self.config['bot_token'] = yaml_config.get('bot_token') or os.getenv('BOT_TOKEN')
        self.config['osu_client_secret'] = yaml_config.get('osu_client_secret') or os.getenv('OSU_CLIENT_SECRET')
        self.config['osu_client_id'] = yaml_config.get('osu_client_id') or os.getenv('OSU_CLIENT_ID') or 0
        self.config['unsplash_api_key'] = yaml_config.get('unsplash_api_key') or os.getenv('UNSPLASH_API_KEY')
        self.config['saucenao_api_key'] = yaml_config.get('saucenao_api_key') or os.getenv('SAUCENAO_API_KEY')
        self.config['data_dir'] = yaml_config.get('data_dir') or os.getenv('DATA_DIR') or '/data'

        self.db_file = os.path.join(self.config['data_dir'], 'data.db')

        if not os.path.exists(self.db_file):
            empty_db_file = os.path.join(dirname, f'assets/empty_data.db')
            shutil.copy(empty_db_file, self.db_file)
            logger.info('Created empty database')

        self.reminders: Dict[int, Reminder] = {}
        self.basic_configs: Dict[int, BasicConfig] = {}
        self.logging_configs: Dict[int, LoggingConfig] = {}
        self.sniped: List[Message] = []
        self.cogs_list: List[str] = []

        self.fully_ready = False
        self.start_time: datetime = None  # type: ignore
        self.db: asqlite.Connection = None  # type: ignore
        self.session = None

    async def setup_hook(self):
        self.loop.create_task(self.startup())

    async def get_context(self, message: Message, *, cls=CustomContext) -> CustomContext:
        return await super().get_context(message, cls=cls)

    async def on_message(self, message):
        if not self.fully_ready:
            await self.wait_for('fully_ready')

        if message.content in [f'<@!{self.user.id}>', f'<@{self.user.id}>']:
            embed = create_embed(
                message.author,
                title='Bot has been pinged!',
                description='The current prefixes are: ' + ', '.join((await self.get_prefix(message))[1:])
            )

            await message.channel.send(embed=embed)

        await self.process_commands(message)

    async def startup(self):
        await self.wait_until_ready()

        self.start_time: datetime = datetime.now(timezone.utc)

        self.db: asqlite.Connection = await asqlite.connect(self.db_file, check_same_thread=False)

        await self.load_reminders()
        await self.load_basic_config()
        await self.load_logging_config()

        self.fully_ready = True
        self.dispatch('fully_ready')

    async def close(self):
        await self.db.close()
        await super().close()

    async def get_owner(self) -> User:
        if not self.owner_id and not self.owner_ids:
            info = await self.application_info()
            self.owner_id = info.owner.id

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

                if not guild:
                    continue

                kick_channel = guild.get_channel(row['kick_channel'])
                ban_channel = guild.get_channel(row['ban_channel'])
                purge_channel = guild.get_channel(row['purge_channel'])
                delete_channel = guild.get_channel(row['delete_channel'])
                mute_channel = guild.get_channel(row['mute_channel'])

                config = LoggingConfig(
                    guild=guild,
                    kick_channel=kick_channel,
                    ban_channel=ban_channel,
                    purge_channel=purge_channel,
                    delete_channel=delete_channel,
                    mute_channel=mute_channel
                )

                self.logging_configs[config.guild.id] = config

    @staticmethod
    def get_custom_prefix(_bot: 'CustomBot', message: discord.Message):
        default_prefixes = ['doggie.', 'Doggie.', 'dog.', 'Dog.']

        if not message.guild:
            return commands.when_mentioned_or(*default_prefixes)(_bot, message)

        config = _bot.basic_configs.get(message.guild.id)

        if not config or not config.prefix:
            return commands.when_mentioned_or(*default_prefixes)(_bot, message)

        else:
            return commands.when_mentioned_or(config.prefix)(_bot, message)


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
    # Emotes available in https://discord.gg/Uk6fg39cWn

    bot_tag = '<:botTag:941816165221679144>'
    discord = '<:discord:941816357949960222>'
    owner = '<:owner:941816499960688650>'
    slowmode = '<:slowmode:941816507342651462>'
    check = '<:check:941816359090806804>'
    xmark = '<:xmark:941816519300616213>'
    role = '<:role:941816504318558208>'
    text = '<:channel:941816354393178172>'
    nsfw = '<:channel_nsfw:941816355995410432>'
    voice = '<:voice:941816520529571860>'
    emoji = '<:emoji_ghost:941816360059687043>'
    store = '<:store_tag:941816513097240656>'
    invite = '<:invite:941816364132368435>'
    partner = '<:partner:941816501248327700>'
    hypesquad = '<:hypesquad:941816362798559232>'
    nitro = '<:nitro:941816498681446460>'
    staff = '<:staff:941816508957483109>'
    balance = '<:balance:941816154681405481>'
    bravery = '<:bravery:941816350916096050>'
    brilliance = '<:brilliance:941816351721422869>'
    bughunter = '<:bughunter:941816353252323448>'
    supporter = '<:supporter:941816514506530856>'

    booster = '<:booster:941816158863102054>'
    booster2 = '<:booster2:941816160985440297>'
    booster3 = '<:booster3:941816161958527017>'
    booster4 = '<:booster4:941816163795603506>'
    verified = '<:verified:941816517710979162>'

    partnernew = '<:partnernew:941816502766690334>'
    members = '<:members:941816367466831983>'
    stage = '<:stagechannel:941816511692156928>'
    stafftools = '<:stafftools:941816510333202452>'
    thread = '<:threadchannel:941816516033269811>'
    mention = '<:mention:941816367466831983>'
    rules = '<:rules:941816505849491586>'
    news = '<:news:941816373062029332>'

    ban_create = '<:bancreate:941816156191346759>'
    ban_delete = '<:bandelete:941816157567070298>'
    member_leave = '<:memberleave:941816365772341298>'
    message_delete = '<:messagedelete:941816371401064490>'
    emote_create = '<:emotecreate:941816361561243700>'

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
        if chann.type == ChannelType.category:
            return ""
        if str(chann.type).endswith('thread'):
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
            await cursor.execute(
                'INSERT OR IGNORE INTO reminders VALUES (?, ?, ?, ?, ?)',
                (self.message_id,
                 self.user.id,
                 self.reminder,
                 int(self.end_time.timestamp()),
                 self.destination.id)
            )

        await self.bot.db.commit()
        await discord.utils.sleep_until(self.end_time)

        embed = discord.Embed(
            title='Reminder!',
            description=self.reminder,
            color=discord.Color.green()
        )

        if isinstance(self.destination, TextChannel):
            embed.set_footer(
                icon_url=fix_url(self.user.display_avatar),
                text=f'Reminder sent by {self.user}'
            )

        else:
            embed.set_footer(
                icon_url=fix_url(self.user.display_avatar),
                text=f'This reminder is sent by you!'
            )

        try:
            await self.destination.send(
                f"**Hey {self.user.mention},**" if isinstance(self.destination, TextChannel) else None,
                embed=embed
            )

        except (discord.Forbidden, discord.HTTPException):
            pass

        await self.remove()

    async def remove(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute('DELETE FROM reminders WHERE id = (?)', (self.message_id,))
        await self.bot.db.commit()

        self.bot.reminders[self.id] = None
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
            await cursor.execute(
                'REPLACE INTO basic_config VALUES(?, ?, ?, ?)',
                (
                    config.guild.id,
                    config.prefix,
                    config.snipe,
                    config.mute_role.id if config.mute_role else None
                )
            )

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
            await cursor.execute(
                'REPLACE INTO logging_config VALUES(?, ?, ?, ?, ?, ?)',
                (
                    config.guild.id,
                    config.kick_channel.id if config.kick_channel else None,
                    config.ban_channel.id if config.ban_channel else None,
                    config.purge_channel.id if config.purge_channel else None,
                    config.delete_channel.id if config.delete_channel else None,
                    config.mute_channel.id if config.mute_channel else None
                )
            )

        await bot.db.commit()

        bot.logging_configs[config.guild.id] = config

        return config


class MissingAPIKey(commands.CommandError):
    pass
