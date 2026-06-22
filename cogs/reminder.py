from datetime import datetime, timezone
from typing import cast

import discord
from discord.ext import commands
from discord import app_commands, Interaction, TextChannel
from discord.app_commands import Transform, Range
import utils

class ReminderList(utils.EntryMenu):
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
                        f'**Destination:** {channel.mention if channel else "Your DMS!"}\n',
                inline=False
            )

        return {"embed": embed}

class ReminderCog(commands.GroupCog, name="reminder"):
    """Create and manage your reminders"""

    def __init__(self, bot: utils.CustomBot):
        self.bot: utils.CustomBot = bot

    @app_commands.command()
    @app_commands.describe(reminder='For what you want to be reminded for')
    @app_commands.describe(time='When you want to be reminded. Can be a Discord-style timestamp, or durations (5h 30min)')
    @app_commands.describe(channel='A channel to send the reminder to. If not specified, it will be sent to your DMs')
    async def add(
        self,
        interaction: Interaction,
        reminder: str,
        time: Transform[datetime, utils.TimeTransformer],
        channel: TextChannel | None
    ):
        """Add a reminder to be sent to you or a channel after a specified duration!"""

        channel: discord.TextChannel = cast(discord.TextChannel, channel)

        if time < datetime.now(tz=timezone.utc):
            embed = utils.create_embed(
                interaction.user,
                title='Invalid time!',
                description='Can\'t set a reminder in the past!',
                color=discord.Color.red()
            )

            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if channel:
            bot_perms = channel.permissions_for(interaction.guild.me)
            author_perms = channel.permissions_for(interaction.user)

            if channel.guild != interaction.guild or \
                    not (bot_perms.view_channel and bot_perms.send_messages) or \
                    not (author_perms.view_channel and author_perms.send_messages):
                embed = utils.create_embed(
                    interaction.user,
                    title='Missing Permissions!',
                    description='You or this bot don\'t have permissions to talk in that channel!',
                    color=discord.Color.red()
                )

                return await interaction.response.send_message(embed=embed, ephemeral=True)

        destination = channel or interaction.user

        rem = utils.Reminder(interaction.id, interaction.user, reminder, destination, time, self.bot)

        embed = utils.create_embed(
            interaction.user,
            title=f'Reminder added! (**ID**: {rem.id})',
            description=f'Reminder "{reminder}" has been added for {utils.user_friendly_dt(time)} to be sent to ' + (channel.mention if channel else 'you') + '!'
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command()
    async def list(self, interaction: Interaction):
        """Shows your active reminders that you made!"""

        filtered_reminders = [reminder for reminder in self.bot.reminders.values()
                              if reminder is not None and reminder.user == interaction.user]

        if not filtered_reminders:
            embed = utils.create_embed(
                interaction.user,
                title='No reminders!',
                description='You don\'t have any reminders set yet, '
                            'use the `reminder` command to add one!',
                color=discord.Color.red()
            )

            return await interaction.response.send_message(embed=embed, ephemeral=True)

        menu = ReminderList(owner=interaction.user, items=filtered_reminders, items_per_page=10)
        contents = await menu.get_page_contents()
        await interaction.response.send_message(view=menu, ephemeral=True, **contents)

    @app_commands.command()
    @app_commands.describe(reminder_id='The ID of the reminder that you want to cancel, can be seen in /reminders list')
    async def cancel(self, interaction: Interaction, reminder_id: Range[int, 1, 9999]):
        """Cancels and deletes a reminder using its ID!"""

        reminder = self.bot.reminders.get(reminder_id)

        if reminder is None:
            raise utils.DoggieBotException('A reminder with that ID wasn\'t found!')

        if reminder.user != interaction.user:
            embed = utils.create_embed(
                interaction.user,
                title='You didn\'t make this reminder!',
                description='Someone else made this reminder, so you can\'t delete it!',
                color=discord.Color.red()
            )

            return await interaction.response.send_message(embed=embed, ephemeral=True)

        reminder_str = discord.utils.escape_markdown(reminder.reminder)

        await reminder.remove()

        embed = utils.create_embed(
            interaction.user,
            title=f'Reminder successfully removed! (ID: {reminder_id})',
            description=f'Reminder "{reminder_str}" has been canceled and deleted!'
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ReminderCog(bot))
