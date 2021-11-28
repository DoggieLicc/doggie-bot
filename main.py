import discord
import asyncio
import aiohttp
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
    'User-Agent': 'DoggieBot (Doggie#8512; "A Discord bot")'
}


intents = discord.Intents(
    reactions=True,
    messages=True,
    members=True,
    guilds=True,
    emojis=True,
    bans=True
)


async def startup():
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

    bot.cogs_list = cogs

    for cog in cogs:
        bot.load_extension(cog)

    async with aiohttp.ClientSession(headers=headers) as session:
        bot.session = session
        await bot.start(bot.config['bot_token'])

if __name__ == '__main__':
    asyncio.run(startup())
