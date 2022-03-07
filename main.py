import discord
import yaml
import asqlite
import utils
import asyncio
import inspect
import commands

from discord import app_commands
from datetime import datetime, timezone
from typing import Dict, Union


GUILD = discord.Object(id=930499492686487602)

headers = {
    'User-Agent': 'DoggieBot (Doggie#8512; "A Discord bot")'
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


class CustomClient(discord.Client):
    # noinspection PyTypeChecker
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with open('config.yaml', 'r') as file:
            self.config = yaml.safe_load(file)

        self.tree: app_commands.CommandTree = None

        self.reminders: Dict[int, utils.Reminder] = {}

        self.start_time: datetime = None  # type: ignore
        self.db: asqlite.Connection = None  # type: ignore
        self.session = None

        self.loop.create_task(self.startup())

    async def startup(self):
        await self.wait_until_ready()

        self.start_time: datetime = datetime.now(timezone.utc)

        self.db: asqlite.Connection = await asqlite.connect('data.db', check_same_thread=False)

        await self.load_reminders()

        await self.tree.sync(guild=GUILD)

    async def close(self):
        await self.db.close()
        await super().close()

    async def load_reminders(self):
        async with self.db.cursor() as cursor:
            for row in await cursor.execute('SELECT * FROM reminders'):
                message_id: int = row['id']
                try:
                    user: discord.User = await self.fetch_user(row['user_id'])
                except discord.NotFound:
                    user: None = None
                reminder: str = row['reminder']
                end_time: int = row['end_time']
                destination: Union[discord.User, discord.TextChannel] = self.get_channel(row['destination']) or user

                if destination is None or user is None:
                    continue

                _reminder = utils.Reminder(
                    message_id=message_id,
                    user=user,
                    reminder=reminder,
                    destination=destination,
                    end_time=datetime.fromtimestamp(end_time, timezone.utc),
                    bot=self
                )

                self.reminders[_reminder.id] = _reminder


async def startup():
    client = CustomClient(
        activity=discord.Game(name='OwO'),
        allowed_mentions=discord.AllowedMentions(replied_user=False),
        intents=intents,
    )

    tree = client.tree = app_commands.CommandTree(client)

    cmds = [v for n, v in inspect.getmembers(commands) if isinstance(v, app_commands.Command)]
    print(cmds)

    for cmd in cmds:
        tree.add_command(cmd, guild=GUILD)

    await client.start(client.config['bot_token'])


if __name__ == '__main__':
    asyncio.run(startup())
