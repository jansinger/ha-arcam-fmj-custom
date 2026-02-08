"""Arcam switch entities."""

from __future__ import annotations

from typing import Any

from arcam.fmj import ConnectionFailed
from arcam.fmj.state import State

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcamFmjConfigEntry
from .entity import ArcamFmjEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ArcamFmjConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Arcam switch entities."""
    data = config_entry.runtime_data

    # Room EQ is only supported on Zone 1
    async_add_entities(
        [
            ArcamRoomEqSwitch(
                config_entry.title,
                data.state_zone1,
                config_entry.unique_id or config_entry.entry_id,
            )
        ],
    )


class ArcamRoomEqSwitch(ArcamFmjEntity, SwitchEntity):
    """Representation of the Arcam Room EQ switch."""

    _attr_translation_key = "room_eq"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(device_name, state, uuid)
        self._attr_unique_id = f"{uuid}-{state.zn}-room_eq"

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
