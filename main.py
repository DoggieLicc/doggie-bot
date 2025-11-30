import discord
import asyncio
import aiohttp
import logging
import inspect

import utils

from loguru import logger
from discord.ext.prometheus import PrometheusCog, PrometheusLoggingHandler


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

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


async def startup():
    discord.utils.setup_logging(handler=InterceptHandler())

    bot = utils.CustomBot(
        activity=discord.Game(name='Default prefixes: "@Doggie Bot" or "doggie."'),
        allowed_mentions=discord.AllowedMentions(replied_user=False),
        command_prefix=utils.CustomBot.get_custom_prefix,
        help_command=utils.CustomHelp(),
        strip_after_prefix=True,
        case_insensitive=True,
        max_messages=20000,
        intents=intents,
    )

    if bot.config['enable_prometheus']:
        port = int(bot.config.get('prometheus_port', 8000))
        logger.info('Prometheus enabled on port %d', port)
        logger.add(PrometheusLoggingHandler())
        await bot.add_cog(PrometheusCog(bot, port=port))

    bot.cogs_list = cogs
    for cog in cogs:
        await bot.load_extension(cog)
        logger.debug('Loaded cog: {}', cog)

    async with aiohttp.ClientSession(headers=headers) as session:
        bot.session = session
        await bot.start(bot.config['bot_token'])

if __name__ == '__main__':
    asyncio.run(startup())
