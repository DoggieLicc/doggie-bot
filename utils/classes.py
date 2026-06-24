import asyncio
import os
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

import yaml
import discord
from discord import TextChannel, ChannelType, Message, User, Guild, Role, app_commands
from discord.ext import commands
from loguru import logger

from utils.funcs import guess_user_nitro_status, create_embed, fix_url
from utils.db_helper import *

__all__ = [
    'CustomBot',
    'Emotes',
    'Reminder',
    'BasicConfig',
    'LoggingConfig',
    'MissingAPIKey',
    'DoggieBotException'
]

dirname = os.getcwd()
config_file = os.path.join(dirname, 'config.yaml')


BasicConfigTable = BaseTable(
    name='basic_config',
    columns=[
        BaseColumn(
            name='guild_id',
            datatype='integer',
            addit_schema='PRIMARY KEY'
        ),
        BaseColumn(
            name='prefix',  # Unused now
            datatype='text'
        ),
        BaseColumn(
            name='snipe',
            datatype='integer'
        ),
        BaseColumn(
            name='mute_role',
            datatype='integer'
        )
    ]
)

LoggingConfigTable = BaseTable(
    name='logging_config',
    columns=[
        BaseColumn(
            name='guild_id',
            datatype='integer',
            addit_schema='PRIMARY KEY'
        ),
        BaseColumn(
            name='kick_channel',
            datatype='integer'
        ),
        BaseColumn(
            name='ban_channel',
            datatype='integer'
        ),
        BaseColumn(
            name='purge_channel',
            datatype='integer'
        ),
        BaseColumn(
            name='delete_channel',
            datatype='integer'
        ),
        BaseColumn(
            name='mute_channel',
            datatype='integer'
        )
    ]
)

RemindersTable = BaseTable(
    name='reminders',
    columns=[
        BaseColumn(
            name='id',
            datatype='integer',
            addit_schema='PRIMARY KEY'
        ),
        BaseColumn(
            name='user_id',
            datatype='integer'
        ),
        BaseColumn(
            name='reminder',
            datatype='text'
        ),
        BaseColumn(
            name='end_time',
            datatype='integer'
        ),
        BaseColumn(
            name='destination',
            datatype='integer'
        )
    ]
)

ALL_DB_TABLES = [BasicConfigTable, LoggingConfigTable, RemindersTable]


class CustomBot(commands.Bot):
    # noinspection PyTypeChecker
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        yaml_config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='UTF-8') as file:
                yaml_config = yaml.safe_load(file)

        self.config = {}

        self.config['bot_token'] = yaml_config.get('bot_token') or os.getenv('BOT_TOKEN')
        self.config['osu_client_secret'] = yaml_config.get('osu_client_secret') or os.getenv('OSU_CLIENT_SECRET')
        self.config['osu_client_id'] = yaml_config.get('osu_client_id') or os.getenv('OSU_CLIENT_ID') or 0
        self.config['unsplash_api_key'] = yaml_config.get('unsplash_api_key') or os.getenv('UNSPLASH_API_KEY')
        self.config['saucenao_api_key'] = yaml_config.get('saucenao_api_key') or os.getenv('SAUCENAO_API_KEY')
        self.config['data_dir'] = yaml_config.get('data_dir') or os.getenv('DATA_DIR') or '/data'
        self.config['prometheus_port'] = yaml_config.get('prometheus_port') or os.getenv('PROMETHEUS_PORT') or 8000
        self.config['enable_prometheus'] = yaml_config.get('enable_prometheus') or os.getenv('ENABLE_PROMETHEUS') or False

        if isinstance(self.config['enable_prometheus'], str):
            if self.config['enable_prometheus'].lower() == 'true':
                self.config['enable_prometheus'] = True
            else:
                self.config['enable_prometheus'] = False

        self.db_file = os.path.join(self.config['data_dir'], 'data.db')

        self.db = DatabaseHelper(
            ALL_DB_TABLES,
            1,
            self.db_file,
            check_same_thread=False
        )

        self.reminders: dict[int, Reminder] = {}
        self.basic_configs: dict[int, BasicConfig] = {}
        self.logging_configs: dict[int, LoggingConfig] = {}
        self.sniped: list[Message] = []
        self.cogs_list: list[str] = []

        self.fully_ready = False
        self.start_time: datetime = None  # type: ignore
        self.session = None

    async def setup_hook(self):
        self.loop.create_task(self.startup())

    async def on_message(self, message):
        # pylint: disable=arguments-differ

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
        await self.db.startup()
        await self.wait_until_ready()

        self.start_time: datetime = datetime.now(timezone.utc)

        await self.load_reminders()
        await self.load_basic_config()
        await self.load_logging_config()

        logger.info('All configurations loaded!')
        self.fully_ready = True
        self.dispatch('fully_ready')

    async def get_owner(self) -> User:
        if not self.owner_id and not self.owner_ids:
            info = await self.application_info()
            self.owner_id = info.owner.id

        return await self.fetch_user(self.owner_id or list(self.owner_ids)[0])

    async def load_reminders(self):
        async with self.db.conn() as conn:
            async with conn.cursor() as cursor:
                for row in await cursor.execute('SELECT * FROM reminders'):
                    message_id: int = row['id']
                    try:
                        user: User = await self.fetch_user(row['user_id'])
                    except discord.NotFound:
                        user: None = None
                    reminder: str = row['reminder']
                    end_time: int = row['end_time']
                    destination: User | TextChannel = self.get_channel(row['destination']) or user

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
        async with self.db.conn() as conn:
            async with conn.cursor() as cursor:
                for row in await cursor.execute('SELECT * FROM basic_config'):
                    guild = self.get_guild(row['guild_id'])
                    snipe = bool(row['snipe'])
                    mute_role = guild.get_role(row['mute_role']) if guild else None

                    if not guild:
                        continue

                    config = BasicConfig(
                        guild=guild,
                        snipe=snipe,
                        mute_role=mute_role
                    )

                    if row['mute_role'] and not mute_role:
                        await cursor.execute('UPDATE basic_config SET mute_role = ? WHERE guild_id = ?', (None, guild.id))
                        await conn.commit()
                        continue

                    self.basic_configs[config.guild.id] = config

    async def load_logging_config(self):
        async with self.db.conn() as conn:
            async with conn.cursor() as cursor:
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

    def get_basic_config(self, guild: Guild) -> 'BasicConfig':
        return self.basic_configs.get(guild.id, BasicConfig(guild))

    def get_logging_config(self, guild: Guild) -> 'LoggingConfig':
        return self.logging_configs.get(guild.id, LoggingConfig(guild))

    def check_commands(self, cmds: app_commands.ContextMenu | app_commands.Command | app_commands.Group):
        for command in cmds:
            if isinstance(command, app_commands.Group):
                self.check_commands(command.commands)
                continue

            if isinstance(command, app_commands.ContextMenu):
                continue

            if command.description == '…':
                logger.warning('App command "{}" missing description!', command.qualified_name)

            for parameter in command.parameters:
                if parameter.description == '…':
                    logger.warning('Parameter "{}" of App command "{}" missing description!', parameter.name, command.qualified_name)

    def check_all_commands(self):
        cmds = list(c for c in self.tree.walk_commands())
        self.check_commands(cmds)

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
    timeout = '<:timeout:1519145193335427185>'

    @staticmethod
    def channel(chann: discord.abc.GuildChannel):
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
        return ''

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


@dataclass
class Reminder:
    message_id: int
    user: User
    reminder: str
    destination: User | TextChannel
    end_time: datetime
    bot: CustomBot
    id: int = field(init=False)
    task: asyncio.Future = field(init=False)

    def __post_init__(self):
        self.id = len(self.bot.reminders) + 1
        self.task = asyncio.ensure_future(self.send_reminder())
        self.bot.reminders[self.id] = self

    async def send_reminder(self):
        await self.bot.db.execute(
            'INSERT OR IGNORE INTO reminders VALUES (?, ?, ?, ?, ?)',
            (
                self.message_id,
                self.user.id,
                self.reminder,
                int(self.end_time.timestamp()),
                self.destination.id
            )
        )

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
                text='This reminder is sent by you!'
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
        await self.bot.db.execute('DELETE FROM reminders WHERE id = (?)', (self.message_id,))

        self.bot.reminders[self.id] = None
        self.task.cancel()

    def __str__(self):
        return self.reminder


@dataclass(frozen=True)
class BasicConfig:
    guild: discord.Guild
    snipe: bool | None = None
    mute_role: Role | None = None

    async def set_config(self, bot: CustomBot, **kwargs) -> 'BasicConfig':
        config = replace(self, **kwargs)

        await bot.db.execute(
            'REPLACE INTO basic_config VALUES(?, ?, ?, ?)',
            (
                config.guild.id,
                None,  # Unused prefix config
                config.snipe,
                config.mute_role.id if config.mute_role else None
            )
        )

        bot.basic_configs[config.guild.id] = config
        return config


@dataclass(frozen=True)
class LoggingConfig:
    guild: discord.Guild
    kick_channel: TextChannel | None = None
    ban_channel: TextChannel | None = None
    purge_channel: TextChannel | None = None
    delete_channel: TextChannel | None = None
    mute_channel: TextChannel | None = None

    async def set_config(self, bot: CustomBot, **kwargs) -> 'LoggingConfig':
        config = replace(self, **kwargs)

        await bot.db.execute(
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

        bot.logging_configs[config.guild.id] = config
        return config


class DoggieBotException(Exception):
    def __init__(self, title, description):
        self.title = str(title)
        self.description = str(description)

class MissingAPIKey(DoggieBotException):
    pass
