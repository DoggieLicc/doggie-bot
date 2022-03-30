import discord
import unicodedata
import utils

from discord import app_commands, User, Member, Interaction

from datetime import datetime, timezone, timedelta
from typing import Optional


__all__ = [
    'multiban',
    'multiunban',
    'multisoftban',
    'multikick',
    'multitimeout',
    'multiuntimeout',
    'purge',
    'multirename',
    'asciify'
]


@app_commands.command()
@app_commands.describe(user1='User to ban (You can also use user ID).')
@app_commands.describe(reason='The reason to ban the users for, this will show up in the audit log.')
async def multiban(
        interaction: Interaction,
        user1: User,
        reason: Optional[str],
        user2: Optional[User],
        user3: Optional[User],
        user4: Optional[User],
        user5: Optional[User],
        user6: Optional[User],
        user7: Optional[User],
        user8: Optional[User],
        user9: Optional[User]
):
    """Bans the specified users"""

    if not utils.perms_check(interaction, 'ban_members'):
        return

    reason = reason or 'No reason specified'

    users = [u for u in [user1, user2, user3, user4, user5, user6, user7, user8, user9] if u]

    lists = await utils.multi_punish(
        interaction.user,
        users,
        interaction.guild.ban,
        reason=f'{str(interaction.user)}: {reason}'
    )

    embed = utils.punish_embed(interaction.user, 'banned', reason, lists)

    await interaction.response.send_message(embed=embed)


@app_commands.command()
@app_commands.describe(user1='User to unban, use User ID.')
@app_commands.describe(reason='The reason to unban the users for, this will show up in the audit log.')
async def multiunban(
        interaction: Interaction,
        user1: User,
        reason: Optional[str],
        user2: Optional[User],
        user3: Optional[User],
        user4: Optional[User],
        user5: Optional[User],
        user6: Optional[User],
        user7: Optional[User],
        user8: Optional[User],
        user9: Optional[User]
):
    """Unbans the specified users"""

    if not utils.perms_check(interaction, 'ban_members'):
        return

    reason = reason or 'No reason specified'

    users = [u for u in [user1, user2, user3, user4, user5, user6, user7, user8, user9] if u]

    lists = await utils.multi_punish(
        interaction.user,
        users,
        interaction.guild.unban,
        reason=f'{str(interaction.user)}: {reason}'
    )

    embed = utils.punish_embed(interaction.user, 'unbanned', reason, lists)

    await interaction.response.send_message(embed=embed)


@app_commands.command()
@app_commands.describe(user1='User to softban (You can also use user ID).')
@app_commands.describe(reason='The reason to softban the users for, this will show up in the audit log.')
async def multisoftban(
        interaction: Interaction,
        user1: User,
        reason: Optional[str],
        user2: Optional[User],
        user3: Optional[User],
        user4: Optional[User],
        user5: Optional[User],
        user6: Optional[User],
        user7: Optional[User],
        user8: Optional[User],
        user9: Optional[User]
):
    """Softbans the specified users (ban then unban)"""

    if not utils.perms_check(interaction, 'ban_members'):
        return

    reason = reason or 'No reason specified'

    users = [u for u in [user1, user2, user3, user4, user5, user6, user7, user8, user9] if u]

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

    await interaction.response.send_message(embed=embed)


@app_commands.command()
@app_commands.describe(member1='Member to kick (You can also use user ID).')
@app_commands.describe(reason='The reason to kick the members for, this will show up in the audit log.')
async def multikick(
        interaction: Interaction,
        member1: Member,
        reason: Optional[str],
        member2: Optional[Member],
        member3: Optional[Member],
        member4: Optional[Member],
        member5: Optional[Member],
        member6: Optional[Member],
        member7: Optional[Member],
        member8: Optional[Member],
        member9: Optional[Member]
):
    """Kicks the specified members"""

    if not utils.perms_check(interaction, 'kick_members'):
        return

    reason = reason or 'No reason specified'

    members = [u for u in [member1, member2, member3, member4, member5, member6, member7, member8, member9] if u]

    lists = await utils.multi_punish(
        interaction.user,
        members,
        interaction.guild.kick,
        reason=f'{str(interaction.user)}: {reason}'
    )

    embed = utils.punish_embed(interaction.user, 'kicked', reason, lists)

    await interaction.response.send_message(embed=embed)


@app_commands.command()
@app_commands.describe(member1='The member to timeout (You can also use user ID).')
@app_commands.describe(hours='The amount of hours to timeout for (float 0-621)')
@app_commands.describe(reason='The reason to timeout the members for. this will show up in the audit log.')
async def multitimeout(
        interaction: Interaction,
        member1: Member,
        hours: app_commands.Range[float, 0, 672 - 1],
        reason: Optional[str],
        member2: Optional[Member],
        member3: Optional[Member],
        member4: Optional[Member],
        member5: Optional[Member],
        member6: Optional[Member],
        member7: Optional[Member],
        member8: Optional[Member],
        member9: Optional[Member]
):
    """Timeouts the specified members for a certain time!"""

    if not utils.perms_check(interaction, 'moderate_members'):
        return

    members = [u for u in [member1, member2, member3, member4, member5, member6, member7, member8, member9] if u]
    reason = reason or 'No reason specified'

    end_time = datetime.now(timezone.utc) + timedelta(hours=hours)

    lists = await utils.multi_punish(
        interaction.user,
        members,
        discord.Member.edit,
        timed_out_until=end_time,
        reason=f'{str(interaction.user)}: {reason}'
    )

    embed = utils.punish_embed(interaction.user, 'timed out', reason, lists)

    await interaction.response.send_message(embed=embed)


@app_commands.command()
@app_commands.describe(member1='The member to remove the timeout from (You can also use user ID).')
@app_commands.describe(reason='The reason to untimeout the members for. this will show up in the audit log.')
async def multiuntimeout(
        interaction: Interaction,
        member1: Member,
        reason: Optional[str],
        member2: Optional[Member],
        member3: Optional[Member],
        member4: Optional[Member],
        member5: Optional[Member],
        member6: Optional[Member],
        member7: Optional[Member],
        member8: Optional[Member],
        member9: Optional[Member]
):
    """Untimeouts the specified members"""

    if not utils.perms_check(interaction, 'moderate_members'):
        return

    members = [u for u in [member1, member2, member3, member4, member5, member6, member7, member8, member9] if u]
    reason = reason or 'No reason specified'

    lists = await utils.multi_punish(
        interaction.user,
        members,
        discord.Member.edit,
        timed_out_until=None,
        reason=f'{str(interaction.user)}: {reason}'
    )

    embed = utils.punish_embed(interaction.user, 'untimedout', reason, lists)

    await interaction.response.send_message(embed=embed)


@app_commands.command()
@app_commands.describe(amount='The amount of messages to search (1-100). Default is 20')
@app_commands.describe(user='The user to only delete messages from (You can also use user ID).')
async def purge(
        interaction: Interaction,
        amount: app_commands.Range[int, 1, 100] = 20,
        user: Optional[User] = None
):
    """Deletes multiple messages in current channel! Specify an user to only delete their messages."""

    if not utils.perms_check(interaction, 'delete_messages'):
        return

    amount = 200 if abs(amount) >= 200 else abs(amount) + 1

    messages_deleted = await interaction.channel.purge(
        limit=amount, check=lambda m: not user or (m.author == user)
    )

    user_m = user.mention if user else 'anyone'
    embed = utils.create_embed(
        interaction.user,
        title=f'{len(messages_deleted)} messages deleted!',
        description=f'Deleted messages from {user_m}'
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command()
@app_commands.describe(member1='Member to rename (You can also use user ID).')
@app_commands.describe(nickname='The name to rename the members\' nickname to (1-32 characters).')
@app_commands.describe(reason='The reason to rename the users for, this will show up in the audit log.')
async def multirename(
        interaction: Interaction,
        member1: Member,
        nickname: str,
        member2: Optional[Member],
        member3: Optional[Member],
        member4: Optional[Member],
        member5: Optional[Member],
        member6: Optional[Member],
        member7: Optional[Member],
        member8: Optional[Member],
        member9: Optional[Member],
        reason: Optional[str] = 'No reason specified'
):
    """Renames members' nicknames to a specified nickname"""

    if not utils.perms_check(interaction, 'manage_nicknames'):
        return

    members = [u for u in [member1, member2, member3, member4, member5, member6, member7, member8, member9] if u]

    if len(nickname) > 32:
        embed = utils.create_embed(
            interaction.user,
            title='Nickname too long!',
            description=f'The nickname {nickname[:100]} is too long! (32 chars max.)',
            color=discord.Color.red()
        )

        return await interaction.response.send_message(embed=embed)

    lists = await utils.multi_punish(
        interaction.user,
        members,
        discord.Member.edit,
        nick=nickname,
        reason=f'interaction.user: {reason}'
    )

    embed = utils.punish_embed(interaction.user, 'renamed', nickname, lists)

    await interaction.response.send_message(embed=embed)


@app_commands.command()
@app_commands.describe(member1='Member whose name to asciify (You can also use user ID).')
async def asciify(
        interaction: Interaction,
        member1: Member,
        member2: Optional[Member],
        member3: Optional[Member],
        member4: Optional[Member],
        member5: Optional[Member],
        member6: Optional[Member],
        member7: Optional[Member],
        member8: Optional[Member],
        member9: Optional[Member],
):
    """Replace weird unicode letters in nicknames with normal ASCII text."""

    if not utils.perms_check(interaction, 'manage_nicknames'):
        return

    members = [u for u in [member1, member2, member3, member4, member5, member6, member7, member8, member9] if u]

    async def _rename(member: discord.Member):
        ascii_text = unicodedata.normalize('NFKD', member.display_name).encode('ascii', 'ignore').decode()
        await member.edit(nick=ascii_text[:31] or 'Unreadable', reason=f'Asciified by {interaction.user}')

    lists = await utils.multi_punish(
        interaction.user,
        members,
        _rename
    )

    embed = utils.punish_embed(interaction.user, 'asciified', 'Asciify strange characters', lists)

    await interaction.response.send_message(embed=embed)
