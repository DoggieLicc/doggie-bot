import discord

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
    'cogs.error'
]


intents = discord.Intents(
    reactions=True,
    messages=True,
    members=True,
    guilds=True,
    bans=True
)


bot = utils.CustomBot(
    activity=discord.Game(name='Default prefixes: "@Doggie Bot" or "doggie."'),
    allowed_mentions=discord.AllowedMentions(replied_user=False),
    command_prefix=utils.CustomBot.get_custom_prefix,
    help_command=utils.CustomHelp(),
    strip_after_prefix=True,
    case_insensitive=True,
    max_messages=10000,
    intents=intents,
)

if __name__ == '__main__':
    for cog in cogs:
        bot.load_extension(cog)

    bot.run(bot.config['bot_token'])
