from typing import TYPE_CHECKING

from discord import Interaction

__all__ = ['MyInteraction']

if TYPE_CHECKING:
    from utils.classes import CustomBot

    class MyInteraction(Interaction):
        client: CustomBot  # type: ignore

else:
    MyInteraction = Interaction
