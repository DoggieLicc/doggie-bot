import discord
from discord.ext import commands

from utils import CustomBot, CustomHelp


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
    'cogs.error'
]


def get_prefix(_bot: CustomBot, message: discord.Message):
    if not message.guild:
        return commands.when_mentioned_or('doggie.')(_bot, message)

    config = _bot.basic_configs.get(message.guild.id)

    if not config or not config.prefix:
        return commands.when_mentioned_or('doggie.')(_bot, message)

    else:
        return commands.when_mentioned_or(config.prefix)(_bot, message)


intents = discord.Intents(
    reactions=True,
    messages=True,
    members=True,
    guilds=True,
    bans=True
)


bot = CustomBot(
    activity=discord.Game(name='Default prefixes: "@Doggie Bot" or "doggie."'),
    allowed_mentions=discord.AllowedMentions(replied_user=False),
    command_prefix=get_prefix,
    help_command=CustomHelp(),
    strip_after_prefix=True,
    case_insensitive=True,
    max_messages=10000,
    intents=intents,
)

if __name__ == '__main__':
    for cog in cogs:
        bot.load_extension(cog)

    bot.run(bot.config['bot_token'])
