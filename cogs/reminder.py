from datetime import datetime, timedelta, timezone

from discord import app_commands, TextChannel
from discord.ext import commands
from discord.utils import escape_markdown

import utils
from utils import CustomBot, CustomContext
from utils.classes import Reminder

class ReminderList(utils.EntryMenu[Reminder]):
    async def get_page_contents(self):
        entries = self.get_page_items()

        embed = utils.create_embed(
            self.owner,
            title=f'Showing active reminders for {self.owner} ({self.current_index}/{self.max_page}):'
        )

        for reminder in entries:
            channel = reminder.destination if isinstance(reminder.destination, TextChannel) else None

            embed.add_field(
                name=f'ID: {reminder.id}',
                value=f'**Reminder:** {str(reminder)[:1100]}\n'
                        f'**Ends at:** {utils.user_friendly_dt(reminder.end_time)}\n'
                        f'**Destination:** {channel.mention if channel else 'Your DMS!'}\n',
                inline=False
            )

        return {'embed': embed}

class ReminderCog(commands.GroupCog, name='Reminder', group_name='reminder'):
    """Create and manage your reminders"""
    def __init__(self, bot: CustomBot):
        self.bot: CustomBot = bot

    @commands.hybrid_command(aliases=['r', 'remindme', 'reminder', 'remind'], usage='<duration> [channel] <reminder>')
    @app_commands.describe(reminder='For what you want to be reminded for')
    @app_commands.describe(duration='When you want to be reminded. Can be a @time timestamp, or durations (5h 30min)')
    @app_commands.describe(channel='A channel to send the reminder to. If not specified, it will be sent to your DMs')
    async def add(
        self,
        ctx: CustomContext,
        duration: commands.Greedy[utils.TimeConverter],
        channel: TextChannel | None,
        *,
        reminder: str
    ):
        """Add a reminder to be sent to you or a channel after a specified duration!"""

        time = timedelta()
        for d in duration:
            time += d
        if time == timedelta():
            raise utils.DoggieBotException('Invalid duration!', 'No duration was set!')

        dtime = datetime.now(tz=timezone.utc) + time

        if dtime < datetime.now(tz=timezone.utc):
            raise utils.DoggieBotException('Invalid duration!', 'Can\'t set a reminder in the past!')

        if channel and ctx.interaction and (not ctx.guild or not ctx.guild.owner_id):
            raise utils.DoggieBotException('Invalid option:', 'Can\'t specify a channel to send to when bot is installed as only an user app')

        if channel and ctx.guild:
            bot_perms = channel.permissions_for(ctx.guild.me)
            author_perms = channel.permissions_for(ctx.author)

            if channel.guild != ctx.guild or not (bot_perms.view_channel and bot_perms.send_messages) or not (author_perms.view_channel and author_perms.send_messages):
                raise utils.DoggieBotException('Missing Permissions', 'You or this bot don\'t have permissions to talk in that channel!')

        destination = channel or ctx.author

        rem = utils.Reminder(ctx.message.id, ctx.author, reminder, destination, dtime, self.bot)

        embed = utils.create_embed(
            ctx.author,
            title=f'Reminder added! (**ID**: {rem.id})',
            description=f'Reminder "{reminder}" has been added for {utils.user_friendly_dt(dtime)} to be sent to ' + (channel.mention if channel else 'you') + '!'
        )

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(liases=['reminders', 'list_reminders', 'listreminders', 'all', 'all_reminders'])
    async def list(self, ctx: CustomContext):
        """Shows your active reminders that you made!"""

        filtered_reminders = [reminder for reminder in self.bot.reminders.values()
                              if reminder is not None and reminder.user == ctx.author]

        if not filtered_reminders:
            raise utils.DoggieBotException('No reminders!', 'You don\'t have any reminders set yet, use the `/reminder add` command to add one!')

        view = ReminderList(owner=ctx.author, items=filtered_reminders, items_per_page=5)
        await ctx.send(view=view, ephemeral=True, **await view.get_page_contents())

    @commands.hybrid_command(aliases=['deletereminder', 'cancelreminder', 'del'])
    @app_commands.describe(reminder_id='The ID of the reminder that you want to cancel, can be seen in /reminders list')
    async def cancel(self, ctx: CustomContext, reminder_id: commands.Range[int, 1, 9999]):
        """Cancels and deletes a reminder using its ID!"""

        reminder = self.bot.reminders.get(reminder_id)

        if reminder is None or reminder.user != ctx.author:
            raise utils.DoggieBotException('Reminder not found!', 'A reminder with that ID wasn\'t found, or it is not your reminder!')

        reminder_str = escape_markdown(reminder.reminder)

        await reminder.remove()

        embed = utils.create_embed(
            ctx.author,
            title=f'Reminder successfully removed! (ID: {reminder_id})',
            description=f'Reminder "{reminder_str}" has been canceled and deleted!'
        )

        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ReminderCog(bot))
