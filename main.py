import asyncio
import logging
import inspect

import discord
import aiohttp
from discord.ext.prometheus import PrometheusCog, PrometheusLoggingHandler
from loguru import logger

import utils

cogs = [
    'cogs.info',
    'cogs.mod',
    'cogs.reminder',
    'cogs.misc',
    'cogs.game',
    'cogs.dev',
    'cogs.utility',
    'cogs.image',
    'cogs.config',
    'cogs.events',
    'cogs.error',
    'cogs.randomc'
]


headers = {
    'User-Agent': 'DoggieBot (@doggielicc); "A Discord bot")'
}


intents = discord.Intents(
    message_content=True,
    reactions=True,
    messages=True,
    members=True,
    guilds=True,
    emojis=True,
    bans=True
)

D_BOT_TOKEN = '=PLACEHOLDER='

class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        message = record.getMessage().replace(D_BOT_TOKEN, 'BOT_TOKEN')
        logger.opt(depth=depth, exception=record.exc_info).log(level, message)


async def startup():
    discord.utils.setup_logging(handler=InterceptHandler())

    bot = utils.CustomBot(
        activity=discord.Game(name='Default prefixes: "@Doggie Bot" or "doggie." (Or use slash commands!)'),
        allowed_mentions=discord.AllowedMentions.none(),
        command_prefix=utils.CustomBot.get_custom_prefix,
        help_command=utils.CustomHelp(),
        strip_after_prefix=True,
        case_insensitive=True,
        max_messages=20000,
        intents=intents,
        allowed_installs=discord.app_commands.AppInstallationType(guild=True, user=True),
        allowed_contexts=discord.app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)
    )

    global D_BOT_TOKEN  # pylint: disable=global-statement
    D_BOT_TOKEN = bot.config['bot_token']

    if bot.config['enable_prometheus']:
        port = int(bot.config.get('prometheus_port', 8000))
        logger.info('Prometheus enabled on port {}', port)
        logger.add(PrometheusLoggingHandler())
        await bot.add_cog(PrometheusCog(bot, port=port))

    bot.cogs_list = cogs
    for cog in cogs:
        await bot.load_extension(cog)
        logger.debug('Loaded cog: {}', cog)

    bot.check_all_commands()

    async with aiohttp.ClientSession(headers=headers) as session:
        bot.session = session
        await bot.start(bot.config['bot_token'])

if __name__ == '__main__':
    asyncio.run(startup())
