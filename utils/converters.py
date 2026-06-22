import re

from discord.ext import commands
from discord import Member, User, TextChannel, PartialEmoji, Asset, Message, StickerFormatType, Emoji
from discord import DiscordException, HTTPException, NotFound, Forbidden

__all__ = [
    'IntentionalMember',
    'IntentionalUser',
    'MentionedTextChannel',
    'NitrolessEmoteConverter',
]

ID_REGEX = re.compile(r'([0-9]{15,20})$')


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
    async def convert(self, _, argument: str):
        return {'url': argument.strip('<>\n ')}


class URLConverter(commands.Converter):
    async def convert(self, _, argument: str):
        return argument.strip('<>\n ')


class ColorIntConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        argument = argument.strip('\n ')

        if argument.isnumeric():
            return int(argument)

        color = await commands.ColorConverter().convert(ctx, argument)
        return color.value


class NitrolessEmoteConverter(commands.Converter):
    async def convert(self, ctx, argument: str) -> Emoji | PartialEmoji:
        argument = argument.strip('`\n \\').replace(';', ':')

        try:
            return await commands.EmojiConverter().convert(ctx, argument)
        except (commands.CommandError, commands.BadArgument):
            pass

        return await commands.PartialEmojiConverter().convert(ctx, argument)
