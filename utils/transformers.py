from typing import Any

import discord
from discord import app_commands, Interaction, Message
from discord.utils import cached_property, maybe_coroutine
from discord.app_commands import Choice
from discord.ext.commands import MessageConverter, MemberConverter, RoleConverter, BadArgument, CommandError, InviteConverter, ColorConverter


__all__ = [
    'FakeContext',
    'FakeMessage',
    'MessageTransformer',
    'GreedyMemberRoleTransformer',
    'PartialEmoteTransformer',
    'InviteTransformer',
    'ColorTransformer'
]


class FakeContext(discord.Object):
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
        super().__init__(id=0)


class FakeMessage(discord.Object):
    # pylint: disable=no-member
    def __init__(self, guild: discord.Guild | None, content: str):
        self.content = content
        self.guild = guild
        super().__init__(id=0)

    @cached_property
    def raw_mentions(self) -> list[int]:
        return Message.raw_mentions.function(self)

    @cached_property
    def raw_channel_mentions(self) -> list[int]:
        return Message.raw_channel_mentions.function(self)

    @cached_property
    def raw_role_mentions(self) -> list[int]:
        return Message.raw_role_mentions.function(self)

    @cached_property
    def channel_mentions(self) -> list[discord.abc.GuildChannel | discord.Thread]:
        return Message.channel_mentions.function(self)

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
        return Message.clean_content.function(self)


class MessageTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> discord.Message:
        if value.isnumeric():  # MessageConverter does not fetch message for an id, so we handle it here
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

        fake_ctx = FakeContext(bot=interaction.client, guild=interaction.guild)
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
            raise SDGException()

        return items


class PartialEmoteTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> discord.PartialEmoji:
        value = value.strip('`\n \\').replace(';', ':')

        return discord.PartialEmoji.from_str(value, client=interaction.client)

class InviteTransformer(app_commands.Transformer):
    # pylint: disable=abstract-method
    async def transform(self, interaction: Interaction, value: str, /) -> discord.Invite:
        fakectx = FakeContext(bot=interaction.client)
        return await InviteConverter().convert(fakectx, value)

class ColorTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str, /) -> list[discord.Color]:
        fakectx = FakeContext(bot=interaction.client, guild=interaction.guild)
        try:
            member = await MemberConverter().convert(fakectx, value)
            return [member.color]
        except Exception:
            pass

        try:
            role = await RoleConverter().convert(fakectx, value)
            return [c for c in [role.color, role.secondary_color, role.tertiary_color] if c is not None]
        except Exception:
            pass

        return [await ColorConverter().convert(fakectx, value)]
