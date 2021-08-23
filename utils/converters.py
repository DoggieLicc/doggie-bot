import re

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

import discord
from discord.ext import commands
from discord import Member, User, TextChannel

__all__ = [
    'IntentionalMember',
    'IntentionalUser',
    'TimeConverter',
    'MentionedTextChannel',
    'EmbedConverter',
    'NitrolessEmoteConverter'
]


class IntentionalMember(commands.converter.MemberConverter):
    async def convert(self, ctx, argument: str) -> Member:
        if not argument.isnumeric() and not (len(argument) > 5 and argument[-5] == '#') and not \
                self._get_id_match(argument) and not re.match(r'<@!?([0-9]{15,20})>$', argument):
            # Not a mention or an ID a name#tag
            raise commands.errors.MemberNotFound(argument)

        return await super().convert(ctx, argument)


class IntentionalUser(commands.converter.UserConverter):
    async def convert(self, ctx, argument: str) -> User:
        if not argument.isnumeric() and not (len(argument) > 5 and argument[-5] == '#') and not \
                self._get_id_match(argument) and not re.match(r'<@!?([0-9]{15,20})>$', argument):
            # Not a mention or an ID or a name#tag
            raise commands.errors.UserNotFound(argument)

        return await super().convert(ctx, argument)


@dataclass(frozen=True)
class TimeUnit:
    name: str
    seconds: int


@dataclass(frozen=True)
class Time:
    unit_amount: int
    unit_name: str
    unit: TimeUnit
    seconds: int

    def __str__(self):
        return f'{self.unit_amount} {self.unit_name}'


class TimeConverter(commands.Converter):
    @staticmethod
    def get_unit(text: str):
        text = text.lower()

        if text in ['s', 'sec', 'secs', 'second', 'seconds']:
            return TimeUnit('second', 1)
        if text in ['m', 'min', 'mins', 'minute', 'minutes']:
            return TimeUnit('minute', 60)
        if text in ['h', 'hr', 'hrs', 'hour', 'hours']:
            return TimeUnit('hour', 3600)
        if text in ['d', 'day', 'days']:
            return TimeUnit('day', 86_400)
        if text in ['w', 'wk', 'wks', 'week', 'weeks']:
            return TimeUnit('week', 604_800)
        if text in ['mo', 'mos', 'month', 'months']:
            return TimeUnit('month', 2_592_000)
        if text in ['y', 'yr', 'yrs', 'year', 'years']:
            return TimeUnit('year', 31_536_000)
        return None

    async def convert(self, _, argument: str):

        argument = argument.replace(',', '')

        if argument.lower() in ['in', 'me']: return None

        try:
            amount, unit = [re.findall(r'(\d+)(\w+)', argument)[0]][0]

            if amount == 0:
                raise commands.BadArgument('Amount can\'t be zero')

            unit = self.get_unit(unit)
            unit_correct_name = unit.name if amount == '1' else unit.name + 's'
            seconds = unit.seconds * int(amount)
        except Exception:
            raise commands.BadArgument()

        return Time(amount, unit_correct_name, unit, seconds)


ID_REGEX = re.compile(r'([0-9]{15,20})$')


class MentionedTextChannel(commands.Converter):
    async def convert(self, ctx, argument) -> TextChannel:
        match = ID_REGEX.match(argument) or re.match(r'<#([0-9]{15,20})>$', argument)

        if match is None or not ctx.guild:
            raise commands.ChannelNotFound(argument)

        channel_id = int(match.group(1))
        result = ctx.guild.get_channel(channel_id)

        if not isinstance(result, TextChannel):
            raise commands.ChannelNotFound(argument)

        return result


class ImageURLConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        return {'url': argument.strip('<>\n ')}


class URLConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        return argument.strip('<>\n ')


class ColorIntConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        argument = argument.strip('\n ')

        if argument.isnumeric(): return int(argument)
        color = await commands.ColorConverter().convert(ctx, argument)
        return color.value


class EmbedTimestampConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        argument = argument.strip('\n ')
        if argument.isnumeric(): return datetime.fromtimestamp(int(argument)).isoformat()
        return argument


class EmbedFieldConverter(commands.FlagConverter, delimiter=':', prefix='='):
    name: str
    value: str
    inline: Optional[bool] = True

    async def convert(self, *args, **kwargs):
        flag_map = await super().convert(*args, **kwargs)
        return dict(flag_map)


class EmbedAuthorConverter(commands.FlagConverter, delimiter=':', prefix='='):
    name: Optional[str]
    url: Optional[URLConverter]
    icon_url: Optional[URLConverter]

    async def convert(self, *args, **kwargs):
        flag_map = await super().convert(*args, **kwargs)
        return dict(flag_map)


class EmbedFooterConverter(commands.FlagConverter, delimiter=':', prefix='='):
    text: Optional[str]
    icon_url: Optional[URLConverter]

    async def convert(self, *args, **kwargs):
        flag_map = await super().convert(*args, **kwargs)
        return dict(flag_map)


class EmbedConverter(commands.FlagConverter, delimiter=':', prefix='-'):
    color: ColorIntConverter = commands.flag(name='color', aliases=['colour'], default=lambda ctx: 0)
    description: str = ''
    title: str = ''
    url: URLConverter = ''
    thumbnail: Optional[ImageURLConverter]
    image: Optional[ImageURLConverter]
    author: Optional[EmbedAuthorConverter]
    footer: Optional[EmbedFooterConverter]
    timestamp: Optional[EmbedTimestampConverter]
    fields: List[EmbedFieldConverter] = commands.flag(
        name='fields',
        aliases=['field'],
        default=lambda ctx: [],
        max_args=10
    )

    async def convert(self, *args, **kwargs):
        flag_map = await super().convert(*args, **kwargs)
        return discord.Embed.from_dict(dict(flag_map))


class NitrolessEmoteConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        argument = argument.strip('<>`\n ').replace(';', ':')

        try:
            return await commands.EmojiConverter().convert(ctx, f'<{argument}>')
        except (commands.CommandError, commands.BadArgument):
            pass

        return await commands.PartialEmojiConverter().convert(ctx, f'<{argument}>')
