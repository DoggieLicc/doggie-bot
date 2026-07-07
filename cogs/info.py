import base64
import datetime

from discord import Emoji, Member, Role, User, app_commands, File, Thread, Invite, Message, TextChannel, VoiceChannel, StageChannel, NotFound, Forbidden, HTTPException
from discord.ext import commands
from discord.abc import GuildChannel
from discord.utils import oauth_url, snowflake_time

import whoisdomain as whois
import utils
from utils import CustomBot, CustomContext
from utils.menus import PaginatedMenu

def sync_whois(ctx: CustomContext, domain: str):
    try:
        query = whois.query(domain, ignore_returncode=True)

    except whois.exceptions.FailedParsingWhoisOutput as e:
        raise utils.DoggieBotException('Lookup failed!', 'Can\'t get WHOIS lookup! (Server down?)') from e

    except whois.exceptions.UnknownTld as e:
        raise utils.DoggieBotException('Unsupported TLD', 'Sorry, can\'t get domains from that TLD!') from e

    if not query:
        raise utils.DoggieBotException('Domain not found!', 'That domain wasn\'t found.')

    embed = utils.create_embed(ctx.author, title=f'WHOIS Lookup for {domain}')

    expiration_date = utils.user_friendly_dt(query.expiration_date) if query.expiration_date else 'Unknown'
    creation_date = utils.user_friendly_dt(query.creation_date) if query.creation_date else 'Unknown'

    embed.add_field(name='Name:', value=query.name, inline=False)
    embed.add_field(name='Registrar:', value=(query.registrar or 'Unknown'), inline=False)
    embed.add_field(name='Name Servers:', value=(('\n'.join(query.name_servers)) or 'Unknown'), inline=False)
    embed.add_field(name='Expiration Date:', value=expiration_date, inline=False)
    embed.add_field(name='Creation Date:', value=creation_date, inline=False)

    if getattr(query, 'owner', None):
        embed.add_field(name='Owner', value=query.owner, inline=False)

    if getattr(query, 'abuse_contact', None):
        embed.add_field(name='Abuse Contact', value=query.abuse_contact)

    if getattr(query, 'admin', None):
        embed.add_field(name='Admin', value=query.admin)

    if getattr(query, 'registrant', None):
        embed.add_field(name='Registrant', value=query.registrant)

    return embed


class EmotesView(PaginatedMenu[Emoji]):
    def format_line(self, item) -> str:
        return (f'**Emote:** {item}\n'
                f'**Name:** {item.name}\n'
                f'**ID:** {item.id}\n')

    async def get_page_contents(self) -> dict:
        embed = utils.create_embed(
            self.owner,
            title=f'Listing emotes: ({self.current_index}/{self.max_page})',
            description=self.current_page
        )
        return {'embed': embed}

class ChannelsView(PaginatedMenu[GuildChannel]):
    def format_line(self, item) -> str:
        return (f'**Channel:** {item.mention}\n'
                f'**Category:** {item.type.name.title()}\n'
                f'**ID:** {item.id}\n')

    async def get_page_contents(self) -> dict:
        embed = utils.create_embed(
            self.owner,
            title=f'Listing channels: ({self.current_index}/{self.max_page})',
            description=self.current_page
        )
        return {'embed': embed}


class Info(commands.Cog, name='Information'):
    """Get info for Discord objects, domains, and more"""

    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    @commands.hybrid_command(aliases=['guild'])
    @commands.guild_only()
    @app_commands.allowed_installs(users=False)
    async def server(self, ctx: CustomContext):
        """Shows info for this server"""
        if not ctx.guild:
            return

        guild = ctx.guild

        bot_count = sum(member.bot for member in guild.members)

        embed = utils.create_embed(
            ctx.author,
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
            value=f'Description: {guild.description or 'No description'}\n'
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
                  f'{guild.premium_subscriber_role.mention if guild.premium_subscriber_role else 'None'}',
            inline=False
        )

        embed.add_field(
            name='Counts:',
            value=f'Members: {guild.member_count} total members\n'
                  f'{(guild.member_count or 0) - bot_count} humans; {bot_count} bots\n'
                  f'Roles: {len(guild.roles)} roles\n'
                  f'Text channels: {len(guild.text_channels)} channels\n'
                  f'Voice Channels: {len(guild.voice_channels)} channels\n'
                  f'Emotes: {len(guild.emojis)} emotes',
            inline=False
        )

        embed.add_field(
            name='Security Info:',
            value=f'2FA required?: {'Yes' if guild.mfa_level else 'No'}\n'
                  f'Verification Level: {str(guild.verification_level).replace('_', ' ').title()}\n'
                  f'NSFW Filter: {str(guild.explicit_content_filter).replace('_', ' ').title()}'
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['member', 'ui'])
    @app_commands.describe(user='The user to get info about.')
    async def user(self, ctx: CustomContext, user: Member | User | None):
        """Shows information about the user specified, if no user specified then it returns info for you"""

        user = user or ctx.author

        fetched = user if user.banner else await self.bot.fetch_user(user.id)

        flags = [name.replace('_', ' ').title() for name, value in dict.fromkeys(iter(user.public_flags)) if value]
        badges = '\n'.join(flags) or 'None'

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {user} {utils.Emotes.badges(user)}:',
            thumbnail=user.display_avatar,
            image=fetched.banner
        )

        embed.add_field(
            name=f'Is bot? {utils.Emotes.bot_tag}',
            value=f'Yes\n'
                  f'[Invite This Bot]({oauth_url(user.id)})' if user.bot else 'No',
            inline=False
        )

        embed.add_field(
            name='General Info:',
            value=f'**User ID:** {user.id}\n'
                  f'**Creation Date:** {utils.user_friendly_dt(user.created_at)}\n'
                  f'**Badges:** {badges}',
            inline=False
        )

        if isinstance(user, Member) and user.guild == ctx.guild and ctx.guild and user:
            role_mentions = utils.shorten_below_number(
                [role.mention for role in reversed(user.roles)][:-1],
                separator=' ',
                number=500
            )
            top_role = user.top_role.mention if user.top_role != ctx.guild.default_role else 'No roles!'

            embed.add_field(
                name='Member Info:',
                value=f'**Nickname:** {user.nick or 'No nickname'}\n'
                      f'**Joined Server At:** {utils.user_friendly_dt(user.joined_at)}\n'
                      f'**Highest Role:** {top_role}\n'
                      f'**Roles:** {role_mentions or 'No roles!'}',
                inline=False
            )

            embed.add_field(
                name=f'Permissions: {utils.Emotes.stafftools}',
                value=utils.format_perms(user.guild_permissions),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['pfp'])
    @app_commands.describe(user='The user to get info about.')
    async def avatar(self, ctx: CustomContext, user: Member | User | None):
        """Shows the avatar of the specified user, if no user specified then it returns info for you"""

        user = user or ctx.author

        avatar = user.display_avatar

        addit_anim_links = ''
        if avatar.is_animated():
            addit_anim_links = f' | [GIF]({avatar.with_format('gif')})'

        embed = utils.create_embed(
            ctx.author,
            description=f'[JPG]({avatar.with_format('jpg')}) | [WEBP]({avatar.with_format('webp')}) | [PNG]({avatar.with_format('png')})' + addit_anim_links,
            title=f'Avatar of {user}:',
            image=avatar
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['inv'])
    @app_commands.describe(invite='The Discord invite to get info for')
    async def invite(self, ctx: CustomContext, invite: Invite):
        """Shows info for an invite using a invite URL or its code"""

        embed = utils.create_embed(
            ctx.author,
            title=f'Invite Info: {utils.Emotes.invite}',
            thumbnail=getattr(invite.guild, 'icon', None),
            image=getattr(invite.guild, 'banner', None)
        )

        if invite.channel:
            embed.add_field(
                name='Invite channel:',
                value=f'**Name:** #{getattr(invite.channel, 'name', 'Unknown')} {utils.Emotes.channel(invite.channel)}\n'
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

        if invite.guild:
            embed.add_field(
                name='Server Info:',
                value=f'**Name:** {invite.guild}\n'
                    f'**Description:** {getattr(invite.guild, 'description', 'None')}\n'
                    f'**ID:** {invite.guild.id}\n'
                    f'**Created at:** {utils.user_friendly_dt(invite.guild.created_at)}'
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['chann', 'chan'])
    @commands.guild_only()
    @app_commands.allowed_installs(users=False)
    @app_commands.describe(channel='The channel to get info for')
    async def channel(self, ctx: CustomContext, channel: GuildChannel | Thread):
        """Shows info for the channel specified"""

        if not ctx.guild or not ctx.channel:
            return

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {channel.name}: {utils.Emotes.channel(channel)}',
            thumbnail=ctx.guild.icon
        )

        if isinstance(channel, (TextChannel, Thread)):
            slowmode = 'Disabled' if not channel.slowmode_delay else f'{channel.slowmode_delay} seconds'
            embed.add_field(name=f'Slowmode: {utils.Emotes.slowmode}', value=slowmode, inline=False)
            embed.add_field(name='NSFW?:', value=('Yes' if channel.is_nsfw() else 'No'), inline=False)

            if not isinstance(channel, Thread):
                embed.add_field(name='Topic:', value=(channel.topic or 'No topic set'), inline=False)

            else:
                embed.add_field(
                    name='Thread Info',
                    value=f'{len(await channel.fetch_members())} members\n'
                          f'Archived?: {'Yes' if channel.archived else 'No'}\n'
                          f'Locked?: {'Yes' if channel.locked else 'No'}\n'
                          f'Archive timestamp: {utils.user_friendly_dt(channel.archive_timestamp)}\n'
                          f'Archive time: {channel.auto_archive_duration} seconds\n'
                          f'Creator: {channel.owner.mention if channel.owner else 'Unknown'}',
                    inline=False
                )

        if isinstance(channel, VoiceChannel):
            embed.add_field(
                name='Voice Channel Info:',
                value=f'**Bitrate:** {round(channel.bitrate / 1000)}kbps\n'
                      f'**Region:** {str((channel.rtc_region or 'Automatic')).title()}\n'
                      f'**# Connected:** {len(channel.members)} connected '
                      f'{f'/ {channel.user_limit} max' if channel.user_limit else ''}',
                inline=False
            )

        if isinstance(channel, StageChannel):
            embed.add_field(name='Connected:', value=f'{len(channel.members)} connected')
            embed.add_field(name='Region:', value=str((channel.rtc_region or 'Automatic')).title())

        embed.add_field(
            name='General Channel Info:',
            value=f'**Type:** {str(channel.type).replace('_', ' ').title()} channel\n'
                  f'**Category:** {channel.category}\n'
                  f'**ID:** {channel.id}\n'
                  f'**Created at:** {utils.user_friendly_dt(channel.created_at)}',
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.guild_only()
    @app_commands.allowed_installs(users=False)
    @app_commands.describe(role='The role to get info for')
    async def role(self, ctx: CustomContext, role: Role):
        """Shows info for the role specified"""

        if not ctx.guild:
            return

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {role.name} {utils.Emotes.role}:',
            thumbnail=role.icon
        )

        if role.is_bot_managed() and role.tags and role.tags.bot_id:
            bot = ctx.guild.get_member(role.tags.bot_id)
            embed.add_field(name='Bot manager name:', value=str(bot), inline=False)
            embed.add_field(name='Bot manager ID:', value=role.tags.bot_id, inline=False)

        elif role.is_integration() and role.tags and role.tags.integration_id:
            embed.add_field(name='Integration ID:', value=role.tags.integration_id, inline=False)

        embed.add_field(
            name='General Info:',
            value=f'**Name:** {role.mention}\n'
                  f'**Position:** {role.position}\n'
                  f'**ID:** {role.id}\n'
                  f'**Color:** {role.color}\n'
                  f'**Created at:** {utils.user_friendly_dt(role.created_at)}\n'
                  f'**# members with role:** {len(role.members)}\n'
                  f'**Mentionable?:** {'Yes' if role.mentionable else 'No'}\n'
                  f'**Hoisted?:** {'Yes' if role.hoist else 'No'}\n',
            inline=False
        )

        embed.add_field(
            name=f'{utils.Emotes.stafftools} Permissions:',
            value=utils.format_perms(role.permissions) or 'None',
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['emoji'])
    @app_commands.describe(emote='The emote to get info for')
    async def emote(self, ctx: CustomContext, emote: utils.PartialEmoteConverter):
        """Shows info of a custom Discord emote"""

        if not emote.id:
            raise utils.DoggieBotException('Invalid Emote!', 'This doesn\'t seem like a valid emote...')

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for custom emote: {utils.Emotes.emoji}',
            thumbnail=emote.url
        )

        embed.add_field(name='Emote name:', value=emote.name, inline=False)
        embed.add_field(name='Emote ID:', value=emote.id, inline=False)
        embed.add_field(name='Animated?:', value='Yes' if emote.animated else 'No')
        embed.add_field(name='Created at:', value=utils.user_friendly_dt(emote.created_at), inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @app_commands.describe(token='The Discord account token to get info for')
    async def token(self, ctx: CustomContext, token: str):
        """Shows info of an account/bot token!"""

        tokens = token.split('.', 2)
        if len(tokens) != 3:
            raise utils.DoggieBotException('Invalid token!', 'The specified token is not a valid Discord token')

        # pylint: disable=broad-exception-caught
        try:
            user = await self.bot.fetch_user(int(base64.b64decode(tokens[0])))
            bytes_int = base64.urlsafe_b64decode(tokens[1] + '==')
            bytes_decoded = int.from_bytes(bytes_int, 'big')
        except Exception as e:
            raise utils.DoggieBotException('Invalid token!', 'The specified token is not a valid Discord token') from e

        time = datetime.datetime.utcfromtimestamp(bytes_decoded)

        if time.year < 2015:
            time = datetime.datetime.utcfromtimestamp(bytes_decoded + 1293840000)

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {user.name}\'s token!',
            thumbnail=user.display_avatar,
            image=user.banner
        )

        embed.add_field(
            name='Token Info:',
            value=f'**Token:** {'.'.join(tokens)}\n'
                  f'**Creation Date:** {utils.user_friendly_dt(time)}',
            inline=False
        )

        embed.add_field(
            name='User Info:',
            value=f'**Name:** {user}\n'
                  f'**ID:** {user.id}\n'
                  f'**Is bot?:** {'Yes' if user.bot else 'No'}\n'
                  f'**Created at:** {utils.user_friendly_dt(user.created_at)}'
        )

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(aliases=['msg'])
    @app_commands.allowed_installs(users=False)
    @app_commands.describe(message='The message to get info for, best to use the message link')
    async def message(self, ctx: CustomContext, message: Message):
        """Gets information for a Discord Message"""

        if message.guild != ctx.guild or (message.guild is None and (message.channel != ctx.channel)):
            raise utils.DoggieBotException('Invalid message!', 'Can\'t get a message from a different server!')

        embed = utils.create_embed(
            ctx.author,
            title='Info for message:',
            description=f'"{message.content}"' if message.content else '*Message has no content*',
            url=message.jump_url,
        )

        images = [a.url for a in message.attachments if a.content_type and a.content_type.startswith('image')]

        embed.set_author(name=message.author, icon_url=utils.fix_url(message.author.display_avatar))

        attachments = '\n'.join([f'[{a.filename}]({a.url})' for a in message.attachments]) or 'No attachments'

        embed.add_field(name='Attachments:', value=attachments, inline=False)

        if message.reference and message.reference.message_id:
            try:
                replied = await message.channel.fetch_message(message.reference.message_id)
            except (NotFound, Forbidden, HTTPException):
                replied = None

            if replied:
                embed.add_field(
                    name='Replied Message:',
                    value=f'ID: {replied.id}\n'
                          f'Author: {replied.author.mention}\n'
                          f'Content: {replied.content[:100] or '*No content*'}\n'
                          f'[Jump to Message]({replied.jump_url})'
                )

        embed.add_field(
            name='Info:',
            value=f'ID: {message.id}\n'
                  f'Channel: <#{message.channel.id}> ({message.channel.id})\n'
                  f'Created at: {utils.user_friendly_dt(message.created_at)}\n'
                  f'{len(message.mentions)} members mentioned\n'
                  f'Stickers: {(', '.join([f'[{s}]({s.url})' for s in message.stickers]) or 'No stickers')}\n'
                  f'Embeds: {len(message.embeds)} embeds',
            inline=False
        )

        image_embeds = [utils.create_embed(None, url=message.jump_url, image=image) for image in images]

        await ctx.send(embeds=[embed] + image_embeds)

    @commands.hybrid_command(aliases=['colour'])
    @app_commands.describe(colors='The color name or a member/role to get colors of')
    async def color(self, ctx: CustomContext, colors: utils.ColorConverter):
        """Gets info for a color! You can specify a member, role, or color"""

        embeds = []
        files = []

        for i, color in enumerate(colors):
            buffer = await self.bot.loop.run_in_executor(None, utils.solid_color_image, color.to_rgb())
            files.append(File(filename=f'color{i+1}.png', fp=buffer))

            embed = utils.create_embed(
                ctx.author,
                title=f'Info for color #{i+1}:',
                color=color,
                thumbnail=f'attachment://color{i+1}.png'
            )

            embed.add_field(name='Hex:', value=f'`{color}`')
            embed.add_field(name='Int:', value=f'`{str(color.value).zfill(8)}`')
            embed.add_field(name='RGB:', value=f'`{color.to_rgb()}`')
            embeds.append(embed)

        await ctx.send(files=files, embeds=embeds)

    @commands.hybrid_command(aliases=['domain'])
    @commands.cooldown(1, 10, commands.BucketType.user)
    @app_commands.describe(domain='The domain to get a WHOIS lookup for')
    async def whois(self, ctx: CustomContext, domain: str):
        """Does a WHOIS lookup on a domain!"""

        embed = await self.bot.loop.run_in_executor(None, sync_whois, ctx, domain)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['emotes', 'listemojis'], guild_only=True)
    @app_commands.allowed_installs(users=False)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def listemotes(self, ctx: CustomContext):
        """List all custom emotes in this server!"""
        if not ctx.guild:
            return

        if not ctx.guild.emojis:
            raise utils.DoggieBotException('No emotes!', 'This server has no custom emotes to show.')

        view = EmotesView(ctx.author, ctx.guild.emojis)

        await ctx.send(view=view, ephemeral=True, **await view.get_page_contents())

    @commands.hybrid_command(aliases=['channels'], guild_only=True)
    @app_commands.allowed_installs(users=False)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def listchannels(self, ctx: CustomContext):
        """List all channels in this server!"""
        if not ctx.guild:
            return

        if not ctx.guild.channels:
            raise utils.DoggieBotException('No channels!', 'This server has no channels to show... somehow?')

        view = ChannelsView(ctx.author, ctx.guild.channels)

        await ctx.send(view=view, ephemeral=True, **await view.get_page_contents())

    @commands.hybrid_command(aliases=['id'])
    @app_commands.describe(_id='The Discord ID to get info of')
    @app_commands.rename(_id='id')
    async def snowflake(self, ctx: CustomContext, _id: str = commands.parameter(displayed_name='id')):
        """Gets creation date for a Discord snowflake"""

        try:
            time = snowflake_time(int(_id))
            embed = utils.create_embed(
                ctx.author,
                title='Snowflake info:',
                description=f'**ID:** {_id}\n'
                            f'**Creation Date:** {utils.user_friendly_dt(time)}'
            )

        except OSError as e:
            raise utils.DoggieBotException('Invalid ID!', 'The snowflake ID was invalid.') from e

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))
