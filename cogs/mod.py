import unicodedata
from functools import partial

from discord import Message, CategoryChannel, Color, DMChannel, ForumChannel, GroupChannel, PartialMessageable, app_commands, Member, User, Role, Embed, TextChannel, Interaction, ui, ButtonStyle
from discord.ext import commands

import utils
from utils import CustomBot, CustomContext

async def add_mute(member: Member, role: Role, **kwargs):
    await member.add_roles(role, **kwargs)


async def remove_mute(member: Member, role: Role, **kwargs):
    await member.remove_roles(role, **kwargs)


class SnipeMenu(utils.EntryMenu[Embed | Message]):
    async def get_page_contents(self):
        message = self.get_page_items()[0]
        if isinstance(message, Embed):
            return {"embed": message}

        embed = utils.format_deleted_msg(message, title=f'Sniped message {self.current_index}/{self.max_page}:')

        embed.set_footer(
            text=f'Command sent by {self.owner}',
            icon_url=utils.fix_url(self.owner.display_avatar)
        )

        return {"embed": embed}


class EnableSnipeView(utils.CustomView):
    async def interaction_check(self, interaction: Interaction[CustomBot], /) -> bool:
        self.message = interaction.message
        if not interaction.guild or isinstance(self.owner, User):
            return False

        if not self.owner.guild_permissions.manage_guild:
            await interaction.response.send_message('You need `Manage Server` permissions to enable message snipes...', ephemeral=True)
            return False

        basic_config = interaction.client.get_basic_config(interaction.guild)

        if basic_config.snipe:
            await interaction.response.send_message('Message sniping is already enabled in this server!', ephemeral=True)
            await self.on_timeout()
            return False

        return True

    @ui.button(label='MOD ACTION: Enable Message Sniping', style=ButtonStyle.red)
    async def enable_snipe(self, interaction: Interaction[CustomBot], _: ui.Button):
        basic_config = interaction.client.get_basic_config(interaction.guild)
        await basic_config.set_config(interaction.client, snipe=True)
        await self.on_timeout()
        await interaction.response.send_message('Message sniping has been enabled for this server! `/config`', ephemeral=True)


@commands.guild_only()
@app_commands.allowed_installs(users=False)
class Moderation(commands.GroupCog, group_name='mod'):
    """Commands to make moderation easier and simpler"""

    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    @commands.hybrid_command()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(users='Mentions or IDs of one or multiple users, space seperated')
    @app_commands.describe(reason='The reason for the ban. Shown in the audit log')
    async def ban(
        self,
        ctx: CustomContext,
        *,
        users: commands.Greedy[utils.IntentionalUser],
        reason: str | None = "No reason specified"
    ):
        """Ban members who broke the rules! You can specify multiple members in one command."""

        if not ctx.guild:
            return

        await ctx.defer()

        lists = await utils.multi_punish(
            ctx.author,
            users,
            ctx.guild.ban,
            reason=f'{str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'banned', reason, lists)

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(users='Mentions or IDs of one or multiple users, space seperated')
    @app_commands.describe(reason='The reason for the unban. Shown in the audit log')
    async def unban(
        self,
        ctx: CustomContext,
        *,
        users: commands.Greedy[utils.IntentionalUser],
        reason: str | None = "No reason specified"
    ):
        """Unban banned users with their User ID, you can specify multiple people to be unbanned"""

        if not ctx.guild:
            return

        await ctx.defer()

        lists = await utils.multi_punish(
            ctx.author,
            users,
            ctx.guild.unban,
            reason=f'{str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'unbanned', reason, lists)

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(users='Mentions or IDs of one or multiple users, space seperated')
    @app_commands.describe(reason='The reason for the softban. Shown in the audit log')
    async def softban(
        self,
        ctx: CustomContext,
        *,
        users: commands.Greedy[utils.IntentionalUser],
        reason: str | None = "No reason specified"
    ):
        """Bans then unbans the specified users, which deletes their recent messages and 'kicks' them"""

        if not ctx.guild:
            return

        await ctx.defer()

        banned, not_banned = await utils.multi_punish(
            ctx.author,
            users,
            ctx.guild.ban,
            reason=f'(Softban) {str(ctx.author)}: {reason}'
        )

        unbanned, _ = await utils.multi_punish(
            ctx.author,
            banned,
            ctx.guild.unban,
            reason=f'(Softban) {str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'softbanned', reason, (unbanned, not_banned))

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the kick. Shown in the audit log')
    async def kick(
        self,
        ctx: CustomContext,
        *,
        members: commands.Greedy[utils.IntentionalMember],
        reason: str | None = "No reason specified"
    ):
        """Kick members who broke the rules! You can specify multiple members in one command"""

        if not ctx.guild:
            return

        await ctx.defer()

        lists = await utils.multi_punish(
            ctx.author,
            members,
            ctx.guild.kick,
            reason=f'{str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'kicked', reason, lists)

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['timein', 'removetimeout'])
    @commands.bot_has_guild_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(duration='How long to timeout the member for. Can be a Discord-style timestamp, or durations (5h 30min)')
    @app_commands.describe(reason='The reason for the timeout. Shown in the audit log')
    async def timeout(
        self,
        ctx: CustomContext,
        *,
        members: commands.Greedy[utils.IntentionalMember],
        duration: utils.TimeConverter,
        reason: str | None = 'No reason specified'
    ):
        """Puts specified members in timeout! You can specify multiple members in one command"""

        await ctx.defer()

        lists = await utils.multi_punish(
            ctx.author,
            members,
            Member.edit,
            timed_out_until=duration,
            reason=f'{str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'timed out', reason, lists)

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.bot_has_guild_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the untimeout. Shown in the audit log')
    async def untimeout(
        self,
        ctx: CustomContext,
        *,
        members: commands.Greedy[utils.IntentionalMember],
        reason: str | None = "No reason specified"
    ):
        """Removes timeout from members!"""

        remove_timeout = partial(Member.edit, timed_out_until=None)

        lists = await utils.multi_punish(
            ctx.author,
            members,
            remove_timeout,
            reason=f'{str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'untimedout', reason, lists)

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['nick', 'nickname'])
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    @commands.has_permissions(manage_nicknames=True)
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(nickname='The new nickname to set for the members')
    async def rename(
        self,
        ctx: CustomContext,
        *,
        members: commands.Greedy[utils.IntentionalMember],
        nickname: str
    ):
        """Renames members to a specified name"""

        if len(nickname) > 32:
            raise utils.DoggieBotException('Nickname too long!', f'The nickname {nickname[:100]} is too long! (32 chars max.)')

        await ctx.defer()

        lists = await utils.multi_punish(
            ctx.author,
            members,
            Member.edit,
            nick=nickname,
            reason=f'Renamed by {ctx.author}'
        )

        embed = utils.punish_embed(ctx.author, 'renamed', nickname, lists)

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['silence'])
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the mute. Shown in the audit log')
    async def mute(
        self,
        ctx: CustomContext,
        *,
        members: commands.Greedy[utils.IntentionalMember],
        reason: str | None = "No reason specified"
    ):
        """Gives the configured mute role to members!"""

        mute_role = ctx.bot.get_basic_config(ctx.guild).mute_role

        if not mute_role:
            raise utils.DoggieBotException('Mute role not configured!', 'A server admin must use `/config edit` and set a mute role for this server')

        await ctx.defer()

        lists: tuple = await utils.multi_punish(
            ctx.author,
            members,
            add_mute,
            role=mute_role,
            reason=f'{str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'muted', reason, lists)

        await ctx.send(embed=embed)

        self.bot.dispatch('mute', ctx, lists[0], reason)

    @commands.hybrid_command(aliases=['unsilence'])
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    @app_commands.describe(reason='The reason for the unmute. Shown in the audit log')
    async def unmute(
        self,
        ctx: CustomContext,
        *,
        members: commands.Greedy[utils.IntentionalMember],
        reason: str | None = "No reason specified"
    ):
        """Removes the configured mute role from members!"""

        mute_role = ctx.bot.get_basic_config(ctx.guild).mute_role

        if not mute_role:
            raise utils.DoggieBotException('Mute role not configured!', 'A server admin must use `/config edit` and set a mute role for this server')

        await ctx.defer()

        lists = await utils.multi_punish(
            ctx.author,
            members,
            remove_mute,
            role=mute_role,
            reason=f'{str(ctx.author)}: {reason}'
        )

        embed = utils.punish_embed(ctx.author, 'unmuted', reason, lists)

        self.bot.dispatch('unmute', ctx, lists[0], reason)

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['clear', 'delete'])
    @commands.bot_has_guild_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(users='Mentions or IDs of one or multiple users to delete messages from, space seperated')
    @app_commands.describe(amount='The amount of messages to check. Max of 200')
    async def purge(
        self,
        ctx: CustomContext,
        *,
        users: commands.Greedy[utils.IntentionalUser],
        amount: commands.Range[int, 1, 200] | None = 200
    ):
        """Deletes multiple messages from the current channel."""

        amount = 200 if abs(amount) >= 200 else abs(amount) + 1

        await ctx.defer(ephemeral=True)

        if not ctx.channel or isinstance(ctx.channel, (ForumChannel, CategoryChannel, DMChannel, GroupChannel, PartialMessageable)):
            raise utils.DoggieBotException('Invalid channel!', 'Can\'t use purge in forums, dms, or groups.')

        messages_deleted = await ctx.channel.purge(limit=amount, check=lambda m: not users or (m.author in users), bulk=True)

        users_s = [user.mention for user in users] if users else ['anyone']
        embed = utils.create_embed(
            ctx.author,
            title=f'{len(messages_deleted)} messages deleted!',
            description='Deleted messages from ' + ', '.join(users_s)
        )

        await ctx.send(embed=embed)

        self.bot.dispatch('purge', ctx, users_s, len(messages_deleted))

    @commands.hybrid_command(aliases=['ascii'])
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    @commands.has_permissions(manage_nicknames=True)
    @app_commands.describe(members='Mentions or IDs of one or multiple server members, space seperated')
    async def asciify(
        self,
        ctx: CustomContext,
        *,
        members: commands.Greedy[utils.IntentionalMember],
    ):
        """Replace weird unicode letters in nicknames with normal ASCII text!"""

        async def rename(member: Member):
            ascii_text = unicodedata.normalize('NFKD', member.display_name).encode('ascii', 'ignore').decode()
            await member.edit(nick=ascii_text[:31] or 'Unreadable', reason=f'Asciified by {ctx.author}')

        await ctx.defer()

        lists = await utils.multi_punish(
            ctx.author,
            members,
            rename
        )

        embed = utils.punish_embed(ctx.author, 'asciified', 'Asciify strange characters', lists)

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['snpied', 'deleted'], guild_only=True)
    @app_commands.describe(channel='Specify a channel to get deleted messages from it. You can only snipe messages from channels in which you have `Manage Messages` and `View Channel` in.')
    @app_commands.describe(user='Specify an user to only get deleted messages from that user')
    async def snipe(
        self,
        ctx: CustomContext,
        channel: TextChannel | None,
        user: User | None
    ):
        """Shows recent deleted messages! Must be enabled by a mod first"""

        if not ctx.guild or not ctx.channel or isinstance(ctx.channel, (DMChannel, GroupChannel)):
            return

        if not ctx.bot.get_basic_config(ctx.guild).snipe:
            if isinstance(ctx.author, Member) and ctx.author.guild_permissions.manage_guild:
                view = EnableSnipeView(ctx.author)
                raise utils.DoggieBotException('Snipe not enabled!', 'You must use `/config edit` and enable message snipes for this server', view=view)
            raise utils.DoggieBotException('Snipe not enabled!', 'A server admin must use `/config edit` and enable message snipes for this server')

        channel = channel or ctx.channel  # type: ignore

        if not channel:
            return

        if not (channel.permissions_for(ctx.author).manage_messages and channel.permissions_for(ctx.author).view_channel):
            raise utils.DoggieBotException('Can\'t snipe from that channel!', 'You need permissions to view and manage messages of that channel before you can snipe messages from it!')

        await ctx.defer(ephemeral=True)

        filtered = [message for message in self.bot.sniped if (message.guild == ctx.guild)
                    and (user is None or user == message.author) and (channel == message.channel)][:100]

        if not filtered:
            raise utils.DoggieBotException('No messages found!', 'There is no recently deleted messages in this channel that fit the criteria')

        if not ctx.interaction:
            w_embed = utils.create_embed(
                ctx.author,
                title='Showing Deleted Messages!',
                description=f'This command will show recently deleted messages from {channel.mention}!\n'
                            f'It is recommended to use this command via slash commands so that only you may see them.',
                color=Color.orange()
            )
            filtered.insert(0, w_embed)

        view = SnipeMenu(ctx.author, filtered, 1)
        await ctx.send(view=view, **await view.get_page_contents())


async def setup(bot):
    await bot.add_cog(Moderation(bot))
