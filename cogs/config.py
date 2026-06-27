from dataclasses import fields

from discord import TextChannel, Role, app_commands, Embed, ui, Guild, CheckboxGroupOption, Interaction
from discord.ext.commands import GroupCog

import utils
from utils import CustomBot


def maybe_mention(channel):
    return channel.mention if channel else "Not set"

def get_config_embed(bot, interaction: Interaction[CustomBot]) -> Embed:
    basic_config = bot.get_basic_config(interaction.guild)
    logging_config = bot.get_logging_config(interaction.guild)

    embed = utils.create_embed(
        interaction.user,
        title='Showing current server configuration:',
        description=f'**Guild:** {basic_config.guild} ({basic_config.guild.id})\n'
                    f'**Mute role:** {maybe_mention(basic_config.mute_role)}\n'
                    f'**Snipe command:** {"Enabled" if basic_config.snipe else "Disabled"}')

    embed.add_field(
        name='Logging configuration:',
        value=f'**Ban channel:** {maybe_mention(logging_config.ban_channel)}\n'
                f'**Kick channel:** {maybe_mention(logging_config.kick_channel)}\n'
                f'**Deleted messages channel:** {maybe_mention(logging_config.delete_channel)}\n'
                f'**Mute channel:** {maybe_mention(logging_config.mute_channel)}\n'
                f'**Purge channel:** {maybe_mention(logging_config.purge_channel)}'
    )

    return embed

class ConfigClearer(ui.Modal):
    # pylint: disable=arguments-differ
    def __init__(self, interaction: Interaction[CustomBot], *, title: str):
        super().__init__(title=title)
        self.has_items = False
        self.add_checkboxes(interaction)

    def add_checkboxes(self, interaction: Interaction[CustomBot]):
        if not interaction.guild:
            return
        basic_config: utils.BasicConfig = interaction.client.get_basic_config(interaction.guild)
        logging_config: utils.LoggingConfig = interaction.client.get_logging_config(interaction.guild)

        options: list[CheckboxGroupOption] = []

        if basic_config.snipe:
            options.append(
                CheckboxGroupOption(
                    label='Message Snipes',
                    description='Current snipe state: Enabled',
                    value='snipe'
                )
            )
            self.has_items = True

        if basic_config.mute_role:
            options.append(
                CheckboxGroupOption(
                    label='Mute Role',
                    description=f'Current mute role: @{basic_config.mute_role.name}',
                    value='mute_role'
                )
            )
            self.has_items = True

        for k, v in {field.name: getattr(logging_config, field.name) for field in fields(logging_config)}.items():
            if not v or isinstance(v, Guild):
                continue

            k_name = k.replace('_', ' ').title()
            options.append(
                CheckboxGroupOption(
                    label=k_name,
                    description=f'Current {k_name.lower()}: #{v.name}',
                    value=k
                )
            )
            self.has_items = True

        if not self.has_items:
            return

        self.add_item(
            ui.Label(
                text='Select the configurations to clear & reset',
                component=ui.CheckboxGroup(
                    min_values=1,
                    options=options,
                    id=100
                )
            )
        )

    async def on_submit(self, interaction: Interaction[CustomBot]):  # type: ignore
        checkbox_group = self.find_item(100)
        if not isinstance(checkbox_group, ui.CheckboxGroup) or not interaction.guild:
            return
        basic_changes = {}
        logging_changes = {}
        for value in checkbox_group.values:
            if value == 'snipe':
                basic_changes['snipe'] = None
                continue
            if value == 'mute_role':
                basic_changes['mute_role'] = None
                continue
            logging_changes[value] = None

        if basic_changes:
            basic_config = interaction.client.get_basic_config(interaction.guild)
            await basic_config.set_config(interaction.client, **basic_changes)

        if logging_changes:
            logging_config = interaction.client.get_logging_config(interaction.guild)
            await logging_config.set_config(interaction.client, **logging_changes)

        embed = utils.create_embed(
            interaction.user,
            title='Configurations cleared!',
            description=f'{len(checkbox_group.values)} configuration(s) were cleared & reset.'
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.guild_only()
@app_commands.allowed_installs(users=False)
class Configuration(GroupCog, group_name='config'):
    """Commands to view and edit the bot configuration"""

    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    @app_commands.command()
    async def view(self, interaction: Interaction[CustomBot]):
        """Shows the current configuration for this server!"""

        embed = get_config_embed(self.bot, interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @utils.invoker_has_permissions(manage_guild=True)
    @app_commands.command()
    @app_commands.describe(snipe_enabled='Whether to enable the bot to store deleted message for the "/mod snipe" command')
    @app_commands.describe(mute_role='The role that will be given to users when using the "/mod mute" command')
    @app_commands.describe(logging_ban_channel='The channel where messages will be sent in when an user is banned')
    @app_commands.describe(logging_kick_channel='The channel where messages will be sent in when a member is kicked')
    @app_commands.describe(logging_deleted_messages_channel='The channel where deleted messages will be reposted')
    @app_commands.describe(logging_mutes_channel='The channel where messages will be sent in when a member is muted via "/mod mute", or timeout-ed')
    @app_commands.describe(logging_purge_channel='The channel where purges by this or other bots are reported')
    async def edit(
        self,
        interaction: Interaction[CustomBot],
        snipe_enabled: bool | None,
        mute_role: Role | None,
        logging_ban_channel: TextChannel | None,
        logging_kick_channel: TextChannel | None,
        logging_deleted_messages_channel: TextChannel | None,
        logging_mutes_channel: TextChannel | None,
        logging_purge_channel: TextChannel | None,
    ):
        """Edit the server configuration for this bot. You need "Manage Server" permissions!"""
        if not any((
            snipe_enabled is not None,
            mute_role,
            logging_ban_channel,
            logging_kick_channel,
            logging_deleted_messages_channel,
            logging_mutes_channel,
            logging_purge_channel
        )):
            raise utils.DoggieBotException('No options set!', 'You didn\'t specify any options to configure.')

        basic_config = self.bot.get_basic_config(interaction.guild)
        logging_config = self.bot.get_logging_config(interaction.guild)
        basic_changes = {}
        logging_changes = {}

        if snipe_enabled is not None:
            basic_changes['snipe'] = snipe_enabled

        if mute_role:
            basic_changes['mute_role'] = mute_role

        if logging_ban_channel:
            logging_changes['ban_channel'] = logging_ban_channel

        if logging_kick_channel:
            logging_changes['kick_channel'] = logging_kick_channel

        if logging_deleted_messages_channel:
            logging_changes['delete_channel'] = logging_deleted_messages_channel

        if logging_mutes_channel:
            logging_changes['mute_channel'] = logging_mutes_channel

        if logging_purge_channel:
            logging_changes['purge_channel'] = logging_purge_channel

        if basic_changes:
            await basic_config.set_config(self.bot, **basic_changes)

        if logging_changes:
            await logging_config.set_config(self.bot, **logging_changes)

        embed = get_config_embed(self.bot, interaction)
        embed.title = 'New Server Configuration:'

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @utils.invoker_has_permissions(manage_guild=True)
    @app_commands.command()
    async def clear(self, interaction: Interaction[CustomBot]):
        """Open a menu where you can clear specific configurations for this server. You need "Manage Server" permissions!"""
        modal = ConfigClearer(interaction, title='Clear Configurations')

        if not modal.has_items:
            raise utils.DoggieBotException('No configuration!', 'There are no configurations set for this server, so there\'s nothing to clear.')

        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(Configuration(bot))
