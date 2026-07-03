import re

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord import Color, Member, User
from discord.ext import commands
from discord.ext.commands import BadArgument, BadTimestampArgument, Context, RoleNotFound, Timestamp, MemberNotFound
from discord.ext.commands import MemberConverter, RoleConverter, Converter

from utils.classes import CustomContext

__all__ = [
    'PartialEmoteConverter',
    'MultiplePartialEmoteConverter',
    'ColorConverter',
    'TimeConverter',
    'IntentionalMember',
    'IntentionalUser'
]

if TYPE_CHECKING:
    TimeConverter = datetime
    ColorConverter = Color
    MultiplePartialEmoteConverter = list[discord.PartialEmoji]
    PartialEmoteConverter = discord.PartialEmoji
    IntentionalMember = Member
    IntentionalUser = User
else:
    class TimeConverter(Converter):
        # pylint: disable=abstract-method
        @staticmethod
        def get_seconds(text: str) -> int:
            text = text.lower()

            if text in ['s', 'sec', 'secs', 'second', 'seconds']:
                return 1
            if text in ['m', 'min', 'mins', 'minute', 'minutes']:
                return 60
            if text in ['h', 'hr', 'hrs', 'hour', 'hours']:
                return 3_600
            if text in ['d', 'day', 'days']:
                return 86_400
            if text in ['w', 'wk', 'wks', 'week', 'weeks']:
                return 604_800
            if text in ['mo', 'mos', 'month', 'months']:
                return 2_592_000
            if text in ['y', 'yr', 'yrs', 'year', 'years']:
                return 31_536_000
            return 0

        async def convert(self, ctx: Context, value: str, /) -> datetime:
            try:
                # pylint: disable=no-value-for-parameter
                return await Timestamp().convert(ctx, value)  # type: ignore
            except BadTimestampArgument:
                pass

            seconds = 0
            values = value.split()
            for argument in values:
                argument = argument.replace(',', '')
                amount, unit = [re.findall(r'(\d+)(\w+)', argument)[0]][0]

                if int(amount) <= 0:
                    raise BadArgument(f'Argument {argument} has a duration of 0 or less!')

                seconds += self.get_seconds(unit) * int(amount)

            if seconds <= 0:
                raise BadArgument(f'Duration for {value} is 0 or less!')

            return datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)

    class ColorConverter(Converter):
        # pylint: disable=abstract-method
        async def convert(self, ctx: CustomContext, value: str, /) -> list[discord.Color]:
            if ctx.guild:
                try:
                    member = await MemberConverter().convert(ctx, value)
                    return [member.color]
                except MemberNotFound:
                    pass

                try:
                    role = await RoleConverter().convert(ctx, value)
                    return [c for c in [role.color, role.secondary_color, role.tertiary_color] if c is not None]
                except RoleNotFound:
                    pass

            return [await commands.ColorConverter().convert(ctx, value)]

    class MultiplePartialEmoteConverter(Converter):
        # pylint: disable=abstract-method
        async def convert(self, ctx: CustomContext, value: str, /) -> list[discord.PartialEmoji]:
            emotes = []

            value = value.strip('`\n \\').replace(';', ':').replace(',', ' ')

            for val in value.split():
                try:
                    emote = discord.PartialEmoji.from_str(val, client=ctx.bot)
                    if emote not in emotes:
                        emotes.append(emote)
                except OSError:
                    pass

            return emotes

    class PartialEmoteConverter(Converter):
        # pylint: disable=abstract-method
        async def convert(self, ctx: CustomContext, value: str, /) -> discord.PartialEmoji:
            value = value.strip('`\n \\').replace(';', ':')

            return discord.PartialEmoji.from_str(value, client=ctx.bot)

    class IntentionalMember(commands.converter.MemberConverter):
        async def convert(self, ctx, argument: str) -> Member:
            if not (len(argument) > 5 and argument[-5] == '#') and not \
                argument.startswith('@') and not \
                self._get_id_match(argument) and not \
                re.match(r'<@!?([0-9]{15,20})>$', argument):
                # Not a mention or an ID a name#tag or @username
                raise commands.errors.MemberNotFound(argument)

            return await super().convert(ctx, argument.strip('@'))


    class IntentionalUser(commands.converter.UserConverter):
        async def convert(self, ctx, argument: str) -> User:
            if not (len(argument) > 5 and argument[-5] == '#') and not \
                argument.startswith('@') and not \
                self._get_id_match(argument) and not \
                re.match(r'<@!?([0-9]{15,20})>$', argument):
                # Not a mention or an ID a name#tag or @username
                raise commands.errors.UserNotFound(argument)

            return await super().convert(ctx, argument.strip('@'))
