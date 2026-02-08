"""Arcam select entities."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from arcam.fmj import ConnectionFailed
from arcam.fmj.state import State

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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

# Display brightness levels: protocol value -> label
DISPLAY_BRIGHTNESS_OPTIONS = {
    0: "Off",
    1: "Level 1",
    2: "Level 2",
    3: "Level 3",
}

# Compression modes: protocol value -> label
COMPRESSION_OPTIONS = {
    0: "Off",
    1: "Light",
    2: "Medium",
    3: "Heavy",
}


@dataclass(frozen=True, kw_only=True)
class ArcamSelectEntityDescription(SelectEntityDescription):
    """Describes an Arcam select entity."""

    options_map: dict[int, str]
    get_value: Callable[[State], int | None]
    set_value: Callable[[State, int], Coroutine[Any, Any, None]]
    zone_support: bool = True


SELECT_DESCRIPTIONS: list[ArcamSelectEntityDescription] = [
    ArcamSelectEntityDescription(
        key="display_brightness",
        translation_key="display_brightness",
        name="Display Brightness",
        options_map=DISPLAY_BRIGHTNESS_OPTIONS,
        options=list(DISPLAY_BRIGHTNESS_OPTIONS.values()),
        get_value=lambda state: state.get_display_brightness(),
        set_value=lambda state, value: state.set_display_brightness(value),
        zone_support=False,
    ),
    ArcamSelectEntityDescription(
        key="compression",
        translation_key="compression",
        name="Compression",
        options_map=COMPRESSION_OPTIONS,
        options=list(COMPRESSION_OPTIONS.values()),
        get_value=lambda state: state.get_compression(),
        set_value=lambda state, value: state.set_compression(value),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ArcamFmjConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Arcam select entities."""
    data = config_entry.runtime_data
    uuid = config_entry.unique_id or config_entry.entry_id

    # Display brightness and compression are only supported on Zone 1
    entities: list[ArcamSelectEntity] = [
        ArcamSelectEntity(config_entry.title, data.state_zone1, uuid, description)
        for description in SELECT_DESCRIPTIONS
    ]

    async_add_entities(entities)


class ArcamSelectEntity(SelectEntity):
    """Representation of an Arcam select control."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False
    entity_description: ArcamSelectEntityDescription

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
        description: ArcamSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        self._state = state
        self.entity_description = description
        self._reverse_map = {v: k for k, v in description.options_map.items()}
        self._attr_unique_id = f"{uuid}-{state.zn}-{description.key}"
        self._attr_entity_registry_enabled_default = state.zn == 1
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uuid)},
            manufacturer="Arcam",
            model=state.model or "Arcam FMJ AVR",
            name=device_name,
        )
        if state.zn != 1:
            self._attr_name = f"{description.name} Zone {state.zn}"

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        raw = self.entity_description.get_value(self._state)
        if raw is None:
            return None
        return self.entity_description.options_map.get(raw)

    async def async_select_option(self, option: str) -> None:
        """Set the selected option."""
        raw = self._reverse_map.get(option)
        if raw is None:
            _LOGGER.error("Unknown option %s for %s", option, self.entity_description.key)
            return
        try:
            await self.entity_description.set_value(self._state, raw)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                f"Connection failed during {self.entity_description.key}"
            ) from exception
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
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
                self.async_write_ha_state()

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
            _LOGGER.debug("Connection lost during update")
