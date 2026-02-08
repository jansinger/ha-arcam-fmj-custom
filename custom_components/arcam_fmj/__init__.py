"""Arcam component."""

import asyncio
from asyncio import timeout
from dataclasses import dataclass
import logging
from typing import Any

from arcam.fmj import AmxDuetRequest, ConnectionFailed
from arcam.fmj.client import Client
from arcam.fmj.state import State

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    SIGNAL_CLIENT_DATA,
    SIGNAL_CLIENT_STARTED,
    SIGNAL_CLIENT_STOPPED,
)


@dataclass
class ArcamFmjData:
    """Runtime data for Arcam FMJ integration."""

    client: Client
    state_zone1: State
    state_zone2: State
    device_name: str


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
        async with timeout(3):
            await client.start()
        amx = await client.request_raw(AmxDuetRequest())
        if amx and amx.device_model:
            return amx.device_model
    except (ConnectionFailed, TimeoutError):
        _LOGGER.debug("Could not fetch model name during setup")
    except Exception:
        _LOGGER.debug("Unexpected error fetching model name", exc_info=True)
    finally:
        if client.connected:
            await client.stop()
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ArcamFmjConfigEntry) -> bool:
    """Set up config entry."""
    client = Client(entry.data[CONF_HOST], entry.data[CONF_PORT])
    state_zone1 = State(client, 1)
    state_zone2 = State(client, 2)

    await state_zone1.start()
    await state_zone2.start()

    # Fetch model name before creating entities so entity IDs are short
    model = await _fetch_device_name(client)
    device_name = f"Arcam {model}" if model else DEFAULT_NAME

    entry.runtime_data = ArcamFmjData(
        client=client,
        state_zone1=state_zone1,
        state_zone2=state_zone2,
        device_name=device_name,
    )

    entry.async_create_background_task(
        hass, _run_client(hass, entry.runtime_data, DEFAULT_SCAN_INTERVAL), "arcam_fmj"
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Cleanup before removing config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _run_client(hass: HomeAssistant, data: ArcamFmjData, interval: float) -> None:
    client = data.client

    def _listen(_: Any) -> None:
        async_dispatcher_send(hass, SIGNAL_CLIENT_DATA, client.host)

    while True:
        try:
            async with timeout(interval):
                await client.start()

            _LOGGER.debug("Client connected %s", client.host)

            # Do a single state update before notifying entities.
            # This prevents every entity from calling update() independently.
            try:
                await data.state_zone1.update()
                await data.state_zone2.update()
            except Exception:
                _LOGGER.debug("Initial state update failed", exc_info=True)

            async_dispatcher_send(hass, SIGNAL_CLIENT_STARTED, client.host)

            try:
                with client.listen(_listen):
                    await client.process()
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
