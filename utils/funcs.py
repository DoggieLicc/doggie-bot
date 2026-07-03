import io
from datetime import datetime
from typing import Any, Unpack
from uuid import UUID
from collections.abc import Callable, Awaitable

import discord
from PIL import Image
from discord import Embed, User, Member, Permissions, app_commands, Interaction, Color, File, Forbidden, HTTPException, Message, DeletedReferencedMessage, DMChannel
from discord.ext import commands
from discord.ext.commands import Context

__all__ = [
    'create_embed',
    'guess_user_nitro_status',
    'user_friendly_dt',
    'format_perms',
    'hierarchy_check',
    'shorten_below_number',
    'multi_punish',
    'punish_embed',
    'is_uuid4',
    'format_deleted_msg',
    'str_to_file',
    'fix_url',
    'solid_color_image',
    'invoker_has_permissions',
    'not_user_integration'
]


def create_embed(user: Member | User | None, *, image=None, thumbnail=None, **kwargs) -> Embed:
    """Makes a discord.Embed with options for image and thumbnail URLs, and adds a footer with author name"""

    kwargs['color'] = kwargs.get('color', Color.green())

    embed = Embed(**kwargs)
    embed.set_image(url=fix_url(image))
    embed.set_thumbnail(url=fix_url(thumbnail))

    if user:
        embed.set_footer(text=f'Command sent by {user}', icon_url=fix_url(user.display_avatar))

    return embed


def guess_user_nitro_status(user: Member | User) -> bool:
    """Guess if an user or member has Discord Nitro"""

    if isinstance(user, Member):
        has_emote_status = any(a.emoji.is_custom_emoji() for a in user.activities if getattr(a, 'emoji', None) and a.emoji)  # pyright: ignore[reportAttributeAccessIssue]

        return any([user.display_avatar.is_animated(), has_emote_status, user.premium_since])

    return any([user.display_avatar.is_animated(), user.banner])


def user_friendly_dt(dt: datetime | None) -> str:
    """Format a datetime as "short_date (relative_date)" """
    if not dt:
        return 'Unknown Date'
    return discord.utils.format_dt(dt, style='f') + f' ({discord.utils.format_dt(dt, style="R")})'


def format_perms(permissions: Permissions) -> str:
    perms_list = [p.title().replace('_', ' ') for p, v in iter(permissions) if v]
    return '\n'.join(perms_list)


def hierarchy_check(mod: Member | User, user: Member | User) -> bool:
    """Check if a moderator and the bot can punish an user/member"""

    if isinstance(mod, User):
        return False

    if isinstance(user, User):
        return True

    if mod == user:
        return False

    if mod.guild.owner == mod:
        return True

    return mod.top_role > user.top_role and mod.guild.me.top_role > user.top_role and not user == mod.guild.owner


def shorten_below_number(_list: list[Any], *, separator: str = '\n', number: int = 1000) -> str:
    shortened = ''

    while _list and len(shortened) + len(str(_list[0])) <= number:
        shortened += str(_list.pop(0)) + separator

    return shortened[:-len(separator)]

async def multi_punish[T: (Member, User)](
        mod: Member | User,
        users: list[T],
        func: Callable[[Member | User], Awaitable[None]],
        **kwargs
) -> tuple[list[T], list[T]]:
    punished = []
    not_punished = [user for user in users if not hierarchy_check(mod, user)]

    users = [user for user in users if user not in not_punished]
    for user in users:
        try:
            await func(user, **kwargs)
            punished.append(user)
        except (Forbidden, HTTPException):
            not_punished.append(user)

    return punished, not_punished


def punish_embed(
    mod: Member,
    punishment: str,
    reason: str,
    punish_lists: tuple[list[Member | User], list[Member | User]]
) -> Embed:
    punished, not_punished = punish_lists
    punished, not_punished = punished.copy(), not_punished.copy()

    if not punished:
        return create_embed(mod,
                            title=f'Users couldn\'t be {punishment}!',
                            description=f'The bot wasn\'t able to {punishment} any users! '
                                        'Maybe their role is higher than yours. or higher than this bot\'s roles.',
                            color=Color.red())

    if not_punished:
        embed = create_embed(mod,
                             title=f'Some users couldn\'t be {punishment}!',
                             description=f'{len(punished)} users were {punishment} for "{reason[:1000]}"\n'
                                         f'{len(not_punished)} users couldn\'t be punished, '
                                         f'maybe their role is higher than yours. or higher than this bot\'s roles.',
                             color=Color.orange())

        embed.add_field(name=f'Users not {punishment}:',
                        value=shorten_below_number(not_punished))

    else:
        embed = create_embed(mod,
                             title=f'Users successfully {punishment}!',
                             description=f'{len(punished)} users were {punishment} for "{reason[:1000]}"')

    embed.add_field(name=f'Users {punishment}:',
                    value=shorten_below_number(punished))

    return embed


def is_uuid4(string: str) -> bool:
    try:
        uuid = UUID(string, version=4)
    except ValueError:
        return False
    return uuid.hex == string


def str_to_file(string: str, *, filename: str = 'file.txt', encoding: str = 'utf-8') -> File:
    """Converts a given str to a discord.File ready for sending"""

    _bytes = bytes(string, encoding)
    buffer = io.BytesIO(_bytes)
    file = File(buffer, filename=filename)
    return file


def format_deleted_msg(message: Message, title: str | None = None) -> Embed:
    emote = '<:messagedelete:941816371401064490>'
    reply = message.reference

    if reply:
        reply = reply.resolved

    reply_deleted = isinstance(reply, DeletedReferencedMessage)

    embed = Embed(
        title=f'{emote} {title}' if title else f'{emote} Message deleted in #{message.channel}',
        description=f'"{message.content}"' if message.content else '*No content*',
        color=Color.red()
    )

    embed.set_author(name=f'{message.author}: {message.author.id}', icon_url=fix_url(message.author.display_avatar))

    if message.attachments:
        if message.attachments[0].filename.endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')):
            embed.set_image(url=fix_url(message.attachments[0].proxy_url))

        file_urls = [f'[{file.filename}]({file.proxy_url})' for file in message.attachments]
        embed.add_field(name='Deleted files:', value='\n'.join(file_urls))

    embed.add_field(
        name='Message created at:',
        value=user_friendly_dt(message.created_at),
        inline=False
    )

    if reply:
        if reply_deleted:
            msg = 'Replied message has been deleted.'
        else:
            msg = f'Replied to {reply.author} - [Link to replied message]({reply.jump_url} "Jump to Message")'

        embed.add_field(name='Message reply:', value=msg)

    if message.channel:
        embed.add_field(name='Message channel:', value=f'<#{message.channel.id}>', inline=False)

    return embed


def fix_url(url: Any) -> str | None:
    if not url:
        return None

    return str(url)


def solid_color_image(color: tuple[float, ...]):
    buffer = io.BytesIO()
    image = Image.new('RGB', (80, 80), color)
    image.save(buffer, 'png')
    buffer.seek(0)

    return buffer

def client_has_permissions(**perms: Unpack[discord.permissions._PermissionsKwargs]):
    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f'Invalid permission(s): {", ".join(invalid)}')

    def predicate(interaction: Interaction) -> bool:
        permissions = interaction.app_permissions

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        return False

    return app_commands.check(predicate)

def invoker_has_permissions(**perms: Unpack[discord.permissions._PermissionsKwargs]):
    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f'Invalid permission(s): {", ".join(invalid)}')

    def predicate(interaction: Interaction) -> bool:
        if isinstance(interaction.user, User):
            return False

        permissions = interaction.user.guild_permissions

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        return False

    return app_commands.check(predicate)

def not_user_integration():
    def predicate(ctx: Context) -> bool:
        if not ctx.interaction:
            return True

        if (not ctx.guild or not ctx.guild.owner_id) and ctx.channel.type != DMChannel:
            return False

        return True

    return commands.check(predicate)
