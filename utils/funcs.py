import io
from datetime import datetime
from typing import Union, Any, Callable, Tuple, List, Coroutine, Optional
from uuid import UUID

import discord
from PIL import Image
from discord import Embed, User, Member, Permissions

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
    'solid_color_image'
]


def create_embed(user: Optional[Union[Member, User]], *, image=None, thumbnail=None, **kwargs) -> Embed:
    """Makes a discord.Embed with options for image and thumbnail URLs, and adds a footer with author name"""

    kwargs['color'] = kwargs.get('color', discord.Color.green())

    embed = discord.Embed(**kwargs)
    embed.set_image(url=fix_url(image))
    embed.set_thumbnail(url=fix_url(thumbnail))

    if user:
        embed.set_footer(text=f'Command sent by {user}', icon_url=fix_url(user.display_avatar))

    return embed


def guess_user_nitro_status(user: Union[User, Member]) -> bool:
    """Guess if an user or member has Discord Nitro"""

    if isinstance(user, Member):
        has_emote_status = any([a.emoji.is_custom_emoji() for a in user.activities if getattr(a, 'emoji', None)])

        return any([user.display_avatar.is_animated(), has_emote_status, user.premium_since])

    return any([user.display_avatar.is_animated(), user.banner])


def user_friendly_dt(dt: datetime):
    """Format a datetime as "short_date (relative_date)" """
    return discord.utils.format_dt(dt, style='f') + f' ({discord.utils.format_dt(dt, style="R")})'


def format_perms(permissions: Permissions) -> str:
    perms_list = [p.title().replace('_', ' ') for p, v in iter(permissions) if v]
    return '\n'.join(perms_list)


def hierarchy_check(mod: Member, user: Union[Member, User]) -> bool:
    """Check if a moderator and the bot can punish an user/member"""

    if isinstance(user, User): return True

    return mod.top_role > user.top_role and mod.guild.me.top_role > user.top_role and not user == mod.guild.owner


def shorten_below_number(_list: List[Any], *, separator: str = '\n', number: int = 1000):
    shortened = ''

    while _list and len(shortened) + len(str(_list[0])) <= number:
        shortened += str(_list.pop(0)) + separator

    return shortened[:-len(separator)]


USER_LIST = List[Union[Member, User]]


async def multi_punish(
        mod: Member,
        users: USER_LIST,
        func: Callable[[Union[Member, User], Any], Coroutine[Any, Any, Any]],
        **kwargs
) -> Tuple[USER_LIST, USER_LIST]:
    punished = []
    not_punished = [user for user in users if not hierarchy_check(mod, user)]

    users = [user for user in users if user not in not_punished]
    for user in users:
        try:
            await func(user, **kwargs)
            punished.append(user)
        except (discord.Forbidden, discord.HTTPException):
            not_punished.append(user)

    return punished, not_punished


def punish_embed(mod: Member, punishment: str, reason: str, punish_lists: Tuple[USER_LIST, USER_LIST]) -> Embed:
    punished, not_punished = punish_lists
    punished, not_punished = punished.copy(), not_punished.copy()

    if not punished:
        return create_embed(mod,
                            title=f'Users couldn\'t be {punishment}!',
                            description=f'The bot wasn\'t able to {punishment} any users! '
                                        'Maybe their role is higher than yours. or higher than this bot\'s roles.',
                            color=discord.Color.red())

    if not_punished:
        embed = create_embed(mod,
                             title=f'Some users couldn\'t be {punishment}!',
                             description=f'{len(punished)} users were {punishment} for "{reason[:1000]}"\n'
                                         f'{len(not_punished)} users couldn\'t be punished, '
                                         f'maybe their role is higher than yours. or higher than this bot\'s roles.',
                             color=discord.Color.orange())

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


def str_to_file(string: str, *, filename: str = 'file.txt', encoding: str = 'utf-8') -> discord.File:
    """Converts a given str to a discord.File ready for sending"""

    _bytes = bytes(string, encoding)
    buffer = io.BytesIO(_bytes)
    file = discord.File(buffer, filename=filename)
    return file


def format_deleted_msg(message: discord.Message, title: Optional[str] = None) -> discord.Embed:
    emote = '<:messagedelete:941816371401064490>'
    reply = message.reference

    if reply: reply = reply.resolved
    reply_deleted = isinstance(reply, discord.DeletedReferencedMessage)

    embed = discord.Embed(
        title=f'{emote} {title}' if title else f'{emote} Message deleted in #{message.channel}',
        description=f'"{message.content}"' if message.content else '*No content*',
        color=discord.Color.red()
    )

    embed.set_author(name=f'{message.author}: {message.author.id}', icon_url=fix_url(message.author.display_avatar))

    if message.attachments:
        if message.attachments[0].filename.endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')):
            embed.set_image(url=fix_url(message.attachments[0].proxy_url))

        file_urls = [f'[{file.filename}]({file.proxy_url})' for file in message.attachments]
        embed.add_field(name='Deleted files:', value=f'\n'.join(file_urls))

    embed.add_field(
        name=f'Message created at:',
        value=user_friendly_dt(message.created_at),
        inline=False
    )

    if reply:
        if reply_deleted:
            msg = 'Replied message has been deleted.'
        else:
            msg = f'Replied to {reply.author} - [Link to replied message]({reply.jump_url} "Jump to Message")'

        embed.add_field(name='Message reply:', value=msg)

    embed.add_field(name='Message channel:', value=message.channel.mention, inline=False)

    return embed


def fix_url(url: Any):
    if not url:
        return None

    return str(url)


def solid_color_image(color: tuple):
    buffer = io.BytesIO()
    image = Image.new('RGB', (80, 80), color)
    image.save(buffer, 'png')
    buffer.seek(0)

    return buffer
