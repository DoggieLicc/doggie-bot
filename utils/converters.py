import re

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord import Color, Member, User
from discord.ext import commands
from discord.ext.commands import BadTimestampArgument, CommandError, RoleNotFound, MemberNotFound
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
    TimeConverter = timedelta
    ColorConverter = Color
    MultiplePartialEmoteConverter = list[discord.PartialEmoji]
    PartialEmoteConverter = discord.PartialEmoji
    IntentionalMember = Member
    IntentionalUser = User
else:
    class TimeConverter(commands.Converter):
        @staticmethod
        def get_unit(text: str) -> timedelta:
            text = text.lower()

            if text in ['s', 'sec', 'secs', 'second', 'seconds']:
                return timedelta(seconds=1)
            if text in ['m', 'min', 'mins', 'minute', 'minutes']:
                return timedelta(minutes=1)
            if text in ['h', 'hr', 'hrs', 'hour', 'hours']:
                return timedelta(hours=1)
            if text in ['d', 'day', 'days']:
                return timedelta(days=1)
            if text in ['w', 'wk', 'wks', 'week', 'weeks']:
                return timedelta(weeks=1)
            if text in ['mo', 'mos', 'month', 'months']:
                return timedelta(days=30)
            if text in ['y', 'yr', 'yrs', 'year', 'years']:
                return timedelta(days=365)
            return timedelta()

        async def convert(self, ctx, argument: str) -> timedelta | None:
            argument = argument.replace(',', '')

            if argument.lower() in ['in', 'me', 'at']:
                return timedelta()

            try:
                # pylint: disable=no-value-for-parameter
                conv: Converter = commands.Timestamp()  # type: ignore
                dt = await conv.convert(ctx, argument)
                td = dt - datetime.now(tz=timezone.utc)
                return td
            except BadTimestampArgument:
                pass

            try:
                amount, unit = [re.findall(r'(\d+)(\w+)', argument)[0]][0]
                if amount == 0:
                    raise commands.CommandError('Amount can\'t be zero')

                amount = int(amount)
                td = self.get_unit(unit)
                if td == timedelta():
                    raise commands.CommandError('Invalid unit')
            except CommandError:
                raise
            except Exception as e:
                raise commands.CommandError() from e

            return td * amount

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
