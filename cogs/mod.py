import unicodedata
from datetime import datetime
from functools import partial

from discord import app_commands, Member, User, Interaction, Color, Role, Embed, TextChannel, ChannelType
from discord.ext.commands import GroupCog
from discord.app_commands import Transform, Range

import utils


def maybe_first_snipe_msg(interaction: Interaction):
    embed = utils.create_embed(
        interaction.user,
        title='⚠ Warning!',
        description='That channel seems to be locked, and this channel '
                    'isn\'t. You should move to a private channel to avoid leaking sensitive '
                    'information. However, you have permissions to snipe from that channel, '
                    'so you may proceed with caution.',
        color=Color.orange()
    )

    return embed


async def add_mute(member: Member, role: Role, **kwargs):
    await member.add_roles(role, **kwargs)


async def remove_mute(member: Member, role: Role, **kwargs):
    await member.remove_roles(role, **kwargs)


class SnipeMenu(utils.EntryMenu):
    async def get_page_contents(self):
        message = self.get_page_items()[0]
        if isinstance(message, Embed):
            return message

        embed = utils.format_deleted_msg(message, title=f'Sniped message {self.current_index}/{self.max_page}:')

        embed.set_footer(
            text=f'Command sent by {self.owner}',
            icon_url=utils.fix_url(self.owner.display_avatar)
        )

        return {"embed": embed}

@app_commands.guild_only()
@app_commands.allowed_installs(users=False)
class Moderation(GroupCog, group_name='mod'):
    """Commands to make moderation easier and simpler"""

    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @utils.invoker_has_permissions(ban_members=True)
    @utils.client_has_permissions(ban_members=True)
    @app_commands.command()
    @app_commands.describe(users='Mentions or IDs of one or multiple users, space seperated')
    @app_commands.describe(reason='The reason for the ban. Shown in the audit log')
    async def ban(
        self,
        interaction: Interaction,
        users: Transform[list[Member | User], utils.GreedyMemberUserTransformer],
        reason: str | None = "No reason specified"
    ):
        """Ban members who broke the rules! You can specify multiple members in one command."""

        await interaction.response.defer(thinking=True)

        lists = await utils.multi_punish(
            interaction.user,
            users,
            interaction.guild.ban,
            reason=f'{str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'banned', reason, lists)

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(ban_members=True)
    @utils.client_has_permissions(ban_members=True)
    @app_commands.command()
    @app_commands.describe(users='Mentions or IDs of one or multiple users, space seperated')
    @app_commands.describe(reason='The reason for the unban. Shown in the audit log')
    async def unban(
        self,
        interaction: Interaction,
        users: Transform[list[Member | User], utils.GreedyMemberUserTransformer],
        reason: str | None = "No reason specified"
    ):
        """Unban banned users with their User ID, you can specify multiple people to be unbanned"""

        await interaction.response.defer(thinking=True)

        lists = await utils.multi_punish(
            interaction.user,
            users,
            interaction.guild.unban,
            reason=f'{str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'unbanned', reason, lists)

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(ban_members=True)
    @utils.client_has_permissions(ban_members=True)
    @app_commands.command()
    @app_commands.describe(users='Mentions or IDs of one or multiple users, space seperated')
    @app_commands.describe(reason='The reason for the softban. Shown in the audit log')
    async def softban(
        self,
        interaction: Interaction,
        users: Transform[list[Member | User], utils.GreedyMemberUserTransformer],
        reason: str | None = "No reason specified"
    ):
        """Bans then unbans the specified users, which deletes their recent messages and 'kicks' them"""

        await interaction.response.defer(thinking=True)

        banned, not_banned = await utils.multi_punish(
            interaction.user,
            users,
            interaction.guild.ban,
            reason=f'(Softban) {str(interaction.user)}: {reason}'
        )

        unbanned, _ = await utils.multi_punish(
            interaction.user,
            banned,
            interaction.guild.unban,
            reason=f'(Softban) {str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'softbanned', reason, (unbanned, not_banned))

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(kick_members=True)
    @utils.client_has_permissions(kick_members=True)
    @app_commands.command()
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the kick. Shown in the audit log')
    async def kick(
        self,
        interaction: Interaction,
        members: Transform[list[Member], utils.GreedyMemberTransformer],
        reason: str | None = "No reason specified"
    ):
        """Kick members who broke the rules! You can specify multiple members in one command"""

        await interaction.response.defer(thinking=True)

        lists = await utils.multi_punish(
            interaction.user,
            members,
            interaction.guild.kick,
            reason=f'{str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'kicked', reason, lists)

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(moderate_members=True)
    @utils.client_has_permissions(moderate_members=True)
    @app_commands.command()
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(duration='How long to timeout the member for. Can be a Discord-style timestamp, or durations (5h 30min)')
    @app_commands.describe(reason='The reason for the timeout. Shown in the audit log')
    async def timeout(
        self,
        interaction: Interaction,
        members: Transform[list[Member], utils.GreedyMemberTransformer],
        duration: Transform[datetime, utils.TimeTransformer],
        reason: str | None = 'No reason specified'
    ):
        """Puts specified members in timeout! You can specify multiple members in one command"""

        await interaction.response.defer(thinking=True)

        lists = await utils.multi_punish(
            interaction.user,
            members,
            Member.edit,
            timed_out_until=duration,
            reason=f'{str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'timed out', reason, lists)

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(moderate_members=True)
    @utils.client_has_permissions(moderate_members=True)
    @app_commands.command()
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the untimeout. Shown in the audit log')
    async def untimeout(
        self,
        interaction: Interaction,
        members: Transform[list[Member], utils.GreedyMemberTransformer],
        reason: str | None = "No reason specified"
    ):
        """Removes timeout from members!"""

        remove_timeout = partial(Member.edit, timed_out_until=None)

        lists = await utils.multi_punish(
            interaction.user,
            members,
            remove_timeout,
            reason=f'{str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'untimedout', reason, lists)

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(manage_nicknames=True)
    @utils.client_has_permissions(manage_nicknames=True)
    @app_commands.command()
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(nickname='The new nickname to set for the members')
    async def rename(
        self,
        interaction: Interaction,
        members: Transform[list[Member], utils.GreedyMemberTransformer],
        nickname: str
    ):
        """Renames members to a specified name"""

        if len(nickname) > 32:
            raise utils.DoggieBotException('Nickname too long!', f'The nickname {nickname[:100]} is too long! (32 chars max.)')

        await interaction.response.defer(thinking=True)

        lists = await utils.multi_punish(
            interaction.user,
            members,
            Member.edit,
            nick=nickname,
            reason=f'Renamed by {interaction.user}'
        )

        embed = utils.punish_embed(interaction.user, 'renamed', nickname, lists)

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(manage_roles=True)
    @utils.client_has_permissions(manage_roles=True)
    @app_commands.command()
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the mute. Shown in the audit log')
    async def mute(
        self,
        interaction: Interaction,
        members: Transform[list[Member], utils.GreedyMemberTransformer],
        reason: str | None = "No reason specified"
    ):
        """Gives the configured mute role to members!"""

        mute_role = interaction.client.get_basic_config(interaction.guild).mute_role

        if not mute_role:
            raise utils.DoggieBotException('Mute role not configured!', 'A server admin must use `/config edit` and set a mute role for this server')

        await interaction.response.defer(thinking=True)

        lists: tuple = await utils.multi_punish(
            interaction.user,
            members,
            add_mute,
            role=mute_role,
            reason=f'{str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'muted', reason, lists)

        await interaction.edit_original_response(embed=embed)

        self.bot.dispatch('mute', interaction, lists[0], reason)

    @utils.invoker_has_permissions(manage_roles=True)
    @utils.client_has_permissions(manage_roles=True)
    @app_commands.command()
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the unmute. Shown in the audit log')
    async def unmute(
        self,
        interaction: Interaction,
        members: Transform[list[Member], utils.GreedyMemberTransformer],
        reason: str | None = "No reason specified"
    ):
        """Removes the configured mute role from members!"""

        mute_role = interaction.client.get_basic_config(interaction.guild).mute_role

        if not mute_role:
            raise utils.DoggieBotException('Mute role not configured!', 'A server admin must use `/config edit` and set a mute role for this server')

        await interaction.response.defer(thinking=True)

        lists = await utils.multi_punish(
            interaction.user,
            members,
            remove_mute,
            role=mute_role,
            reason=f'{str(interaction.user)}: {reason}'
        )

        embed = utils.punish_embed(interaction.user, 'unmuted', reason, lists)

        self.bot.dispatch('unmute', interaction, lists[0], reason)

        await interaction.edit_original_response(embed=embed)

    @utils.invoker_has_permissions(manage_messages=True)
    @utils.client_has_permissions(manage_messages=True)
    @app_commands.command()
    @app_commands.describe(users='Mentions or IDs of one or multiple users to delete messages from, space seperated')
    @app_commands.describe(amount='The amount of messages to check. Max of 200')
    async def purge(
        self,
        interaction: Interaction,
        users: Transform[list[Member | User], utils.GreedyMemberUserTransformer] | None = None,
        amount: Range[int, 1, 200] | None = 200
    ):
        """Deletes multiple messages from the current channel, you can specify users that it will delete messages from. You can also specify the amount of messages to check."""

        amount = 200 if abs(amount) >= 200 else abs(amount) + 1

        await interaction.response.defer(thinking=True, ephemeral=True)

        messages_deleted = await interaction.channel.purge(limit=amount, check=lambda m: not users or (m.author in users), bulk=True)

        users = [user.mention for user in users] if users else ['anyone']
        embed = utils.create_embed(
            interaction.user,
            title=f'{len(messages_deleted)} messages deleted!',
            description='Deleted messages from ' + ', '.join(users)
        )

        await interaction.edit_original_response(embed=embed)

        self.bot.dispatch('purge', interaction, users, len(messages_deleted))

    @utils.invoker_has_permissions(manage_nicknames=True)
    @utils.client_has_permissions(manage_nicknames=True)
    @app_commands.command()
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    async def asciify(
        self,
        interaction: Interaction,
        members: Transform[list[Member], utils.GreedyMemberTransformer],
    ):
        """Replace weird unicode letters in nicknames with normal ASCII text!"""

        async def rename(member: Member):
            ascii_text = unicodedata.normalize('NFKD', member.display_name).encode('ascii', 'ignore').decode()
            await member.edit(nick=ascii_text[:31] or 'Unreadable', reason=f'Asciified by {interaction.user}')

        await interaction.response.defer(thinking=True)

        lists = await utils.multi_punish(
            interaction.user,
            members,
            rename
        )

        embed = utils.punish_embed(interaction.user, 'asciified', 'Asciify strange characters', lists)

        await interaction.edit_original_response(embed=embed)

    @app_commands.command()
    @app_commands.describe(channel='Specify a channel to get deleted messages from it. You can only snipe messages from channels in which you have `Manage Messages` and `View Channel` in.')
    @app_commands.describe(user='Specify an user to only get deleted messages from that user')
    async def snipe(
        self,
        interaction: Interaction,
        channel: TextChannel | None,
        user: User | None
    ):
        """Shows recent deleted messages! An administrator must opt-in to message sniping for the bot to store messages."""

        if not interaction.client.get_basic_config(interaction.guild).snipe:
            raise utils.DoggieBotException('Snipe not enabled!', 'A server admin must use `/config edit` and enable message snipes for this server')

        channel = channel or interaction.channel

        if not (channel.permissions_for(interaction.user).manage_messages and channel.permissions_for(interaction.user).view_channel):
            raise utils.DoggieBotException('Can\'t snipe from that channel!', 'You need permissions to view and manage messages of that channel before you can snipe messages from it!')

        await interaction.response.defer(thinking=True)

        filtered = [message for message in self.bot.sniped if (message.guild == interaction.guild)
                    and (user is None or user == message.author) and (channel == message.channel)][:100]

        if not filtered:
            raise utils.DoggieBotException('No messages found!', 'There is no recently deleted messages in this channel that fit the criteria')

        view = SnipeMenu(interaction.user, filtered, 1)
        first_msg = (await view.get_page_contents())['embed']
        if channel.type is ChannelType.text:
            if (
                not channel.overwrites_for(interaction.guild.default_role).view_channel and
                interaction.channel.overwrites_for(interaction.guild.default_role).view_channel
            ):
                first_msg = maybe_first_snipe_msg(interaction)

        await interaction.edit_original_response(view=view, embed=first_msg)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
