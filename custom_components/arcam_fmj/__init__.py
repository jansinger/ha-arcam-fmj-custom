"""Arcam component."""

import asyncio
from asyncio import timeout
import contextlib
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from arcam.fmj import (
    AmxDuetRequest,
    ApiModel,
    ConnectionFailed,
    SourceCodes,
    detect_api_model,
)
from arcam.fmj.client import Client
from arcam.fmj.state import State

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .artwork import ArtworkLookup
from .const import (
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    SIGNAL_CLIENT_DATA,
    SIGNAL_CLIENT_STARTED,
    SIGNAL_CLIENT_STOPPED,
)

_DEFAULT_POLL_INTERVAL = 10
_NETWORK_SOURCES = {SourceCodes.NET, SourceCodes.USB, SourceCodes.BT, SourceCodes.NET_USB}
_IMAGES_PATH = Path(__file__).parent / "images"
STATIC_URL_PREFIX = "/api/arcam_fmj/images"


@dataclass
class ArcamFmjData:
    """Runtime data for Arcam FMJ integration."""

    client: Client
    state_zone1: State
    state_zone2: State
    device_name: str
    artwork: ArtworkLookup


type ArcamFmjConfigEntry = ConfigEntry[ArcamFmjData]

_LOGGER = logging.getLogger(__name__)


PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]


async def _fetch_device_name(client: Client) -> str | None:
    """Connect briefly to get device model name via AMX Duet protocol."""
    try:
        async with timeout(5):
            await client.start()
            # process() must run for request/response to work
            process_task = asyncio.create_task(client.process())
            try:
                amx = await client.request_raw(AmxDuetRequest())
                if amx and amx.device_model:
                    return amx.device_model
            finally:
                process_task.cancel()
                try:
                    await process_task
                except (asyncio.CancelledError, ConnectionFailed):
                    pass
    except (ConnectionFailed, TimeoutError):
        _LOGGER.debug("Could not fetch model name during setup")
    except Exception:
        _LOGGER.debug("Unexpected error fetching model name", exc_info=True)
    finally:
        await client.stop()
    return None


def _resolve_api_model(model: str | None) -> ApiModel:
    """Resolve device model name to API model enum."""
    if model:
        result = detect_api_model(model)
        if result is not None:
            return result
    return ApiModel.API450_SERIES


async def async_setup_entry(hass: HomeAssistant, entry: ArcamFmjConfigEntry) -> bool:
    """Set up config entry."""
    client = Client(entry.data[CONF_HOST], entry.data[CONF_PORT])

    # Fetch model name before creating State objects so api_model is correct
    model = await _fetch_device_name(client)
    device_name = f"Arcam {model}" if model else DEFAULT_NAME
    api_model = _resolve_api_model(model)

    state_zone1 = State(client, 1, api_model)
    state_zone2 = State(client, 2, api_model)

    await state_zone1.start()
    await state_zone2.start()

    entry.runtime_data = ArcamFmjData(
        client=client,
        state_zone1=state_zone1,
        state_zone2=state_zone2,
        device_name=device_name,
        artwork=ArtworkLookup(async_get_clientsession(hass)),
    )

    # Register static path for source images
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL_PREFIX, str(_IMAGES_PATH), cache_headers=True)]
    )

    entry.async_create_background_task(
        hass, _run_client(hass, entry, DEFAULT_SCAN_INTERVAL), "arcam_fmj"
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Cleanup before removing config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _poll_now_playing(
    data: ArcamFmjData, hass: HomeAssistant, poll_interval: int
) -> None:
    """Periodically re-poll now-playing metadata while a network source is active.

    The Arcam device pushes state changes for standard commands (power, volume,
    mute, source) via the TCP socket listener.  However, now-playing metadata
    (title, artist, album) for network sources is NOT pushed by the device,
    so it must be polled periodically.
    """
    while True:
        await asyncio.sleep(poll_interval)
        try:
            updated = False
            for state in (data.state_zone1, data.state_zone2):
                if state.get_power() and state.get_source() in _NETWORK_SOURCES:
                    await state.update_now_playing()
                    updated = True
            if updated:
                async_dispatcher_send(hass, SIGNAL_CLIENT_DATA, data.client.host)
        except ConnectionFailed:
            return
        except Exception:
            _LOGGER.debug("Now playing poll failed", exc_info=True)


async def _run_client(
    hass: HomeAssistant, entry: ArcamFmjConfigEntry, interval: float
) -> None:
    """Maintain persistent connection to the Arcam device.

    All outgoing requests (user commands and polling) are serialized by the
    library's priority queue with 0.2s throttle and deduplication, so there
    are no race conditions between concurrent callers.
    """
    data: ArcamFmjData = entry.runtime_data
    client = data.client

    def _listen(_: Any) -> None:
        async_dispatcher_send(hass, SIGNAL_CLIENT_DATA, client.host)

    while True:
        try:
            async with timeout(interval):
                await client.start()

            _LOGGER.debug("Client connected %s", client.host)

            try:
                with client.listen(_listen):
                    # process() must run for request/response to work
                    process_task = asyncio.create_task(client.process())

                    # Do a single state update before notifying entities.
                    try:
                        await data.state_zone1.update()
                        await data.state_zone2.update()
                    except Exception:
                        _LOGGER.debug("Initial state update failed", exc_info=True)

                    async_dispatcher_send(hass, SIGNAL_CLIENT_STARTED, client.host)

                    # Poll now-playing metadata periodically alongside
                    # the packet reader so track changes are picked up.
                    poll_interval = entry.options.get(
                        "poll_interval", _DEFAULT_POLL_INTERVAL
                    )
                    poll_task = asyncio.create_task(
                        _poll_now_playing(data, hass, poll_interval)
                    )
                    try:
                        await process_task
                    finally:
                        poll_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await poll_task
            finally:
                await client.stop()

                _LOGGER.debug("Client disconnected %s", client.host)
                async_dispatcher_send(hass, SIGNAL_CLIENT_STOPPED, client.host)

        except ConnectionFailed:
            await asyncio.sleep(interval)
        except TimeoutError:
            continue
        except Exception:
            _LOGGER.exception("Unexpected exception in arcam client, retrying")
            await asyncio.sleep(interval)
