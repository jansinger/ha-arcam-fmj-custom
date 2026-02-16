"""Arcam media player."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import functools
import logging
from typing import Any

from arcam.fmj import ConnectionFailed, SourceCodes
from arcam.fmj.state import State

from homeassistant.components.media_player import (
    BrowseError,
    BrowseMedia,
    MediaClass,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcamFmjConfigEntry
from .artwork import ArtworkLookup
from .const import DOMAIN, EVENT_TURN_ON, SIGNAL_CLIENT_DATA
from .entity import ArcamFmjEntity

_LOGGER = logging.getLogger(__name__)

NETWORK_SOURCES = {SourceCodes.NET, SourceCodes.USB, SourceCodes.BT, SourceCodes.NET_USB}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ArcamFmjConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the configuration entry."""
    data = config_entry.runtime_data
    uuid = config_entry.unique_id or config_entry.entry_id

    async_add_entities(
        [
            ArcamFmj(data.device_name, data.state_zone1, uuid, data.artwork),
            ArcamFmj(data.device_name, data.state_zone2, uuid, data.artwork),
        ],
    )


def convert_exception[**_P, _R](
    func: Callable[_P, Coroutine[Any, Any, _R]],
) -> Callable[_P, Coroutine[Any, Any, _R]]:
    """Return decorator to convert a connection error into a home assistant error."""

    @functools.wraps(func)
    async def _convert_exception(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return await func(*args, **kwargs)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                f"Connection failed to device during {func.__name__}"
            ) from exception

    return _convert_exception


class ArcamFmj(ArcamFmjEntity, MediaPlayerEntity):
    """Representation of a media device."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_media_image_remotely_accessible = True

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
        artwork: ArtworkLookup,
    ) -> None:
        """Initialize device."""
        super().__init__(device_name, state, uuid)
        self._artwork = artwork
        self._artwork_url: str | None = None
        self._artwork_key: tuple[str, str] | None = None
        self._attr_name = f"Zone {state.zn}"
        self._attr_supported_features = (
            MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.BROWSE_MEDIA
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.TURN_ON
        )
        if state.zn == 1:
            self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOUND_MODE
        self._attr_unique_id = f"{uuid}-{state.zn}"
        self._attr_entity_registry_enabled_default = state.zn == 1

    async def async_added_to_hass(self) -> None:
        """Register artwork lookup on data updates."""
        await super().async_added_to_hass()

        @callback
        def _check_artwork(host: str) -> None:
            if host == self._state.client.host:
                self._schedule_artwork_lookup()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CLIENT_DATA, _check_artwork
            )
        )

    @callback
    def _schedule_artwork_lookup(self) -> None:
        """Schedule async artwork lookup if metadata changed."""
        source = self._state.get_source()
        if source not in NETWORK_SOURCES:
            self._artwork_url = None
            self._artwork_key = None
            return

        info = self._state.get_now_playing_info()
        if not info:
            self._artwork_url = None
            self._artwork_key = None
            return

        artist = info.artist or ""
        album = info.album or ""
        title = info.title or ""

        if artist and album:
            key = (artist, album)
        elif title:
            key = ("__podcast__", title)
        else:
            self._artwork_url = None
            self._artwork_key = None
            return

        if key == self._artwork_key:
            return

        self._artwork_key = key
        self._artwork_url = None
        self.hass.async_create_task(
            self._async_fetch_artwork(artist, album, title)
        )

    async def _async_fetch_artwork(
        self, artist: str, album: str, title: str
    ) -> None:
        """Fetch artwork from iTunes (with companion fallback) and update state."""
        try:
            if artist and album:
                url = await self._artwork.get_album_artwork(artist, album)
            else:
                url = await self._artwork.get_podcast_artwork(title)
        except Exception:
            _LOGGER.debug("Artwork lookup failed", exc_info=True)
            url = None

        if not url:
            url = self._find_companion_artwork()

        self._artwork_url = url
        self.async_write_ha_state()

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the device."""
        if self._state.get_power() is True:
            return MediaPlayerState.ON
        return MediaPlayerState.OFF

    @convert_exception
    async def async_mute_volume(self, mute: bool) -> None:
        """Send mute command."""
        await self._state.set_mute(mute)
        self.async_write_ha_state()

    @convert_exception
    async def async_select_source(self, source: str) -> None:
        """Select a specific source."""
        try:
            value = SourceCodes[source]
        except KeyError:
            _LOGGER.error("Unsupported source %s", source)
            return

        await self._state.set_source(value)
        self.async_write_ha_state()

    @convert_exception
    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select a specific sound mode."""
        try:
            await self._state.set_decode_mode(sound_mode)
        except (KeyError, ValueError) as exception:
            raise HomeAssistantError(
                f"Unsupported sound_mode {sound_mode}"
            ) from exception

        self.async_write_ha_state()

    @convert_exception
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self._state.set_volume(round(volume * 99.0))
        self.async_write_ha_state()

    @convert_exception
    async def async_volume_up(self) -> None:
        """Turn volume up for media player."""
        await self._state.inc_volume()
        self.async_write_ha_state()

    @convert_exception
    async def async_volume_down(self) -> None:
        """Turn volume down for media player."""
        await self._state.dec_volume()
        self.async_write_ha_state()

    @convert_exception
    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        if self._state.get_power() is not None:
            _LOGGER.debug("Turning on device using connection")
            await self._state.set_power(True)
        else:
            _LOGGER.debug("Firing event to turn on device")
            self.hass.bus.async_fire(EVENT_TURN_ON, {ATTR_ENTITY_ID: self.entity_id})

    @convert_exception
    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self._state.set_power(False)
        self.async_write_ha_state()

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the websocket media browsing helper."""
        if media_content_id not in (None, "root"):
            raise BrowseError(
                f"Media not found: {media_content_type} / {media_content_id}"
            )

        presets = self._state.get_preset_details()

        radio = [
            BrowseMedia(
                title=preset.name,
                media_class=MediaClass.MUSIC,
                media_content_id=f"preset:{preset.index}",
                media_content_type=MediaType.MUSIC,
                can_play=True,
                can_expand=False,
            )
            for preset in presets.values()
        ]

        return BrowseMedia(
            title="Arcam FMJ Receiver",
            media_class=MediaClass.DIRECTORY,
            media_content_id="root",
            media_content_type="library",
            can_play=False,
            can_expand=True,
            children=radio,
        )

    @convert_exception
    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play media."""
        if media_id.startswith("preset:"):
            preset = int(media_id[7:])
            await self._state.set_tuner_preset(preset)
        else:
            _LOGGER.error("Media %s is not supported", media_id)
            return

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        if (value := self._state.get_source()) is None:
            return None
        return value.name

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        return [x.name for x in self._state.get_source_list()]

    @property
    def sound_mode(self) -> str | None:
        """Name of the current sound mode."""
        if (value := self._state.get_decode_mode()) is None:
            return None
        return value.name

    @property
    def sound_mode_list(self) -> list[str] | None:
        """List of available sound modes."""
        if (values := self._state.get_decode_modes()) is None:
            return None
        return [x.name for x in values]

    @property
    def is_volume_muted(self) -> bool | None:
        """Boolean if volume is currently muted."""
        if (value := self._state.get_mute()) is None:
            return None
        return value

    @property
    def volume_level(self) -> float | None:
        """Volume level of device."""
        if (value := self._state.get_volume()) is None:
            return None
        return value / 99.0

    @property
    def media_content_type(self) -> MediaType | None:
        """Content type of current playing media."""
        source = self._state.get_source()
        if source in (SourceCodes.DAB, SourceCodes.FM):
            return MediaType.MUSIC
        if source in NETWORK_SOURCES:
            info = self._state.get_now_playing_info()
            if info and info.title:
                return MediaType.MUSIC
        return None

    @property
    def media_content_id(self) -> str | None:
        """Content type of current playing media."""
        source = self._state.get_source()
        if source in (SourceCodes.DAB, SourceCodes.FM):
            if preset := self._state.get_tuner_preset():
                value = f"preset:{preset}"
            else:
                value = None
        else:
            value = None

        return value

    @property
    def media_channel(self) -> str | None:
        """Channel currently playing."""
        source = self._state.get_source()
        if source == SourceCodes.DAB:
            value = self._state.get_dab_station()
        elif source == SourceCodes.FM:
            value = self._state.get_rds_information()
        else:
            value = None
        return value

    @property
    def media_artist(self) -> str | None:
        """Artist of current playing media, music track only."""
        source = self._state.get_source()
        if source in NETWORK_SOURCES:
            info = self._state.get_now_playing_info()
            if info and info.artist:
                return info.artist
        if source == SourceCodes.DAB:
            return self._state.get_dls_pdt()
        return None

    @property
    def media_album_name(self) -> str | None:
        """Album name of current playing media."""
        source = self._state.get_source()
        if source in NETWORK_SOURCES:
            info = self._state.get_now_playing_info()
            if info and info.album:
                return info.album
        return None

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""
        if (source := self._state.get_source()) is None:
            return None

        if source in NETWORK_SOURCES:
            info = self._state.get_now_playing_info()
            if info and info.title:
                return info.title

        if channel := self.media_channel:
            return f"{source.name} - {channel}"
        return source.name

    @property
    def media_image_url(self) -> str | None:
        """Return cached artwork URL (resolved asynchronously)."""
        if self._state.get_source() not in NETWORK_SOURCES:
            return None
        return self._artwork_url

    def _find_companion_artwork(self) -> str | None:
        """Find entity_picture from a companion media player on the same host."""
        if not self.hass:
            return None

        host = self._state.client.host
        registry = er.async_get(self.hass)

        for state in self.hass.states.async_all("media_player"):
            picture = state.attributes.get("entity_picture")
            if not picture:
                continue

            entry = registry.async_get(state.entity_id)
            if not entry or not entry.config_entry_id:
                continue

            config_entry = self.hass.config_entries.async_get_entry(
                entry.config_entry_id
            )
            if not config_entry or config_entry.domain == DOMAIN:
                continue

            if self._host_in_config_entry(config_entry, host):
                return picture

        return None

    @staticmethod
    def _host_in_config_entry(config_entry, host: str) -> bool:
        """Check if a config entry references the given host."""
        for value in config_entry.data.values():
            if isinstance(value, str):
                if value == host or f"://{host}" in value:
                    return True
        return False
