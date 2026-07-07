import math
from typing import Any

import discord
from discord import Interaction, Member, User, ButtonStyle
from discord.ui import View, Button, Item
from discord.ext.commands import Paginator

from utils.classes import CustomBot

__all__ = [
    'PaginatedMenu',
    'CustomView',
    'PageView',
    'EntryMenu'
]


class CustomView(View):
    def __init__(self, owner: User | Member):
        self.owner = owner
        self.message = None
        super().__init__(timeout=6000)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        self.message = interaction.message

        if interaction.user != self.owner:
            await interaction.response.send_message(content='You didn\'t use this command!', ephemeral=True)
            return False

        return True

    async def on_timeout(self) -> None:
        self.disable_children()

        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    def disable_children(self) -> None:
        for child in self._children:
            setattr(child, 'disabled', True)

    async def on_error(self, interaction: Interaction[CustomBot], error: Exception, _: Item[Any], /) -> None:  # type: ignore
        await interaction.client.tree.on_error(interaction, error)


class PageView(CustomView):
    def __init__(self, owner: User):
        super().__init__(owner)
        self.current_index = 1

    async def get_page_contents(self) -> dict:
        raise NotImplementedError()

    async def update_page(self, interaction: Interaction):
        contents = await self.get_page_contents()
        self.update_button_state()
        await interaction.response.edit_message(view=self, **contents)

    @property
    def max_page(self) -> int:
        raise NotImplementedError()

    def remove_buttons_if_one_page(self):
        if self.max_page == 1:
            self.clear_items()

    def update_button_state(self):
        self.far_left.disabled = False
        self.left.disabled = False
        self.right.disabled = False
        self.far_right.disabled = False

        if self.current_index == 1:
            self.far_left.disabled = True
            self.left.disabled = True

        if self.current_index == self.max_page:
            self.right.disabled = True
            self.far_right.disabled = True

    @discord.ui.button(emoji='\U000023EA', style=ButtonStyle.blurple, disabled=True)
    async def far_left(self, interaction: Interaction, _: Button):
        self.current_index = 1
        await self.update_page(interaction)

    @discord.ui.button(emoji='\U000025C0', style=ButtonStyle.blurple, disabled=True)
    async def left(self, interaction: Interaction, _: Button):
        self.current_index -= 1
        self.current_index = max(self.current_index, 1)

        await self.update_page(interaction)

    @discord.ui.button(emoji='\U000023F9', style=ButtonStyle.red)
    async def stop_button(self, interaction: Interaction, _: Button):
        children = self.children
        for child in children:
            setattr(child, 'disabled', True)
        self._children = children

        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji='\U000025B6', style=ButtonStyle.blurple)
    async def right(self, interaction: Interaction, _: Button):
        self.current_index += 1
        self.current_index = min(self.current_index, self.max_page)

        await self.update_page(interaction)

    @discord.ui.button(emoji='\U000023E9', style=ButtonStyle.blurple)
    async def far_right(self, interaction: Interaction, _: Button):
        self.current_index = self.max_page
        await self.update_page(interaction)


class EntryMenu[T](PageView):
    def __init__(self, owner: User, items: list[T], items_per_page: int):
        super().__init__(owner)
        self.items = items
        self.items_per_page = items_per_page
        self.remove_buttons_if_one_page()

    async def get_page_contents(self) -> dict:
        raise NotImplementedError()

    def get_page_items(self) -> list[T]:
        return self.items[(self.current_index - 1) * self.items_per_page:self.current_index * self.items_per_page]

    @property
    def max_page(self) -> int:
        return math.ceil(len(self.items) / self.items_per_page) or 1


class PaginatedMenu[T](PageView):
    def __init__(self, owner: User, items: list[T], max_size: int = 750):
        super().__init__(owner)

        self.max_size = max_size
        self.paginator = self.get_paginator(items)
        self.items = items
        self.current_index = 1
        self.remove_buttons_if_one_page()

    def format_line(self, item: T) -> str:
        raise NotImplementedError()

    def get_paginator(self, items: list[T]) -> Paginator:
        paginator = Paginator(prefix=None, suffix=None, max_size=self.max_size)

        for item in items:
            paginator.add_line(self.format_line(item))

        return paginator

    async def get_page_contents(self) -> dict:
        raise NotImplementedError()

    @property
    def current_page(self) -> str:
        return self.paginator.pages[self.current_index - 1]

    @property
    def max_page(self) -> int:
        return len(self.paginator.pages)
