import base64
import datetime

from typing import Optional, Union

import whois as whois
import aiowiki
import discord
from discord import Color, Member, Role, User
from discord.ext import commands

import utils


def sync_whois(ctx: utils.CustomContext, domain: str):
    if not isinstance(domain, str):
        return utils.create_embed(
            ctx.author,
            title='Error!',
            description='It seems that you confused this command with ``user``, '
                        'this command is for [WHOIS](https://www.whois.net) lookup only.',
            color=discord.Color.red()
        )

    try:
        query = whois.query(domain)

    except whois.exceptions.FailedParsingWhoisOutput:
        return utils.create_embed(
            ctx.author,
            title='Error!',
            description='Can\'t get WHOIS lookup! (Server down?)',
            color=discord.Color.red()
        )

    except whois.exceptions.UnknownTld:
        return utils.create_embed(
            ctx.author,
            title='Error!',
            description='Sorry, can\'t get domains from that TLD!',
            color=discord.Color.red()
        )

    if not query:
        return utils.create_embed(
            ctx.author,
            title='Error!',
            description='Domain not found! (This command is for website domains, not discord users)',
            color=discord.Color.red()
        )

    embed = utils.create_embed(ctx.author, title=f'WHOIS Lookup for {domain}')

    expiration_date = utils.user_friendly_dt(query.expiration_date) if query.expiration_date else 'Unknown'
    creation_date = utils.user_friendly_dt(query.creation_date) if query.creation_date else 'Unknown'

    embed.add_field(name='Name:', value=query.name, inline=False)
    embed.add_field(name='Registrar:', value=(query.registrar or 'Unknown'), inline=False)
    embed.add_field(name='Name Servers:', value=(('\n'.join(query.name_servers)) or 'Unknown'), inline=False)
    embed.add_field(name='Expiration Date:', value=expiration_date, inline=False)
    embed.add_field(name='Creation Date:', value=creation_date, inline=False)

    if hasattr(query, 'owner'):
        embed.add_field(name='Owner', value=query.owner, inline=False)

    if hasattr(query, 'abuse_contact'):
        embed.add_field(name='Abuse Contact', value=query.abuse_contact)

    if hasattr(query, 'admin'):
        embed.add_field(name='Admin', value=query.admin)

    if hasattr(query, 'registrant'):
        embed.add_field(name='Registrant', value=query.registrant)

    return embed


async def format_page(ctx: utils.CustomContext, page: aiowiki.Page, summary: str, search: str) -> discord.Embed:
    summary = (summary[:3900] + '...') if len(summary) > 3900 else summary
    urls = await page.urls()

    embed = utils.create_embed(
        ctx.author,
        title=f'Wikipedia page for "{search}"',
        description=summary,
        url=urls[0],
    )

    return embed


class Info(commands.Cog, name='Information'):
    """Get info for Discord objects, domains, and more"""

    def __init__(self, bot: utils.CustomBot):
        self.wiki = aiowiki.Wiki.wikipedia()
        self.bot: utils.CustomBot = bot

    @commands.command(aliases=['guild'])
    @commands.guild_only()
    async def server(self, ctx: utils.CustomContext):
        """Lists info for the current guild"""

        guild: discord.Guild = ctx.guild

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
            value=f'Description: {guild.description or "No description"}\n'
                  f'Owner: {guild.owner} ({guild.owner_id})\n'
                  f'Region: {str(guild.region).replace("-", " ").title()}\n'
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
                  f'Emotes: {len(ctx.guild.emojis)} emotes',
            inline=False
        )

        embed.add_field(
            name='Security Info:',
            value=f'2FA required?: {"Yes" if guild.mfa_level else "No"}\n'
                  f'Verification Level: {str(guild.verification_level).replace("_", " ").title()}\n'
                  f'NSFW Filter: {str(guild.explicit_content_filter).replace("_", " ").title()}'
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=['member'])
    async def user(self, ctx: utils.CustomContext, *, user: Optional[Union[discord.Member, discord.User, str]]):
        """Shows information about the user specified, if no user specified then it returns info for invoker"""

        user: Union[discord.Member, discord.User, str] = user or ctx.author

        if isinstance(user, str):
            raise commands.UserNotFound(user)

        flags = [name.replace('_', ' ').title() for name, value in dict.fromkeys(iter(user.public_flags)) if value]
        badges = '\n'.join(flags) or 'None'

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {user} {utils.Emotes.badges(user)}:',
            thumbnail=user.display_avatar
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

        if isinstance(user, discord.Member) and user.guild == ctx.guild:
            role_mentions = [role.mention for role in reversed(user.roles)][:-1]
            top_role = user.top_role.mention if user.top_role != ctx.guild.default_role else 'No roles!'

            embed.add_field(
                name='Member Info:',
                value=f'**Nickname:** {user.nick or "No nickname"}\n'
                      f'**Joined Server At:** {utils.user_friendly_dt(user.joined_at)}\n'
                      f'**Highest Role:** {top_role}\n'
                      f'**Roles:** {" ".join(role_mentions) or "No roles!"}',
                inline=False
            )

            embed.add_field(
                name=f'Permissions: {utils.Emotes.stafftools}',
                value=utils.format_perms(user.guild_permissions),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(aliases=['pfp'])
    async def avatar(self, ctx: utils.CustomContext, *, user: Optional[discord.User]):
        """Shows user's avatar using their ID or name"""

        user: discord.User = user or ctx.author

        embed = utils.create_embed(
            ctx.author,
            title=f'Avatar of {user}:',
            image=user.display_avatar
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=['inv'])
    async def invite(self, ctx: utils.CustomContext, invite: discord.Invite):
        """Shows info for an invite using a invite URL or its code"""

        embed = utils.create_embed(
            ctx.author,
            title=f'Invite Info: {utils.Emotes.invite}',
            thumbnail=invite.guild.icon,
            image=invite.guild.banner
        )

        embed.add_field(
            name='Invite channel:',
            value=f'**Name:** #{invite.channel.name} {utils.Emotes.channel(invite.channel)}\n'
                  f'**ID:** {invite.channel.id}',
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

        await ctx.send(embed=embed)

    @commands.command(aliases=['chann', 'chan'])
    @commands.guild_only()
    async def channel(self, ctx: utils.CustomContext, *, channel: Union[discord.abc.GuildChannel, discord.Thread]):
        """Shows info for the channel specified using channel mention or ID"""

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {channel.name}: {utils.Emotes.channel(channel)}',
            thumbnail=ctx.guild.icon.url
        )

        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            slowmode = 'Disabled' if not channel.slowmode_delay else f'{channel.slowmode_delay} seconds'
            embed.add_field(name=f'Slowmode: {utils.Emotes.slowmode}', value=slowmode, inline=False)
            embed.add_field(name='NSFW?:', value=('Yes' if channel.is_nsfw() else 'No'), inline=False)

            if not isinstance(channel, discord.Thread):
                embed.add_field(name='Topic:', value=(channel.topic or 'No topic set'), inline=False)

            else:
                embed.add_field(
                    name='Thread Info',
                    value=f'{len(await channel.fetch_members())} members\n'
                          f'Archived?: {"Yes" if channel.archived else "No"}\n'
                          f'Locked?: {"Yes" if channel.locked else "No"}\n'
                          f'Archive timestamp: {utils.user_friendly_dt(channel.archive_timestamp)}\n'
                          f'Archive time: {channel.auto_archive_duration} seconds\n'
                          f'Creator: {channel.owner.mention}',
                    inline=False
                )

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
            name='Channel type:',
            value=f'{str(channel.type).replace("_", " ").title()} Channel',
            inline=False
        )

        embed.add_field(name='Channel category:', value=channel.category)
        embed.add_field(name='Channel ID:', value=channel.id, inline=False)

        if not isinstance(channel, discord.Thread):
            embed.add_field(name='Creation date:', value=utils.user_friendly_dt(channel.created_at), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def role(self, ctx: utils.CustomContext, *, role: discord.Role):
        """Shows info for the role specified using role mention or ID"""

        embed = utils.create_embed(ctx.author, title=f'Info for {role.name} {utils.Emotes.role}:')

        if role.is_bot_managed():
            bot = ctx.guild.get_member(role.tags.bot_id)
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
            value=utils.format_perms(role.permissions),
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=['emoji'])
    async def emote(
            self,
            ctx: utils.CustomContext,
            emoji: Union[discord.Emoji, discord.PartialEmoji, utils.NitrolessEmoteConverter]):
        """Shows info of emote using the emote ID or emote itself"""

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for custom emote: {utils.Emotes.emoji}',
            thumbnail=emoji.url
        )

        embed.add_field(name='Emote name:', value=emoji.name, inline=False)
        embed.add_field(name='Emote ID:', value=emoji.id, inline=False)
        embed.add_field(name='Animated?:', value='Yes' if emoji.animated else 'No')

        if isinstance(emoji, discord.PartialEmoji):
            return await ctx.send(embed=embed)

        embed.add_field(name='Created at:', value=utils.user_friendly_dt(emoji.created_at), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def token(self, ctx: utils.CustomContext, token: str):
        """Shows info of an account/bot token! (Don't use valid tokens in public servers!)"""

        token = token.split('.', 2)
        if len(token) != 3:
            embed = utils.create_embed(
                ctx.author,
                title='Error!',
                description='Invalid token!',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        # noinspection PyBroadException
        try:
            user = await self.bot.fetch_user(int(base64.b64decode(token[0])))
            bytes_int = base64.urlsafe_b64decode(token[1] + '==')
            bytes_decoded = int.from_bytes(bytes_int, 'big')

        except Exception:
            embed = utils.create_embed(
                ctx.author,
                title='Error!',
                description='Invalid token!',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        time = datetime.datetime.utcfromtimestamp(bytes_decoded)

        if time.year < 2015:
            time = datetime.datetime.utcfromtimestamp(bytes_decoded + 1293840000)

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {user.name}\'s token!',
            thumbnail=user.display_avatar
        )

        embed.add_field(
            name='Token Info:',
            value=f'**Token:** {token}\n'
                  f'**Creation Date:** {utils.user_friendly_dt(time)}',
            inline=False
        )

        embed.add_field(
            name='User Info:',
            value=f'**Name:** {user}\n'
                  f'**ID:** {user.id}\n'
                  f'**Is bot?:** {"Yes" if user.bot else "No"}'
                  f'**Created at:** {utils.user_friendly_dt(user.created_at)}'
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=['msg'])
    async def message(self, ctx: utils.CustomContext, message: discord.Message):
        """Gets information for a Discord Message!
        You can specify the message using the message's link"""

        if message.guild != ctx.guild:
            raise commands.MessageNotFound(message)

        embed = utils.create_embed(
            ctx.author,
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

        await ctx.send(embeds=[embed] + image_embeds)

    @commands.command(aliases=['colour'])
    async def color(self, ctx: utils.CustomContext, *, color: Union[Color, Role, Member]):
        """Gets info for a color! You can specify a member, role, or color.
        Use the formats: `0x<hex>`, `#<hex>`, `0x#<hex>`, or `rgb(<num>, <num>, <num>)`"""

        alias = ctx.invoked_with.lower()

        color = color if isinstance(color, Color) else color.color

        buffer = await self.bot.loop.run_in_executor(None, utils.solid_color_image, color.to_rgb())
        file = discord.File(filename="color.png", fp=buffer)

        embed = utils.create_embed(
            ctx.author,
            title=f'Info for {alias}:',
            color=color,
            thumbnail="attachment://color.png"
        )

        embed.add_field(name='Hex:', value=f'`{color}`')
        embed.add_field(name='Int:', value=f'`{str(color.value).zfill(8)}`')
        embed.add_field(name='RGB:', value=f'`{color.to_rgb()}`')

        await ctx.send(file=file, embed=embed)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(aliases=['domain'])
    async def whois(self, ctx: utils.CustomContext, domain: Union[Member, User, str]):
        """Does a WHOIS lookup on a domain!"""

        async with ctx.channel.typing():
            embed = await self.bot.loop.run_in_executor(None, sync_whois, ctx, domain)
        await ctx.send(embed=embed)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(aliases=['wiki'])
    async def wikipedia(self, ctx: utils.CustomContext, *, search):
        """Looks up Wikipedia articles by their title!"""

        page = self.wiki.get_page(search)

        try:
            summary = await page.summary()
        except aiowiki.PageNotFound:
            summary = None

        if summary:
            embed = await format_page(ctx, page, summary, search)
        else:
            pages = await self.wiki.opensearch(search)

            if pages:

                best_search = [page.title for page in pages if page.title.lower() == search.lower()]

                if best_search:
                    page = self.wiki.get_page(best_search[0])
                    summary = await page.summary()

                    embed = await format_page(ctx, page, summary, search)

                else:

                    titles = [page.title for page in pages]

                    embed = utils.create_embed(
                        ctx.author,
                        title=f'No page found for "{search}"! Did you mean...',
                        description='\n'.join(titles),
                        color=discord.Color.red()
                    )

            else:
                embed = utils.create_embed(
                    ctx.author,
                    title=f'No results found for "{search}"!',
                    description='Try to search something else!',
                    color=discord.Color.red()
                )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Info(bot))
