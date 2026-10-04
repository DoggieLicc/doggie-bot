import asyncio
import os
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from aiohttp import ClientSession
import yaml
import discord
from discord import TextChannel, ChannelType, Message, User, Guild, Role, app_commands, Thread, ui
from discord.ext import commands
from discord.abc import GuildChannel, PrivateChannel
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
    'DoggieBotException',
    'CustomContext'
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
            name='prefix',
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


class CustomContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.bot: CustomBot = self.bot
        self.error_handled = False

    if not TYPE_CHECKING:
        async def defer(self, *args, **kwargs):
            if 'ephemeral' not in kwargs and self.interaction and self.channel.type != ChannelType.private:
                if not self.guild or not self.guild.owner_id:
                    kwargs['ephemeral'] = True

                if self.guild and (not self.interaction.permissions.send_messages or not self.interaction.app_permissions.send_messages):
                    kwargs['ephemeral'] = True

            return await super().defer(*args, **kwargs)

        async def send(self, *args, **kwargs):
            if 'ephemeral' not in kwargs and self.interaction and self.channel.type != ChannelType.private:
                if not self.guild or not self.guild.owner_id:
                    kwargs['ephemeral'] = True

                if self.guild and (not self.interaction.permissions.send_messages or not self.interaction.app_permissions.send_messages):
                    kwargs['ephemeral'] = True

            return await super().send(*args, **kwargs)


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
        self.config['e621_username'] = yaml_config.get('e621_username') or os.getenv('E621_USERNAME')
        self.config['e621_api_key'] = yaml_config.get('e621_api_key') or os.getenv('E621_API_KEY')
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

        self.user_selected_messages: dict[int, str] = {}
        self.reminders: dict[int, Reminder | None] = {}
        self.basic_configs: dict[int, BasicConfig] = {}
        self.logging_configs: dict[int, LoggingConfig] = {}
        self.sniped: list[Message] = []
        self.cogs_list: list[str] = []

        self.fully_ready = False
        self.start_time: datetime = None  # type: ignore
        self.session: ClientSession | None = None

    async def setup_hook(self):
        self.loop.create_task(self.startup())

    async def get_context(self, message: Message, *, cls=CustomContext) -> CustomContext:
        # pylint: disable=arguments-differ
        return await super().get_context(message, cls=cls)

    async def on_message(self, message):
        # pylint: disable=arguments-differ

        if not self.fully_ready:
            await self.wait_for('fully_ready')

        if not self.user:
            return

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

        return await self.fetch_user(self.owner_id or list(self.owner_ids if self.owner_ids else [])[0])

    async def load_reminders(self):
        async with self.db.conn() as conn:
            async with conn.cursor() as cursor:
                for row in await cursor.execute('SELECT * FROM reminders'):
                    message_id: int = row['id']
                    try:
                        user: User | None = await self.fetch_user(row['user_id'])
                    except discord.NotFound:
                        user = None
                    reminder: str = row['reminder']
                    end_time: int = row['end_time']
                    destination = self.get_channel(row['destination']) or user

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
                    prefix = row['prefix'] or None
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
                        await conn.commit()
                        continue

                    self.basic_configs[config.guild.id] = config

    async def load_logging_config(self):
        async with self.db.conn() as conn:
            async with conn.cursor() as cursor:
                for row in await cursor.execute('SELECT * FROM logging_config'):
                    guild = self.get_guild(row['guild_id'])

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

    @staticmethod
    def get_custom_prefix(_bot: 'CustomBot', message: Message):
        default_prefixes = ['doggie.', 'Doggie.', 'dog.', 'Dog.']

        if not message.guild:
            return commands.when_mentioned_or(*default_prefixes)(_bot, message)

        config = _bot.basic_configs.get(message.guild.id)

        if not config or not config.prefix:
            return commands.when_mentioned_or(*default_prefixes)(_bot, message)

        return commands.when_mentioned_or(config.prefix)(_bot, message)

    def check_commands(self, cmds: list[app_commands.Command[Any, ..., Any] | app_commands.Group]):
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
    bot_tag = '<:botTag:1556430809379110942>'
    discord = '<:discord:1556430810360455239>'
    owner = '<:owner:1556430811618877521>'
    slowmode = '<:slowmode:1556430812532969573>'
    check = '<:check:1556430813963362354>'
    xmark = '<:xmark:1556430815020318730>'
    role = '<:role:1556430816186208326>'
    text = '<:channel:1556430817507409993>'
    nsfw = '<:channel_nsfw:1556430818837266455>'
    voice = '<:voice:1556430820640821338>'
    emoji = '<:emoji_ghost:1556430821840130090>'
    store = '<:store_tag:1556430823140364378>'
    invite = '<:invite:1556430824323285032>'
    partner = '<:partner:1556430825418133524>'
    hypesquad = '<:hypesquad:1556430826202464339>'
    nitro = '<:nitro:1556430827506770091>'
    staff = '<:staff:1556430828643553350>'
    balance = '<:balance:1556430829746393098>'
    bravery = '<:bravery:1556430831025659988>'
    brilliance = '<:brilliance:1556430832741261495>'
    bughunter = '<:bughunter:1556430833705812029>'
    supporter = '<:supporter:1556430834334961777>'
    booster = '<:booster:1556430835966812246>'
    booster2 = '<:booster2:1556430837124304936>'
    booster3 = '<:booster3:1556430838378266724>'
    booster4 = '<:booster4:1556430839280050208>'
    verified = '<:verified:1556430840555114496>'
    partnernew = '<:partnernew:1556430841654157414>'
    members = '<:members:1556430842698403852>'
    stage = '<:stagechannel:1556430852291039418>'
    stafftools = '<:stafftools:1556430853947658240>'
    thread = '<:threadchannel:1556430854924927048>'
    mention = '<:mention:1556430855961055295>'
    rules = '<:rules:1556430857055502346>'
    news = '<:news:1556430858460864613>'
    ban_create = '<:bancreate:1556430861090685000>'
    ban_delete = '<:bandelete:1556430862055243838>'
    member_leave = '<:memberleave:1556430863275790486>'
    message_delete = '<:messagedelete:1556430864303394927>'
    emote_create = '<:emotecreate:1556430865226010656>'
    timeout = '<:timeout:1556430866211676312>'

    @staticmethod
    def channel(chann: discord.abc.GuildChannel | discord.PartialInviteChannel | discord.Thread | discord.Object):
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
            return ''
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
        if 'staff' in flags:
            badges.append(Emotes.staff)
        if 'partner' in flags:
            badges.append(Emotes.partner)
        if 'hypesquad' in flags:
            badges.append(Emotes.hypesquad)
        if 'bug_hunter' in flags:
            badges.append(Emotes.bughunter)
        if 'early_supporter' in flags:
            badges.append(Emotes.supporter)
        if 'hypesquad_briliance' in flags:
            badges.append(Emotes.brilliance)
        if 'hypesquad_bravery' in flags:
            badges.append(Emotes.bravery)
        if 'hypesquad_balance' in flags:
            badges.append(Emotes.balance)
        if 'hypesquad_brilliance' in flags:
            badges.append(Emotes.brilliance)
        if 'verified_bot' in flags:
            badges.append(Emotes.verified)
        if 'verified_bot_developer' in flags:
            badges.append(Emotes.verified)

        if guess_user_nitro_status(user):
            badges.append(Emotes.nitro)

        return ' '.join(badges)


@dataclass
class Reminder:
    message_id: int
    user: User
    reminder: str
    destination: GuildChannel | User | Thread | PrivateChannel
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
            await self.destination.send(  # pyright: ignore[reportAttributeAccessIssue]
                f'**Hey {self.user.mention},**' if isinstance(self.destination, TextChannel) else None,
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
    prefix: str | None = None
    snipe: bool | None = None
    mute_role: Role | None = None

    async def set_config(self, bot: CustomBot, **kwargs) -> 'BasicConfig':
        config = replace(self, **kwargs)

        await bot.db.execute(
            'REPLACE INTO basic_config VALUES(?, ?, ?, ?)',
            (
                config.guild.id,
                config.prefix,
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
    def __init__(self, title, description, view: ui.View | None = None):
        self.title = str(title)
        self.description = str(description)
        self.view = view

class MissingAPIKey(DoggieBotException):
    pass
