"""Arcam number entities for audio controls."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from arcam.fmj import ConnectionFailed
from arcam.fmj.state import State

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcamFmjConfigEntry
from .entity import ArcamFmjEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ArcamNumberEntityDescription(NumberEntityDescription):
    """Describes an Arcam number entity."""

    get_value: Callable[[State], int | None]
    set_value: Callable[[State, int], Coroutine[Any, Any, None]]
    # Arcam protocol uses unsigned bytes with an offset for signed values.
    # e.g. bass: 0x00 = -14, 0x0E = 0, 0x1C = +14
    offset: int = 0


NUMBER_DESCRIPTIONS: list[ArcamNumberEntityDescription] = [
    ArcamNumberEntityDescription(
        key="bass",
        translation_key="bass",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-14,
        native_max_value=14,
        native_step=1,
        offset=14,
        get_value=lambda state: state.get_bass(),
        set_value=lambda state, value: state.set_bass(value),
    ),
    ArcamNumberEntityDescription(
        key="treble",
        translation_key="treble",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-14,
        native_max_value=14,
        native_step=1,
        offset=14,
        get_value=lambda state: state.get_treble(),
        set_value=lambda state, value: state.set_treble(value),
    ),
    ArcamNumberEntityDescription(
        key="balance",
        translation_key="balance",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-13,
        native_max_value=13,
        native_step=1,
        offset=13,
        get_value=lambda state: state.get_balance(),
        set_value=lambda state, value: state.set_balance(value),
    ),
    ArcamNumberEntityDescription(
        key="subwoofer_trim",
        translation_key="subwoofer_trim",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_min_value=-14,
        native_max_value=14,
        native_step=1,
        native_unit_of_measurement="dB",
        offset=14,
        get_value=lambda state: state.get_subwoofer_trim(),
        set_value=lambda state, value: state.set_subwoofer_trim(value),
    ),
    ArcamNumberEntityDescription(
        key="lipsync_delay",
        translation_key="lipsync_delay",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_min_value=0,
        native_max_value=200,
        native_step=5,
        native_unit_of_measurement="ms",
        offset=0,
        get_value=lambda state: state.get_lipsync_delay(),
        set_value=lambda state, value: state.set_lipsync_delay(value),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ArcamFmjConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Arcam number entities."""
    data = config_entry.runtime_data
    uuid = config_entry.unique_id or config_entry.entry_id

    # Audio controls are only supported on Zone 1
    entities: list[ArcamNumberEntity] = [
        ArcamNumberEntity(data.device_name, data.state_zone1, uuid, description)
        for description in NUMBER_DESCRIPTIONS
    ]

    async_add_entities(entities)


class ArcamNumberEntity(ArcamFmjEntity, NumberEntity):
    """Representation of an Arcam number control."""

    entity_description: ArcamNumberEntityDescription

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
        description: ArcamNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(device_name, state, uuid)
        self.entity_description = description
        self._attr_unique_id = f"{uuid}-{state.zn}-{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        raw = self.entity_description.get_value(self._state)
        if raw is None:
            return None
        return raw - self.entity_description.offset

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        raw = int(value + self.entity_description.offset)
        try:
            await self.entity_description.set_value(self._state, raw)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                f"Connection failed during {self.entity_description.key}"
            ) from exception
        self.async_write_ha_state()
