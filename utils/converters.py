import re

from discord import app_commands

from dataclasses import dataclass


__all__ = [
    'TimeConverter',
    'Time'
]

ID_REGEX = re.compile(r'([0-9]{15,20})$')


@dataclass(frozen=True)
class TimeUnit:
    name: str
    seconds: int


@dataclass(frozen=True)
class Time:
    unit_amount: int
    unit_name: str
    unit: TimeUnit
    seconds: int

    def __str__(self):
        return f'{self.unit_amount} {self.unit_name}'


class TimeConverter(app_commands.Transformer):
    @staticmethod
    def get_unit(text: str):
        text = text.lower()

        if text in ['s', 'sec', 'secs', 'second', 'seconds']:
            return TimeUnit('second', 1)
        if text in ['m', 'min', 'mins', 'minute', 'minutes']:
            return TimeUnit('minute', 60)
        if text in ['h', 'hr', 'hrs', 'hour', 'hours']:
            return TimeUnit('hour', 3600)
        if text in ['d', 'day', 'days']:
            return TimeUnit('day', 86_400)
        if text in ['w', 'wk', 'wks', 'week', 'weeks']:
            return TimeUnit('week', 604_800)
        if text in ['mo', 'mos', 'month', 'months']:
            return TimeUnit('month', 2_592_000)
        if text in ['y', 'yr', 'yrs', 'year', 'years']:
            return TimeUnit('year', 31_536_000)
        return None

    @classmethod
    async def convert(cls, _, argument: str):

        argument = argument.replace(',', '')

        if argument.lower() in ['in', 'me']: return None

        try:
            amount, unit = [re.findall(r'(\d+)(\w+)', argument)[0]][0]

            if amount == 0:
                raise app_commands.AppCommandError('Amount can\'t be zero')

            unit = cls.get_unit(unit)
            unit_correct_name = unit.name if amount == '1' else unit.name + 's'
            seconds = unit.seconds * int(amount)
        except Exception:
            raise app_commands.AppCommandError()

        return Time(amount, unit_correct_name, unit, seconds)
