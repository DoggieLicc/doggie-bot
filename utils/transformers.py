import re

from datetime import datetime, timedelta, timezone

import discord
from discord import CategoryChannel, ForumChannel, app_commands, Interaction, Message
from discord.utils import cached_property
from discord.app_commands import Timestamp, TransformerError
from discord.ext.commands import BadArgument, RoleNotFound, UserNotFound, CommandError, MemberNotFound
from discord.ext.commands import MessageConverter, MemberConverter, RoleConverter, InviteConverter, ColorConverter, UserConverter


__all__ = [
    'FakeContext',
    'FakeMessage',
    'MessageTransformer',
    'GreedyMemberRoleTransformer',
    'GreedyMemberUserTransformer',
    'GreedyMemberTransformer',
    'PartialEmoteTransformer',
    'MultiplePartialEmoteTransformer',
    'InviteTransformer',
    'ColorTransformer',
    'TimeTransformer'
]

class FakeContext(discord.Object):
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
        super().__init__(id=0)


class FakeMessage(discord.Object):
    # pylint: disable=no-member

    def __init__(self, guild: discord.Guild | None = None, content: str = ''):
        self.content = content
        self.guild = guild
        super().__init__(id=0)

    @cached_property
    def raw_mentions(self) -> list[int]:
        return Message.raw_mentions.function(self)  # type: ignore

    @cached_property
    def raw_channel_mentions(self) -> list[int]:
        return Message.raw_channel_mentions.function(self)  # type: ignore

    @cached_property
    def raw_role_mentions(self) -> list[int]:
        return Message.raw_role_mentions.function(self)  # type: ignore

    @cached_property
    def channel_mentions(self) -> list[discord.abc.GuildChannel | discord.Thread]:
        return Message.channel_mentions.function(self)  # type: ignore

    @cached_property
    def mentions(self) -> list[discord.Member]:
        mentions = []
        if self.guild:
            for mention in self.raw_mentions:
                member = self.guild.get_member(mention)
                if member:
                    mentions.append(member)
        return mentions

    @cached_property
    def role_mentions(self) -> list[discord.Role]:
        role_mentions = []
        if self.guild:
            for mention in self.raw_role_mentions:
                role = self.guild.get_role(mention)
                if role:
                    role_mentions.append(role)

        return role_mentions

    @cached_property
    def clean_content(self) -> str:
        return Message.clean_content.function(self)  # type: ignore


class MessageTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> discord.Message:
        if value.isnumeric() and interaction.channel and not isinstance(interaction.channel, (ForumChannel, CategoryChannel)):  # MessageConverter does not fetch message for an id, so we handle it here
            state_msg = interaction.client._connection._get_message(int(value))
            message = state_msg or await interaction.channel.fetch_message(int(value))
            return message

        fake_ctx = FakeContext(bot=interaction.client, guild=interaction.guild)
        message_converter = MessageConverter()
        return await message_converter.convert(fake_ctx, value)  # type: ignore


class GreedyMemberRoleTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> list[discord.Role | discord.Member]:
        cleaned_value = value.replace('><', '> <').strip()
        arguments = cleaned_value.split()

        fake_ctx = FakeContext(
            bot=interaction.client,
            guild=interaction.guild,
            message=FakeMessage(),
            _state=interaction._state
        )

        member_converter = MemberConverter()
        role_converter = RoleConverter()
        items = []
        for argument in arguments:
            converted = None
            try:
                converted = await member_converter.convert(fake_ctx, argument)
            except (CommandError, BadArgument):
                try:
                    converted = await role_converter.convert(fake_ctx, argument)
                except (CommandError, BadArgument):
                    pass

            if converted is not None and converted not in items:
                items.append(converted)

        if not items:
            raise BadArgument()

        return items


class GreedyMemberTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> list[discord.Member]:
        cleaned_value = value.replace('><', '> <').strip()
        arguments = cleaned_value.split()

        fake_ctx = FakeContext(
            bot=interaction.client,
            guild=interaction.guild,
            message=FakeMessage(),
            _state=interaction._state
        )

        member_converter = MemberConverter()
        items = []
        for argument in arguments:
            converted = None
            try:
                converted = await member_converter.convert(fake_ctx, argument)
            except (CommandError, MemberNotFound):
                pass

            if converted is not None and converted not in items:
                items.append(converted)

        if not items:
            raise BadArgument()

        return items


class GreedyMemberUserTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> list[discord.User | discord.Member]:
        cleaned_value = value.replace('><', '> <').strip()
        arguments = cleaned_value.split()

        fake_ctx = FakeContext(
            bot=interaction.client,
            guild=interaction.guild,
            message=FakeMessage(),
            _state=interaction._state
        )

        member_converter = MemberConverter()
        user_converter = UserConverter()
        items = []
        for argument in arguments:
            converted = None
            try:
                converted = await member_converter.convert(fake_ctx, argument)
            except (CommandError, MemberNotFound):
                try:
                    converted = await user_converter.convert(fake_ctx, argument)
                except (CommandError, UserNotFound):
                    pass

            if converted is not None and converted not in items:
                items.append(converted)

        if not items:
            raise BadArgument()

        return items


class PartialEmoteTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> discord.PartialEmoji:
        value = value.strip('`\n \\').replace(';', ':')

        return discord.PartialEmoji.from_str(value, client=interaction.client)

class MultiplePartialEmoteTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> list[discord.PartialEmoji]:
        emotes = []

        value = value.strip('`\n \\').replace(';', ':').replace(',', ' ')

        for val in value.split():
            try:
                emote = discord.PartialEmoji.from_str(val, client=interaction.client)
                if emote not in emotes:
                    emotes.append(emote)
            except OSError:
                pass

        return emotes

class InviteTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> discord.Invite:
        fakectx = FakeContext(bot=interaction.client)
        return await InviteConverter().convert(fakectx, value)

class ColorTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> list[discord.Color]:
        fakectx = FakeContext(bot=interaction.client, guild=interaction.guild)
        try:
            member = await MemberConverter().convert(fakectx, value)
            return [member.color]
        except MemberNotFound:
            pass

        try:
            role = await RoleConverter().convert(fakectx, value)
            return [c for c in [role.color, role.secondary_color, role.tertiary_color] if c is not None]
        except RoleNotFound:
            pass

        return [await ColorConverter().convert(fakectx, value)]


class TimeTransformer(app_commands.Transformer):
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

    async def transform(self, interaction: Interaction, value: str, /) -> datetime:
        try:
            # pylint: disable=no-value-for-parameter
            return await Timestamp().transform(interaction, value)  # type: ignore
        except TransformerError:
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
