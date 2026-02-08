"""Arcam switch entities."""

from __future__ import annotations

import logging
from typing import Any

from arcam.fmj import ConnectionFailed
from arcam.fmj.state import State

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcamFmjConfigEntry
from .const import (
    DOMAIN,
    SIGNAL_CLIENT_DATA,
    SIGNAL_CLIENT_STARTED,
    SIGNAL_CLIENT_STOPPED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ArcamFmjConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Arcam switch entities."""
    client = config_entry.runtime_data

    entities: list[ArcamRoomEqSwitch] = []
    for zone in (1, 2):
        state = State(client, zone)
        entities.append(
            ArcamRoomEqSwitch(
                config_entry.title,
                state,
                config_entry.unique_id or config_entry.entry_id,
            )
        )

    async_add_entities(entities, True)


class ArcamRoomEqSwitch(SwitchEntity):
    """Representation of the Arcam Room EQ switch."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False
    _attr_name = "Room EQ"
    _attr_translation_key = "room_eq"

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
    ) -> None:
        """Initialize the switch entity."""
        self._state = state
        self._attr_unique_id = f"{uuid}-{state.zn}-room_eq"
        self._attr_entity_registry_enabled_default = state.zn == 1
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uuid)},
            manufacturer="Arcam",
            model=state.model or "Arcam FMJ AVR",
            name=device_name,
        )
        if state.zn != 1:
            self._attr_name = f"Room EQ Zone {state.zn}"

    @property
    def is_on(self) -> bool | None:
        """Return true if Room EQ is enabled."""
        return self._state.get_room_eq()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable Room EQ."""
        try:
            await self._state.set_room_eq(True)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                "Connection failed during room_eq"
            ) from exception
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable Room EQ."""
        try:
            await self._state.set_room_eq(False)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                "Connection failed during room_eq"
            ) from exception
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await self._state.start()
        try:
            await self._state.update()
            self._attr_available = True
        except ConnectionFailed:
            _LOGGER.debug("Connection lost during addition")

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
                self.async_schedule_update_ha_state(force_refresh=True)

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
            _LOGGER.debug("Connection lost during update")
