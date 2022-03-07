import discord
import asyncio

from discord import TextChannel, ChannelType, User
from discord.ext import menus

from dataclasses import dataclass, field
from datetime import datetime
from typing import Union, Any

from utils.funcs import guess_user_nitro_status, user_friendly_dt, create_embed, fix_url

__all__ = [
    'CustomMenu',
    'Emotes',
    'ReminderList',
    'Reminder',
]


class CustomMenu(menus.MenuPages):
    @menus.button('\N{WASTEBASKET}\ufe0f', position=menus.Last(3))
    async def do_trash(self, _):
        self.stop()
        await self.message.delete()

    def stop(self):
        self.call_end_event()
        super().stop()

    async def finalize(self, timed_out):
        self.call_end_event()

    def call_end_event(self):
        self.bot.dispatch('finalize_menu', self.ctx)


class Emotes:
    # Emotes available in https://discord.gg/Uk6fg39cWn

    bot_tag = '<:botTag:941816165221679144>'
    discord = '<:discord:941816357949960222>'
    owner = '<:owner:941816499960688650>'
    slowmode = '<:slowmode:941816507342651462>'
    check = '<:check:941816359090806804>'
    xmark = '<:xmark:941816519300616213>'
    role = '<:role:941816504318558208>'
    text = '<:channel:941816354393178172>'
    nsfw = '<:channel_nsfw:941816355995410432>'
    voice = '<:voice:941816520529571860>'
    emoji = '<:emoji_ghost:941816360059687043>'
    store = '<:store_tag:941816513097240656>'
    invite = '<:invite:941816364132368435>'
    partner = '<:partner:941816501248327700>'
    hypesquad = '<:hypesquad:941816362798559232>'
    nitro = '<:nitro:941816498681446460>'
    staff = '<:staff:941816508957483109>'
    balance = '<:balance:941816154681405481>'
    bravery = '<:bravery:941816350916096050>'
    brilliance = '<:brilliance:941816351721422869>'
    bughunter = '<:bughunter:941816353252323448>'
    supporter = '<:supporter:941816514506530856>'

    booster = '<:booster:941816158863102054>'
    booster2 = '<:booster2:941816160985440297>'
    booster3 = '<:booster3:941816161958527017>'
    booster4 = '<:booster4:941816163795603506>'
    verified = '<:verified:941816517710979162>'

    partnernew = '<:partnernew:941816502766690334>'
    members = '<:members:941816367466831983>'
    stage = '<:stagechannel:941816511692156928>'
    stafftools = '<:stafftools:941816510333202452>'
    thread = '<:threadchannel:941816516033269811>'
    mention = '<:mention:941816367466831983>'
    rules = '<:rules:941816505849491586>'
    news = '<:news:941816373062029332>'

    ban_create = '<:bancreate:941816156191346759>'
    ban_delete = '<:bandelete:941816157567070298>'
    member_leave = '<:memberleave:941816365772341298>'
    message_delete = '<:messagedelete:941816371401064490>'
    emote_create = '<:emotecreate:941816361561243700>'

    @staticmethod
    def channel(chann):
        if chann.type == ChannelType.text:
            if isinstance(chann, TextChannel):
                if chann.is_nsfw():
                    return Emotes.nsfw
            return Emotes.text
        if chann.type == ChannelType.news:
            return Emotes.news
        if chann.type == ChannelType.voice:
            return Emotes.voice
        if chann.type == ChannelType.store:
            return Emotes.store
        if chann.type == ChannelType.category:
            return ""
        if str(chann.type).endswith('thread'):
            return Emotes.thread
        if chann.type == ChannelType.stage_voice:
            return Emotes.stage

    @staticmethod
    def badges(user):
        badges = []
        flags = [name for name, value in dict.fromkeys(iter(user.public_flags)) if value]

        if user.bot:
            badges.append(Emotes.bot_tag)
        if "staff" in flags:
            badges.append(Emotes.staff)
        if "partner" in flags:
            badges.append(Emotes.partner)
        if "hypesquad" in flags:
            badges.append(Emotes.hypesquad)
        if "bug_hunter" in flags:
            badges.append(Emotes.bughunter)
        if "early_supporter" in flags:
            badges.append(Emotes.supporter)
        if "hypesquad_briliance" in flags:
            badges.append(Emotes.brilliance)
        if "hypesquad_bravery" in flags:
            badges.append(Emotes.bravery)
        if "hypesquad_balance" in flags:
            badges.append(Emotes.balance)
        if "hypesquad_brilliance" in flags:
            badges.append(Emotes.brilliance)
        if "verified_bot" in flags:
            badges.append(Emotes.verified)
        if "verified_bot_developer" in flags:
            badges.append(Emotes.verified)

        if guess_user_nitro_status(user):
            badges.append(Emotes.nitro)

        return " ".join(badges)


class ReminderList(menus.ListPageSource):
    async def format_page(self, menu, entries):
        index = menu.current_page + 1
        embed = create_embed(menu.ctx.author, title=f'Showing active reminders for {menu.ctx.author} '
                                                    f'({index}/{self._max_pages}):')

        for reminder in entries:
            channel = reminder.destination if isinstance(reminder.destination, TextChannel) else None

            embed.add_field(name=f'ID: {reminder.id}',
                            value=f'**Reminder:** {str(reminder)[:1100]}\n'
                                  f'**Ends at:** {user_friendly_dt(reminder.end_time)}\n'
                                  f'**Destination:** {channel.mention if channel else "Your DMS!"}\n',
                            inline=False)
        return embed


@dataclass
class Reminder:
    message_id: int
    user: User
    reminder: str
    destination: Union[User, TextChannel]
    end_time: datetime
    bot: Any
    id: int = field(init=False)
    task: asyncio.Future = field(init=False)

    def __post_init__(self):
        self.id = len(self.bot.reminders) + 1
        self.task = asyncio.ensure_future(self.send_reminder())
        self.bot.reminders[self.id] = self

    async def send_reminder(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute(
                'INSERT OR IGNORE INTO reminders VALUES (?, ?, ?, ?, ?)',
                (self.message_id,
                 self.user.id,
                 self.reminder,
                 int(self.end_time.timestamp()),
                 self.destination.id)
            )

        await self.bot.db.commit()
        await discord.utils.sleep_until(self.end_time)

        embed = discord.Embed(
            title='Reminder!',
            description=self.reminder,
            color=discord.Color.green()
        )

        if isinstance(self.destination, TextChannel):
            embed.set_footer(
                icon_url=fix_url(self.user.display_avatar),
                text=f'Reminder sent by {self.user}'
            )

        else:
            embed.set_footer(
                icon_url=fix_url(self.user.display_avatar),
                text=f'This reminder is sent by you!'
            )

        try:
            await self.destination.send(
                f"**Hey {self.user.mention},**" if isinstance(self.destination, TextChannel) else None,
                embed=embed
            )

        except (discord.Forbidden, discord.HTTPException):
            pass

        await self.remove()

    async def remove(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute('DELETE FROM reminders WHERE id = (?)', (self.message_id,))
        await self.bot.db.commit()

        self.bot.reminders[self.id] = None
        self.task.cancel()

    def __str__(self):
        return self.reminder
