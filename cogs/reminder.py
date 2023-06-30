import discord
import utils

from discord.ext import commands
from discord.ext.commands import Greedy

from datetime import datetime, timezone, timedelta
from typing import Optional, cast


class ReminderCog(commands.Cog, name="Reminder"):
    """Create and manage your reminders"""

    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @commands.command(aliases=['r', 'rm', 'remindme', 'reminder'],
                      usage='<duration> [channel] <reminder>')
    async def remind(
            self,
            ctx,
            durations: Greedy[utils.TimeConverter], channel: Optional[utils.MentionedTextChannel],
            *,
            reminder: str):
        """Add a reminder to be sent to you or a channel after a specified duration!
        You can specify a channel for the reminder to be sent to, otherwise it will be sent to your DMS

        **Examples**:
        *remind 10mins #general code discord bot*
        *remind 1hr 30m do stuff*"""

        channel: discord.TextChannel = cast(discord.TextChannel, channel)

        durations = [duration for duration in durations if duration]
        durations_set = set([duration.unit for duration in durations])

        if not durations:
            raise commands.BadArgument('The duration wasn\'t specified or it was invalid!')

        if len(durations) != len(durations_set):
            raise commands.BadArgument('There were duplicate units in the duration!')

        if channel:
            bot_perms = channel.permissions_for(ctx.guild.me)
            author_perms = channel.permissions_for(ctx.author)

            if channel.guild != ctx.guild or \
                    not (bot_perms.view_channel and bot_perms.send_messages) or \
                    not (author_perms.view_channel and author_perms.send_messages):
                embed = utils.create_embed(
                    ctx.author,
                    title='Missing Permissions!',
                    description='You or this bot don\'t have permissions to talk in that channel!',
                    color=discord.Color.red()
                )

                return await ctx.send(embed=embed)

        total_seconds = sum([t.seconds for t in durations])
        end_time = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)

        destination = channel or ctx.author

        rem = utils.Reminder(ctx.message.id, ctx.author, reminder, destination, end_time, self.bot)

        embed = utils.create_embed(
            ctx.author,
            title=f'Reminder added! (**ID**: {rem.id})',
            description=f'Reminder "{reminder}" has been added for ' + ', '.join(
                map(str, durations)) + ' to be sent to ' + (channel.mention if channel else 'you') + '!'
        )

        await ctx.send(embed=embed)

    @remind.error
    async def remind_error(self, ctx, error):

        embed = utils.create_embed(
            ctx.author,
            title='Error while making reminder!',
            color=discord.Color.red()
        )

        if isinstance(error, commands.BadArgument):
            embed.add_field(
                name='Invalid duration!',
                value=f'{error}\n'
                      f'Usage example: `remind 5hr 30min make toast`'
            )

        if isinstance(error, commands.MissingRequiredArgument):
            embed.add_field(
                name='Missing reminder!',
                value='You need to specify a reminder!'
            )

        await ctx.send(embed=embed)

    @commands.command(aliases=['list', 'list_reminders', 'listreminders', 'all', 'all_reminders'])
    async def reminders(self, ctx):
        """Shows your active reminders that you made!
        It will show what the reminders are, when they end, and their ID"""

        filtered_reminders = [reminder for reminder in self.bot.reminders.values()
                              if reminder is not None and reminder.user == ctx.author]

        if not filtered_reminders:
            embed = utils.create_embed(
                ctx.author,
                title='No reminders!',
                description='You don\'t have any reminders set yet, '
                            'use the `reminder` command to add one!',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        menu = utils.CustomMenu(source=utils.ReminderList(filtered_reminders, per_page=5), clear_reactions_after=True)
        await menu.start(ctx)

    @commands.command(aliases=['deletereminder', 'cancelreminder', 'del'])
    async def cancel(self, ctx, reminder_id: int):
        """Cancels and deletes a reminder using its ID!
        You can get the IDs for your reminders by using the `reminders` command"""

        reminder = self.bot.reminders.get(reminder_id)

        if reminder is None:
            raise commands.BadArgument('A reminder with that ID wasn\'t found!')

        if reminder.user != ctx.author:
            embed = utils.create_embed(
                ctx.author,
                title='You didn\'t make this reminder!',
                description='Someone else made this reminder, so you can\'t delete it!',
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        reminder_str = discord.utils.escape_markdown(reminder.reminder)

        await reminder.remove()

        embed = utils.create_embed(
            ctx.author,
            title=f'Reminder successfully removed! (ID: {reminder_id})',
            description=f'Reminder "{reminder_str}" has been canceled and deleted!'
        )

        await ctx.send(embed=embed)

    @cancel.error
    async def delete_error(self, ctx, error):

        embed = utils.create_embed(
            ctx.author,
            title='Error while deleting reminder!',
            color=discord.Color.red()
        )

        if isinstance(error, commands.MissingRequiredArgument):
            embed.add_field(
                name='No reminder ID specified!',
                value='You need to specify a reminder ID to delete!\n'
                      'Use the command `reminders` to see your active reminders!'
            )

        if isinstance(error, commands.BadArgument):
            embed.add_field(
                name='Reminder not found!',
                value=f'{error}\n'
                      f'Use the command `reminders` to see your active reminders!'
            )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ReminderCog(bot))
