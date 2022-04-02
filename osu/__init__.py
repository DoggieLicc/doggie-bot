import functools
import inspect
import aiohttp

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Literal, Union, Optional, List


BASE_URL = 'https://osu.ppy.sh/api/v2/'


def maybe_dt(string: Optional[str]):
    return datetime.fromisoformat(string) if string else None


def check_access_key(func):
    @functools.wraps(func)
    async def wrapped(self, *args, **kwargs):
        if not self._access_token or datetime.now(timezone.utc) > self._access_token.expires_at:
            await self._fetch_access_token()
        return await func(self, *args, **kwargs)

    return wrapped


class OsuApi:
    def __init__(self, client_id: int, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: Optional[AccessToken] = None

        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    async def _fetch_access_token(self):
        access_token = await self._request(
            url='https://osu.ppy.sh/oauth/token',
            method='post',
            json={
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'client_credentials',
                'scope': 'public'
            }
        )

        self._access_token = AccessToken(
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=access_token['expires_in']),
            **access_token
        )

        self.headers['Authorization'] = 'Bearer ' + self._access_token.access_token

    @check_access_key
    async def fetch_user(
            self,
            user: Union[int, str],
            mode: Optional[Literal['fruits', 'mania', 'osu', 'taiko']] = None,
            key: Optional[Literal['id', 'username']] = None
    ) -> 'User':
        """Fetches an osu! account with statistics for a gamemode.

        Arguments
        --------
        user: Union[int, str]
            The username or user id of the user

        mode: Optional[Literal['fruits', 'mania', 'osu', 'taiko']]
            The gamemode to get statistics for

        key: Optional[Literal['id', 'user-name']]
            Can be either id or username to limit lookup by their respective type. Passing empty or invalid value will
            result in id lookup followed by username lookup if not found

        Raises
        -----
        OsuApiException
            A problem happened while fetching from osu!api

        Returns
        ------
        User
        """

        data = await self._request(
            BASE_URL + f'users/{user}/{mode or ""}',
            params={'key': key or ''}
        )

        return User.from_dict(data)

    @check_access_key
    async def lookup_beatmap(
            self,
            *,
            checksum: Optional[str] = None,
            filename: Optional[str] = None,
            beatmap_id: Optional[int] = None
    ) -> 'Beatmap':
        """Looks up an osu! beatmap using it's id, filename, or checksum

        Arguments
        --------
        checksum: Optional[str]
            A beatmap checksum

        filename: Optional[str]
            A beatmap filename

        beatmap_id: Optional[int]
            A beatmap id

        Raises
        -----
        OsuApiException
            A problem happened while fetching from osu!api

        Returns
        ------
        Beatmap
        """

        data = await self._request(
            url=BASE_URL + 'beatmaps/lookup',
            params={
                'checksum': checksum or '',
                'filename': filename or '',
                'id': beatmap_id or ''
            }
        )

        return Beatmap.from_dict(data)

    async def _request(self, url: str, method='get', **kwargs) -> Union[dict, list]:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.request(method, url, **kwargs) as response:
                    data: dict = await response.json()

                if not response.ok:
                    raise OsuApiException(repr(data))

                return data

        except Exception as e:
            if isinstance(e, OsuApiException): raise
            raise OsuApiException(f'{type(e)}: {e}')


class OsuApiException(Exception):
    def __init__(self, message):
        super().__init__('Error(s) when fetching from osu!api: ' + message)


@dataclass(frozen=True)
class AccessToken:
    token_type: Literal['Bearer']
    expires_in: int
    access_token: str
    expires_at: datetime


@dataclass(frozen=True)
class GradeCounts:
    a: int
    s: int
    sh: int
    ss: int
    ssh: int


@dataclass(frozen=True)
class UserLevel:
    current: int
    progress: int


@dataclass(frozen=True)
class UserStatistics:
    grade_counts: GradeCounts
    level: UserLevel

    hit_accuracy: float
    is_ranked: bool
    maximum_combo: int
    play_count: int
    pp: int
    global_rank: int
    ranked_score: int
    total_hits: int
    total_score: int

    @classmethod
    def from_dict(cls, env):
        return cls(
            grade_counts=GradeCounts(**env.pop('grade_counts')),
            level=UserLevel(**env.pop('level')),
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )


@dataclass(frozen=True)
class User:
    avatar_url: str
    cover_url: str
    country_code: str
    username: str
    id: int

    is_active: bool
    is_bot: bool
    is_deleted: bool
    is_online: bool
    is_supporter: bool
    has_supported: bool

    last_visit: Optional[datetime]
    join_date: datetime

    statistics: UserStatistics

    @classmethod
    def from_dict(cls, env):
        last_visit = env.pop('last_visit')
        return cls(
            statistics=UserStatistics.from_dict(env.pop('statistics')),
            last_visit=datetime.fromisoformat(last_visit) if last_visit else None,
            join_date=datetime.fromisoformat(env.pop('join_date')),
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )


class BeatmapRankedStatus(Enum):
    GRAVEYARD = -2
    WIP = -1
    PENDING = 0
    RANKED = 1
    APPROVED = 2
    QUALIFIED = 3
    LOVED = 4


class BeatmapGamemode(Enum):
    CATCH = 'fruits'
    MANIA = 'mania'
    STANDARD = 'osu'
    TAIKO = 'taiko'


@dataclass(frozen=True)
class BeatmapSet:
    artist: str
    covers: dict
    creator: str
    favourite_count: int
    id: int
    nsfw: bool
    play_count: int
    preview_url: str
    source: str
    status: str
    title: str
    user_id: int
    video: str

    submitted_date: datetime

    ranked_date: Optional[datetime] = None
    beatmaps: Optional[List['Beatmap']] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    language: Optional[str] = None

    @classmethod
    def from_dict(cls, env):
        return cls(
            submitted_date=maybe_dt(env.pop('submitted_date')),
            ranked_date=maybe_dt(env.pop('ranked_date')),
            beatmaps=[Beatmap.from_dict(beatmap) for beatmap in env.pop('beatmaps')] if env.get('beatmaps') else None,
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )


@dataclass(frozen=True)
class Beatmap:
    id: int
    beatmapset_id: int
    url: str
    total_length: int
    difficulty_rating: float
    bpm: float

    last_updated: datetime
    ranked: BeatmapRankedStatus
    mode: BeatmapGamemode

    count_circles: int
    count_sliders: int
    count_spinners: int

    ar: float
    cs: float
    drain: float
    accuracy: float

    passcount: int
    playcount: int

    failtimes: Optional[dict] = None
    max_combo: Optional[int] = None

    beatmapset: Optional[BeatmapSet] = None

    @classmethod
    def from_dict(cls, env):
        return cls(
            last_updated=maybe_dt(env.pop('last_updated')),
            ranked=BeatmapRankedStatus(env.pop('ranked')),
            mode=BeatmapGamemode(env.pop('mode')),
            beatmapset=BeatmapSet.from_dict(env.pop('beatmapset')) if env.get('beatmapset') else None,
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )
