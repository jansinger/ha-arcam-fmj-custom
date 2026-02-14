"""iTunes artwork lookup with caching for Arcam FMJ integration."""

from __future__ import annotations

import logging
import time

from aiohttp import ClientError, ClientSession

_LOGGER = logging.getLogger(__name__)

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
ARTWORK_SIZE = "600x600bb"
CACHE_TTL = 86400  # 24 hours
NEGATIVE_CACHE_TTL = 3600  # 1 hour for misses
MIN_REQUEST_INTERVAL = 3.0  # seconds between HTTP requests


class ArtworkLookup:
    """Lookup and cache artwork URLs from iTunes Search API."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize with an aiohttp session."""
        self._session = session
        self._cache: dict[tuple[str, str], tuple[str | None, float]] = {}
        self._last_request_time: float = 0.0

    async def get_album_artwork(self, artist: str, album: str) -> str | None:
        """Get artwork URL for a music album."""
        cache_key = (artist.lower().strip(), album.lower().strip())
        cached = self._check_cache(cache_key)
        if cached is not _MISS:
            return cached

        if not self._check_rate_limit():
            return None

        url = await self._do_search(
            f"{artist} {album}", entity="album", media="music"
        )
        self._cache[cache_key] = (url, time.monotonic())
        return url

    async def get_podcast_artwork(self, title: str) -> str | None:
        """Get artwork URL for a podcast."""
        cache_key = ("__podcast__", title.lower().strip())
        cached = self._check_cache(cache_key)
        if cached is not _MISS:
            return cached

        if not self._check_rate_limit():
            return None

        url = await self._do_search(title, entity="podcast")
        self._cache[cache_key] = (url, time.monotonic())
        return url

    def _check_cache(self, key: tuple[str, str]) -> str | None | object:
        """Check cache for a key. Returns _MISS sentinel if not cached/expired."""
        if key in self._cache:
            url, timestamp = self._cache[key]
            ttl = CACHE_TTL if url else NEGATIVE_CACHE_TTL
            if time.monotonic() - timestamp < ttl:
                return url
        return _MISS

    def _check_rate_limit(self) -> bool:
        """Return True if a request is allowed, False if rate-limited."""
        if time.monotonic() - self._last_request_time < MIN_REQUEST_INTERVAL:
            _LOGGER.debug("Rate limited, skipping iTunes lookup")
            return False
        return True

    async def _do_search(self, term: str, **params: str) -> str | None:
        """Execute an iTunes search and extract artwork URL."""
        self._last_request_time = time.monotonic()
        try:
            search_params = {"term": term, "limit": "1", **params}
            async with self._session.get(
                ITUNES_SEARCH_URL, params=search_params, timeout=10
            ) as resp:
                if resp.status != 200:
                    _LOGGER.debug(
                        "iTunes search returned %s for '%s'", resp.status, term
                    )
                    return None
                data = await resp.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("iTunes search failed for '%s': %s", term, err)
            return None

        results = data.get("results", [])
        if not results:
            _LOGGER.debug("No iTunes results for '%s'", term)
            return None

        artwork_url = results[0].get("artworkUrl100") or results[0].get(
            "artworkUrl600"
        )
        if artwork_url and "100x100bb" in artwork_url:
            artwork_url = artwork_url.replace("100x100bb", ARTWORK_SIZE)
        return artwork_url


_MISS = object()  # sentinel for cache miss
