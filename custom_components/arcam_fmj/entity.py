"""Base entity for Arcam FMJ integration."""

from __future__ import annotations

import logging

from arcam.fmj import ConnectionFailed
from arcam.fmj.state import State

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    SIGNAL_CLIENT_DATA,
    SIGNAL_CLIENT_STARTED,
    SIGNAL_CLIENT_STOPPED,
)

_LOGGER = logging.getLogger(__name__)


class ArcamFmjEntity(Entity):
    """Base class for all Arcam FMJ entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
    ) -> None:
        """Initialize the entity."""
        self._state = state
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uuid)},
            manufacturer="Arcam",
            model=state.model or "Arcam FMJ AVR",
            name=device_name,
        )

    async def async_added_to_hass(self) -> None:
        """Register dispatcher callbacks."""
        if self._state.client.connected:
            self._attr_available = True

        @callback
        def _data(host: str) -> None:
            if host == self._state.client.host:
                self.async_write_ha_state()

        @callback
        def _started(host: str) -> None:
            if host == self._state.client.host:
                self._attr_available = True
                self.async_schedule_update_ha_state(force_refresh=True)

        @callback
        def _stopped(host: str) -> None:
            if host == self._state.client.host:
                self._attr_available = False
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_CLIENT_DATA, _data)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_CLIENT_STARTED, _started)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_CLIENT_STOPPED, _stopped)
        )

    async def async_update(self) -> None:
        """Force update of state."""
        try:
            await self._state.update()
        except ConnectionFailed:
            _LOGGER.debug("Connection lost during update for %s", self.entity_id)
