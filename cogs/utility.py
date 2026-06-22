import discord
import asyncio
import time
import utils
import itertools

from discord import app_commands, Interaction, Attachment, PartialEmoji
from discord.app_commands import Transform
from discord.ext.commands import Greedy, BotMissingPermissions, MissingPermissions, MissingRequiredArgument, Cog

from datetime import timedelta
from typing import Union, List, Optional, Dict
from collections import Counter


def get_hoisters(members: List[discord.Member]):
    def check(member):
        value = ord(member.display_name[0])
        return 0 <= value <= 47 or 58 <= value <= 64

    members = sorted(members, key=lambda m: m.display_name)
    return list(itertools.takewhile(check, members))[:200]


class RecentJoinsMenu(utils.EntryMenu):
    async def get_page_contents(self):
        entries = self.get_page_items()
        embed = utils.create_embed(
            self.owner,
            title=f'Showing recent joins for this server'
                  f'({self.current_index}/{self.max_page}):'
        )
        for member in entries:
            joined_at = utils.user_friendly_dt(member.joined_at)
            created_at = utils.user_friendly_dt(member.created_at)
            embed.add_field(
                name=f'{member}',
                value=f'ID: {member.id}\n'
                      f'Joined at: {joined_at}\n'
                      f'Created at: {created_at}', inline=False
            )

        return {"embed": embed}


class RecentAccounts(utils.EntryMenu):
    async def get_page_contents(self):
        embed = utils.create_embed(
            self.owner,
            title=f'Showing newest accounts in this server '
                  f'({self.current_index}/{self.max_page}):'
        )
        for member in self.get_page_items():
            joined_at = utils.user_friendly_dt(member.joined_at)
            created_at = utils.user_friendly_dt(member.created_at)
            embed.add_field(
                name=f'{member}',
                value=f'ID: {member.id}\n'
                      f'Joined at: {joined_at}\n'
                      f'Created at: {created_at}', inline=False
            )

        return {"embed": embed}


class HoistersMenu(utils.EntryMenu):
    async def get_page_contents(self):
        embed = utils.create_embed(
            self.owner,
            title=f'Showing potential hoisters for this server '
                  f'({self.current_index}/{self.max_page}):'
        )

        for member in self.get_page_items():
            embed.add_field(
                name=f'{member.display_name}',
                value=f'Username: {member} ({member.mention})\n'
                      f'ID: {member.id}',
                inline=False
            )

        return embed


class HoistersIDMenu(utils.EntryMenu):
    async def get_page_contents(self):
        return {"content": " ".join(map(str, self.get_page_items())) or 'N/A'}


class SauceMenu(utils.EntryMenu):
    async def get_page_contents(self):
        result = self.get_page_items()[0]

        embed = utils.create_embed(
            self.owner,
            title=f'Result {self.current_index}/{self.max_page}:',
            thumbnail=result['header']['thumbnail']
        )

        if urls := result['data'].get('ext_urls'):
            embed.add_field(name='URL:', value=urls[0], inline=False)

        if title := result['data'].get('title'):
            embed.add_field(name='Title:', value=title, inline=False)

        if (author_name := result['data'].get('author_name')) or (result['data'].get('author_url')):
            author_url = result['data'].get('author_url')
            if author_name and author_url:
                author_str = f'[{author_name}]({author_url})'
            else:
                author_str = author_name or author_url

            embed.add_field(name='Author:', value=author_str, inline=False)

        embed.add_field(name='Index:', value=result['header']['index_name'].split(' - ')[0].split(': ')[1], inline=False)

        embed.add_field(name='Similarity:', value=result['header']['similarity'] + '%', inline=False)

        embed.add_field(name='Potentially explicit?', value='Yes' if result['header']['hidden'] else 'No', inline=False)

        return {"embed": embed}


class PollSelect(discord.ui.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_options: Dict[int, str] = {}

    async def callback(self, interaction: discord.Interaction):
        self.selected_options[interaction.user.id] = self.values[0]
        await interaction.response.defer()


class UtilityCog(Cog, name="Utility"):
    """Utility commands that may be useful to you!"""

    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @app_commands.command()
    @app_commands.guild_only()
    async def recentjoins(self, interaction: Interaction):
        """Shows the most recent joins in the current server"""

        await interaction.response.defer(thinking=True, ephemeral=True)

        members = sorted(interaction.guild.members, key=lambda m: m.joined_at, reverse=True)[:100]
        view = RecentJoinsMenu(interaction.user, members, 10)

        await interaction.edit_original_response(view=view, **await view.get_page_contents())

    @app_commands.guild_only()
    @app_commands.command()
    async def selfbot(self, interaction: Interaction):
        """Creates a fake Nitro giveaway to catch a selfbot (Automated user accounts which auto-react to giveaways)"""

        selfbot_embed = discord.Embed(
            color=discord.Color.green(),
            title='Giveaway',
            description=f'**Prize:** Discord Nitro\n'
                        f'**Time left:** Infinity\n'
                        f'**Hosted by:** {interaction.guild.owner.mention}\n'
                        f'**React with :tada: to participate!**'
        )

        selfbot_embed.set_author(name='Discord Nitro')

        message = await interaction.response.send_message(
            ':tada: **GIVEAWAY** :tada: :yay:',
            embed=selfbot_embed
        ).resource

        try:
            await message.add_reaction('\N{PARTY POPPER}')
        except discord.DiscordException:
            pass

        t = time.perf_counter()
        seen_users = set()
        users_message: Optional[discord.Message] = None

        def check(_reaction, _user):
            if _reaction.message == message and str(_reaction.emoji) == '\N{PARTY POPPER}' \
                    and not _user.bot and _user not in seen_users:
                seen_users.add(_user)
                return True

            return False

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=600, check=check)
            except asyncio.TimeoutError:

                if not seen_users:
                    embed = utils.create_embed(
                        interaction.user,
                        title='Test timed out!',
                        description=f'No one reacted within 10 minutes!',
                        color=discord.Color.red()
                    )

                    await interaction.edit_original_response(embeds=[selfbot_embed, embed])

                return

            else:
                if user == interaction.user:
                    embed = utils.create_embed(
                        interaction.user,
                        title='Test canceled!',
                        description=f'You reacted to your own test, so it was canceled.\nAnyways, '
                                    f'your time is {round(time.perf_counter() - t, 2)} seconds.',
                        color=discord.Color.red()
                    )

                    return await interaction.edit_original_response(embeds=[selfbot_embed, embed])

                else:
                    if not len(message.embeds) > 1:
                        embed = utils.create_embed(
                            interaction.user,
                            title='Reaction found!',
                            description=f'{user} (ID: {user.id})\nreacted with {reaction} in '
                                        f'{round(time.perf_counter() - t, 2)} seconds'
                        )

                        message = await interaction.edit_original_response(embeds=[selfbot_embed, embed])
                    else:
                        new_msg = f'\n\n{user} (ID: {user.id})\nreacted with {reaction} in ' \
                                  f'{round(time.perf_counter() - t, 2)} seconds'

                        embed = utils.create_embed(
                            interaction.user,
                            title='Reactions found!',
                            description=message.embeds[0].description + new_msg
                        )

                        message = await interaction.edit_original_response(embeds=[selfbot_embed, embed])

    @app_commands.guild_only()
    @app_commands.command()
    async def hoisters(self, interaction: Interaction):
        """Shows a list of members who have names made to 'hoist' themselves to the top of the member list!"""

        hoisters = get_hoisters(interaction.guild.members)

        if not hoisters:
            embed = utils.create_embed(
                interaction.user,
                title="No hoisters found!",
                description="There weren't any members with odd characters found!",
                color=discord.Color.red()
            )

            return await interaction.response.send_message(embed=embed, ephemeral=True)

        view = HoistersMenu(interaction.user, hoisters, 10)

        await interaction.response.send_message(view=view, **await view.get_page_contents(), ephemeral=True)

    @utils.client_has_permissions(manage_webhooks=True)
    @app_commands.default_permissions(manage_webhooks=True)
    @app_commands.guild_only()
    @app_commands.command()
    async def send(self, interaction: Interaction):
        """Send a custom webhook message to specified channel"""
        ### pylint: disable=all

        response = await interaction.response.send_modal()
        channel = ...

        if not channel.permissions_for(interaction.guild.me).manage_webhooks:
            raise BotMissingPermissions(['Manage Webhooks'])

        if not channel.permissions_for(interaction.user).manage_webhooks:
            raise MissingPermissions(['Manage Webhooks'])

        webhooks = await channel.webhooks()

        sending_webhooks = [w for w in webhooks if w.name == 'DoggieBot Sending Webhook']

        if not sending_webhooks:
            sending_webhook = await channel.create_webhook(name='DoggieBot Sending Webhook')
        else:
            sending_webhook = sending_webhooks[0]

        await sending_webhook.send(
            #**dict(flags),
            #allowed_mentions=discord.AllowedMentions.none(),
            #files=[await file.to_file() for file in attachments]
        )

    @app_commands.guild_only()
    @app_commands.default_permissions(create_expressions=True)
    @utils.client_has_permissions(create_expressions=True)
    @app_commands.command()
    async def stealemote(
        self,
        interaction: Interaction,
        emotes: Transform[list[PartialEmoji], utils.MultiplePartialEmoteTransformer]
    ):
        """Adds the specified emotes to your server!"""

        added, not_added = [], []
        embed = discord.Embed()

        await interaction.response.defer(thinking=True)

        for emote in emotes:
            if isinstance(emote, discord.Emoji) and emote.guild == interaction.guild:
                not_added.append(emote)
                continue

            try:
                added.append(await interaction.guild.create_custom_emoji(
                    name=emote.name,
                    image=await emote.read(),
                    reason=f'Added by {interaction.user} ({interaction.user.id})')
                )
            except (discord.DiscordException, discord.HTTPException, discord.NotFound, discord.Forbidden):
                not_added.append(emote)

        if not added:
            embed = utils.create_embed(
                interaction.user,
                title='Couldn\'t add any emotes!',
                description='Make sure they aren\'t already in this server, and that the bot has permissions!',
                color=discord.Color.red()
            )

        if added and not_added:
            embed = utils.create_embed(
                interaction.user,
                title='Some emotes couldn\'t be added!',
                description='Make sure they aren\'t already in this server, and that the bot has permissions!',
                color=discord.Color.orange()
            )

        if added and not not_added:
            embed = utils.create_embed(
                interaction.user,
                title='Emotes successfully added!'
            )

        if added:
            embed.add_field(
                name='Emotes added:',
                value=' '.join(map(str, added)),
                inline=False
            )

        if not_added:
            embed.add_field(
                name='Emotes not added:',
                value=' '.join(map(str, not_added)),
                inline=False
            )

        await interaction.edit_original_response(embed=embed)

    @app_commands.guild_only()
    @app_commands.command()
    async def newaccounts(self, interaction: Interaction):
        """Shows the newest accounts in this server!"""

        members = sorted(interaction.guild.members, key=lambda m: m.created_at, reverse=True)[:200]
        view = RecentAccounts(Interaction.user, members, 10)
        await interaction.response.send_message(view=view, **await view.get_page_contents(), ephemeral=True)

    @app_commands.command(nsfw=True)
    async def saucenao(
        self,
        interaction: Interaction,
        image: Attachment | None = None,
        image_url: str | None = None
    ):
        """Gets the source of an image using SauceNAO, usually for art. Most anime databases are disabled. :3"""

        if not image_url and not image:
            raise utils.DoggieBotException('No image was specified!')

        await interaction.response.defer(thinking=True)

        image_url = image_url or image.proxy_url

        BASE_URL = 'https://saucenao.com/search.php'

        allowed_dbs = [23, 24, 29, 34, 39, 40, 41, 42]

        params = {
            'api_key': self.bot.config['saucenao_api_key'],  # key
            'output_type': 2,
            'numres': 10,
            'hide': 1,
            'dbs[]': allowed_dbs,
            'url': image_url
        }

        async with self.bot.session.get(BASE_URL, params=params) as resp:
            data = await resp.json()
            results = data['results']

        view = SauceMenu(interaction.user, results, 1)

        await interaction.edit_original_response(view=view, **await view.get_page_contents())


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
