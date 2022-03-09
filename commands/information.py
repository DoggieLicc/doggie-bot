import discord
import utils

from discord import app_commands, Interaction, User, Member, Role, Message
from typing import Optional, Union

__all__ = [
    'server',
    'user',
    'invite',
    'channel',
    'avatar',
    'role',
    'user_context_menu',
    'message_context_menu'
]


@app_commands.command()
@app_commands.describe(ephemeral='Make the command only visible to you!')
async def server(interaction: Interaction, ephemeral: Optional[bool]):
    """Shows information for the current guild"""

    if not interaction.guild:
        return

    guild: discord.Guild = interaction.guild

    bot_count = sum(member.bot for member in guild.members)

    embed = utils.create_embed(
        interaction.user,
        title=f'Info for {guild.name}:',
        thumbnail=guild.icon,
        image=guild.banner
    )

    features = []
    if 'COMMUNITY' in guild.features:
        features.append('Community')
    if 'VERIFIED' in guild.features:
        features.append(f'{utils.Emotes.verified} Verified')
    if 'PARTNERED' in guild.features:
        features.append(f'{utils.Emotes.partner} Partnered')
    if 'DISCOVERABLE' in guild.features:
        features.append(f'{utils.Emotes.stage} Discoverable')
    if not features:
        features.append('No special features')

    embed.add_field(
        name='General Info:',
        value=f'Description: {guild.description or "No description"}\n'
              f'Owner: {guild.owner} ({guild.owner_id})\n'
              f'ID: {guild.id}\n'
              f'Creation date: {utils.user_friendly_dt(guild.created_at)}',
        inline=False
    )

    embed.add_field(name='Special features:', value=', '.join(features))

    embed.add_field(
        name=f'{utils.Emotes.booster4} Boost Info:',
        value=f'Boost level: {guild.premium_tier} \n'
              f'Amount of boosters: {guild.premium_subscription_count}\n'
              f'Booster Role: '
              f'{guild.premium_subscriber_role.mention if guild.premium_subscriber_role else "None"}',
        inline=False
    )

    embed.add_field(
        name='Counts:',
        value=f'Members: {guild.member_count} total members\n'
              f'{guild.member_count - bot_count} humans; {bot_count} bots\n'
              f'Roles: {len(guild.roles)} roles\n'
              f'Text channels: {len(guild.text_channels)} channels\n'
              f'Voice Channels: {len(guild.voice_channels)} channels\n'
              f'Emotes: {len(guild.emojis)} emotes',
        inline=False
    )

    embed.add_field(
        name='Security Info:',
        value=f'2FA required?: {"Yes" if guild.mfa_level else "No"}\n'
              f'Verification Level: {str(guild.verification_level).replace("_", " ").title()}\n'
              f'NSFW Filter: {str(guild.explicit_content_filter).replace("_", " ").title()}'
    )

    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


@app_commands.command()
@app_commands.describe(user='The user to get info from. Leave blank to get your info!')
@app_commands.describe(ephemeral='Make the command only visible to you!')
async def user(interaction: discord.Interaction, user: Optional[User], ephemeral: Optional[bool]):
    """Shows information about the user specified"""

    user: Union[discord.Member, discord.User, str] = user or interaction.user

    fetched = user if user.banner else await interaction.client.fetch_user(user.id)

    flags = [name.replace('_', ' ').title() for name, value in dict.fromkeys(iter(user.public_flags)) if value]
    badges = '\n'.join(flags) or 'None'

    embed = utils.create_embed(
        interaction.user,
        title=f'Info for {user} {utils.Emotes.badges(user)}:',
        thumbnail=user.display_avatar,
        image=fetched.banner
    )

    embed.add_field(
        name=f'Is bot? {utils.Emotes.bot_tag}',
        value=f'Yes\n'
              f'[Invite This Bot]({discord.utils.oauth_url(user.id)})' if user.bot else 'No',
        inline=False
    )

    embed.add_field(
        name='General Info:',
        value=f'**User ID:** {user.id}\n'
              f'**Creation Date:** {utils.user_friendly_dt(user.created_at)}\n'
              f'**Badges:** {badges}',
        inline=False
    )

    if isinstance(user, discord.Member) and user.guild == interaction.guild:
        role_mentions = utils.shorten_below_number(
            [role.mention for role in reversed(user.roles)][:-1],
            separator=' ',
            number=500
        )
        top_role = user.top_role.mention if user.top_role != interaction.guild.default_role else 'No roles!'

        embed.add_field(
            name='Member Info:',
            value=f'**Nickname:** {user.nick or "No nickname"}\n'
                  f'**Joined Server At:** {utils.user_friendly_dt(user.joined_at)}\n'
                  f'**Highest Role:** {top_role}\n'
                  f'**Roles:** {role_mentions or "No roles!"}',
            inline=False
        )

        embed.add_field(
            name=f'Permissions: {utils.Emotes.stafftools}',
            value=utils.format_perms(user.guild_permissions),
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


@app_commands.command()
@app_commands.describe(user='The user to get the avatar from. Leave blank to get your own!')
@app_commands.describe(ephemeral='Make the command only visible to you!')
async def avatar(interaction: Interaction, user: Optional[User], ephemeral: Optional[bool]):
    """Shows an user's avatar!"""

    user: discord.User = user or interaction.user

    embed = utils.create_embed(
        interaction.user,
        title=f'Avatar of {user}:',
        image=user.display_avatar
    )

    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


@app_commands.command()
@app_commands.describe(invite='The invite to get info from. Can be a link or just the code part')
@app_commands.describe(ephemeral='Make the command only visible to you!')
async def invite(interaction: Interaction, invite: str, ephemeral: Optional[bool]):
    """Shows info for an invite using a invite URL or its code"""

    try:
        invite = await interaction.client.fetch_invite(invite)
    except discord.DiscordException:
        return

    embed = utils.create_embed(
        interaction.user,
        title=f'Invite Info: {utils.Emotes.invite}',
        thumbnail=invite.guild.icon,
        image=invite.guild.banner
    )

    embed.add_field(
        name='Invite channel:',
        value=f'**Name:** #{invite.channel.name} {utils.Emotes.channel(invite.channel)}\n'
              f'**ID:** {invite.channel.id}\n'
              f'**Created at:** {utils.user_friendly_dt(invite.channel.created_at)}',
        inline=True
    )

    embed.add_field(
        name='Active members: Total members',
        value=f'{invite.approximate_presence_count} active member(s): '
              f'{invite.approximate_member_count} total member(s)',
        inline=False
    )

    embed.add_field(
        name='Invite creator:',
        value=f'{invite.inviter}\n'
              f'ID: {invite.inviter.id}' if invite.inviter else 'Unknown',
        inline=False
    )

    embed.add_field(
        name='Server Info:',
        value=f'**Name:** {invite.guild}\n'
              f'**Description:** {invite.guild.description or "None"}\n'
              f'**ID:** {invite.guild.id}\n'
              f'**Created at:** {utils.user_friendly_dt(invite.guild.created_at)}'
    )

    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


@app_commands.command()
@app_commands.describe(channel='The channel to get info for.')
@app_commands.describe(ephemeral='Make the command only visible to you!')
async def channel(interaction: Interaction, channel: app_commands.AppCommandChannel, ephemeral: Optional[bool]):
    """Shows info for a channel!"""

    channel = await channel.fetch()

    if not interaction.guild or interaction.guild != channel.guild:
        return

    embed = utils.create_embed(
        interaction.user,
        title=f'Info for {channel.name}: {utils.Emotes.channel(channel)}',
        thumbnail=interaction.guild.icon
    )

    if isinstance(channel, discord.TextChannel):
        slowmode = 'Disabled' if not channel.slowmode_delay else f'{channel.slowmode_delay} seconds'
        embed.add_field(name=f'Slowmode: {utils.Emotes.slowmode}', value=slowmode, inline=False)
        embed.add_field(name='NSFW?:', value=('Yes' if channel.is_nsfw() else 'No'), inline=False)
        embed.add_field(name='Topic:', value=(channel.topic or 'No topic set'), inline=False)

    if isinstance(channel, discord.VoiceChannel):
        embed.add_field(
            name='Voice Channel Info:',
            value=f'**Bitrate:** {round(channel.bitrate / 1000)}kbps\n'
                  f'**Region:** {str((channel.rtc_region or "Automatic")).title()}\n'
                  f'**# Connected:** {len(channel.members)} connected '
                  f'{f"/ {channel.user_limit} max" if channel.user_limit else ""}',
            inline=False
        )

    if isinstance(channel, discord.StageChannel):
        embed.add_field(name='Connected:', value=f'{len(channel.members)} connected')
        embed.add_field(name='Region:', value=str((channel.rtc_region or 'Automatic')).title())

    embed.add_field(
        name='General Channel Info:',
        value=f'**Type:** {str(channel.type).replace("_", " ").title()} channel\n'
              f'**Category:** {channel.category}\n'
              f'**ID:** {channel.id}\n'
              f'**Created at:** {utils.user_friendly_dt(channel.created_at)}',
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

@app_commands.command()
@app_commands.describe(role='The role to get info for!')
@app_commands.describe(ephemeral='Make the command only visible to you!')
async def role(interaction: Interaction, role: Role, ephemeral: Optional[bool]):
    """Get info for a role."""

    embed = utils.create_embed(
        interaction.user,
        title=f'Info for {role.name} {utils.Emotes.role}:',
        thumbnail=role.icon
    )

    if role.is_bot_managed():
        bot = interaction.guild.get_member(role.tags.bot_id)
        embed.add_field(name='Bot manager name:', value=str(bot), inline=False)
        embed.add_field(name='Bot manager ID:', value=role.tags.bot_id, inline=False)

    elif role.is_integration():
        embed.add_field(name='Integration ID:', value=role.tags.integration_id, inline=False)

    embed.add_field(
        name='General Info:',
        value=f'**Name:** {role.mention}\n'
              f'**Position:** {role.position}\n'
              f'**ID:** {role.id}\n'
              f'**Color:** {role.color}\n'
              f'**Created at:** {utils.user_friendly_dt(role.created_at)}\n'
              f'**# members with role:** {len(role.members)}\n'
              f'**Mentionable?:** {"Yes" if role.mentionable else "No"}\n'
              f'**Hoisted?:** {"Yes" if role.hoist else "No"}\n',
        inline=False
    )

    embed.add_field(
        name=f'{utils.Emotes.stafftools} Permissions:',
        value=utils.format_perms(role.permissions) or 'None',
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


@app_commands.context_menu(name='Member Info')
async def user_context_menu(interaction: Interaction, member: Member):
    await user.callback(interaction, member, True)


@app_commands.context_menu(name='Message Info')
async def message_context_menu(interaction: Interaction, message: Message):
    embed = utils.create_embed(
        interaction.user,
        title='Info for message:',
        description=f'"{message.content}"' if message.content else '*Message has no content*',
        url=message.jump_url,
    )

    images = [a.url for a in message.attachments if a.content_type.startswith('image')]

    embed.set_author(name=message.author, icon_url=utils.fix_url(message.author.display_avatar))

    attachments = '\n'.join([f'[{a.filename}]({a.url})' for a in message.attachments]) or 'No attachments'

    embed.add_field(name='Attachments:', value=attachments, inline=False)

    if message.reference:
        try:
            replied = await message.channel.fetch_message(message.reference.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            replied = None

        if replied:
            embed.add_field(
                name='Replied Message:',
                value=f'ID: {replied.id}\n'
                      f'Author: {replied.author.mention}\n'
                      f'Content: {replied.content[100] or "*No content*"}\n'
                      f'[Jump to Message]({replied.jump_url})'
            )

    embed.add_field(
        name='Info:',
        value=f'ID: {message.id}\n'
              f'Channel: {message.channel.mention} ({message.channel.id})\n'
              f'Created at: {utils.user_friendly_dt(message.created_at)}\n'
              f'{len(message.mentions)} members mentioned\n'
              f'Stickers: {(", ".join([f"[{s}]({s.url})" for s in message.stickers]) or "No stickers")}\n'
              f'Embeds: {len(message.embeds)} embeds',
        inline=False
    )

    image_embeds = [utils.create_embed(None, url=message.jump_url, image=image) for image in images[:4]]

    await interaction.response.send_message(embeds=[embed] + image_embeds, ephemeral=True)
