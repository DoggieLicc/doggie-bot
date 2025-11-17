import dataclasses
import inspect
import aiohttp
import logging

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional, Union, List, TypedDict, no_type_check

logger = logging.getLogger(__name__)

API_BASE_URL = 'https://api.unsplash.com/'
ORIENTATION_LITERAL = Literal['landscape', 'portrait', 'squarish']
CONTENT_FILTER_LITERAL = Literal['low', 'high']


def maybe_dt(string: Optional[str]):
    return datetime.fromisoformat(string.replace('Z', '+00:00')) if string else None


@dataclass(frozen=True)
class PhotoURLS:
    raw: str
    full: str
    regular: str
    thumb: str
    small: str
    small_s3: str


@dataclass(frozen=True)
class PhotoInterchange:
    name: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    exposure_time: Optional[str] = None
    aperture: Optional[float] = None
    focal_length: Optional[float] = None
    iso: Optional[int] = None


class PhotoLocationPosition(TypedDict):
    latitude: float
    longitude: float


@dataclass(frozen=True)
class PhotoLocation:
    title: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    position: Optional[PhotoLocationPosition] = None


@dataclass(frozen=True)
class PhotoLinks:
    self: str
    html: str
    download: str
    download_location: str


@dataclass(frozen=True)
class UserLinks:
    self: str
    html: str
    photos: str
    likes: str
    portfolio: str
    following: Optional[str] = None
    followers: Optional[str] = None


@dataclass(frozen=True)
class UserSocials:
    portfolio_url: str
    instagram_username: Optional[str] = None
    twitter_username: Optional[str] = None
    paypal_email: Optional[str] = None


@dataclass(frozen=True)
class UserProfileImage:
    small: str
    medium: str
    large: str


@dataclass(unsafe_hash=True)
class User:
    id: str

    username: str
    name: str
    first_name: str
    last_name: str
    portfolio_url: str

    total_likes: int
    total_collections: int
    total_photos: int

    accepted_tos: bool
    for_hire: bool

    updated_at: datetime
    links: UserLinks
    profile_image: UserProfileImage

    social: UserSocials

    bio: Optional[str] = None
    location: Optional[str] = None
    instagram_username: Optional[str] = None
    twitter_username: Optional[str] = None

    @classmethod
    def from_dict(cls, env):
        return cls(
            updated_at=maybe_dt(env.pop('updated_at')),
            links=UserLinks(**env.pop('links')),
            profile_image=UserProfileImage(**env.pop('profile_image')),
            social=UserSocials(**env.pop('social')),
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )


@no_type_check
@dataclass(unsafe_hash=True)
class Photo:
    id: str
    created_at: datetime
    updated_at: datetime
    promoted_at: Optional[datetime]
    width: int
    height: int
    color: int
    blur_hash: str
    likes: int
    current_user_collections: dict
    urls: PhotoURLS
    user: User
    links: PhotoLinks
    categories: List[str] = field(default_factory=list)

    description: Optional[str] = None
    alt_description: Optional[str] = None
    sponsorship: Optional[str] = None

    tags: Optional[dict] = None
    exif: Optional[PhotoInterchange] = None
    location: Optional[PhotoLocation] = None
    downloads: Optional[int] = None
    views: Optional[int] = None

    @classmethod
    def from_dict(cls, env):
        env.pop('promoted_at')
        return cls(
            created_at=maybe_dt(env.pop('created_at')),
            updated_at=maybe_dt(env.pop('updated_at')),
            promoted_at=None,
            color=int(env.pop('color').strip('#'), 16),
            urls=PhotoURLS(**env.pop('urls')),
            links=PhotoLinks(**env.pop('links')),
            exif=PhotoInterchange(**env.pop('exif')) if env.get('exif') else None,
            user=User.from_dict(env.pop('user')),
            location=PhotoLocation(**env.pop('location')) if env.get('location') else None,

            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )


class UnsplashException(Exception):
    def __init__(self, message):
        super().__init__('Error(s) when fetching from Unsplash API: ' + message)


@dataclass()
class Page:
    total: int
    total_pages: int
    results: List[Photo]


class Unsplash:
    def __init__(self, access_key: str):
        self.access_key = access_key
        self.headers = {
            'Accept-Version': 'v1',
            'Authorization': 'Client-ID ' + access_key
        }

    async def random(self, **kwargs) -> List[Photo]:
        """Gets random photos from the Unsplash API as a list of :class:`Photo`.
        All kwargs are optional.

        Keyword Arguments
        ----------
        collections: Optional[List[str]]
            Public collection ID(‘s) to filter selection.

        topics: Optional[List[str]]
            Public topic ID(‘s) to filter selection.

        username: Optional[str]
            Limit selection to a single user.

        query: Optional[str]
            Limit selection to photos matching a search term.

        orientation: Optional[ORIENTATION_LITERAL]
            Filter by photo orientation. (Valid values: "landscape", "portrait", "squarish")

        content_filter: Optional[CONTENT_FILTER_LITERAL]
            Limit results by content safety. (Default: "low"). Valid values are "low" and "high".

        count: Optional[int]
            The number of photos to return. (Default: 1; max: 30)

        Raises
        -----
        UnsplashException
            An error happened while fetching from Unsplash API.

        Returns
        ------
        List[Photo]

        Note
        ----
        You can’t use the collections or topics filtering with query parameters in the same request
        """

        data: Union[dict, list] = await self._request('photos/random', **kwargs)
        data = [data] if isinstance(data, dict) else data
        return [Photo.from_dict(d) for d in data]

    async def search(self, query: str, **kwargs) -> Page:
        """Searches the Unsplash API for photos with a query and returns it as a :class:`Page` object.
        All kwargs are optional

        Parameters
        ---------
        query: str
            The search terms

        Keyword Arguments
        ----------------
        page: Optional[int]
            Page number to retrieve. (Default: 1)

        per_page: Optional[int]
            Number of items per page. (Default: 10)

        order_by: Optional[str]
            How to sort the photos. (Default: "relevant"). Valid values are "latest" and "relevant".

        collections: Optional[List[str]]
            Collection ID(‘s) to narrow search.

        content_filter: Optional[CONTENT_FILTER_LITERAL]
            Limit results by content safety. (Default: "low"). Valid values are "low" and "high".

        color: Optional[str]
            Filter results by color. Valid values are: "black_and_white", "black", "white", "yellow", "orange", "red",
            "purple", "magenta", "green", "teal", and "blue".

        orientation: Optional[ORIENTATION_LITERAL]
            Filter by photo orientation. (Valid values: "landscape", "portrait", "squarish")

        Raises
        -----
        UnsplashException
            An error happened while fetching from Unsplash API

        Note
        ----
        The photo objects are missing `exif`, `location`, `downloads`, and `views` fields.

        """
        kwargs['query'] = query
        data = await self._request('search/photos', **kwargs)

        return Page(
            total=data.pop('total'),
            total_pages=data.pop('total_pages'),
            results=[Photo.from_dict(d) for d in data['results']]
        )

    async def _request(self, endpoint: str, *, method: str = 'get', **kwargs) -> Union[dict, list]:
        try:

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.request(method, API_BASE_URL + endpoint, params=kwargs) as response:
                    data: dict = await response.json()

                if not response.ok:
                    errors = data.get('errors', data.values())
                    raise UnsplashException(','.join(errors))

                return data

        except Exception as e:
            if isinstance(e, UnsplashException): raise
            raise UnsplashException(f'{type(e)}: {e}')
