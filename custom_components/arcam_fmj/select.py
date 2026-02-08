"""Arcam select entities."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from arcam.fmj import ConnectionFailed, DolbyAudioMode
from arcam.fmj.state import State

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcamFmjConfigEntry
from .entity import ArcamFmjEntity

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

# Room EQ presets: protocol value -> label
ROOM_EQ_OPTIONS = {
    0: "Off",
    1: "Preset 1",
    2: "Preset 2",
    3: "Preset 3",
}

# Dolby Audio modes: protocol value -> label
DOLBY_AUDIO_OPTIONS = {
    0: "Off",
    1: "Movie",
    2: "Music",
    3: "Night",
}


@dataclass(frozen=True, kw_only=True)
class ArcamSelectEntityDescription(SelectEntityDescription):
    """Describes an Arcam select entity."""

    options_map: dict[int, str]
    get_value: Callable[[State], int | None]
    set_value: Callable[[State, int], Coroutine[Any, Any, None]]


SELECT_DESCRIPTIONS: list[ArcamSelectEntityDescription] = [
    ArcamSelectEntityDescription(
        key="display_brightness",
        translation_key="display_brightness",
        entity_category=EntityCategory.CONFIG,
        options_map=DISPLAY_BRIGHTNESS_OPTIONS,
        options=list(DISPLAY_BRIGHTNESS_OPTIONS.values()),
        get_value=lambda state: state.get_display_brightness(),
        set_value=lambda state, value: state.set_display_brightness(value),
    ),
    ArcamSelectEntityDescription(
        key="compression",
        translation_key="compression",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        options_map=COMPRESSION_OPTIONS,
        options=list(COMPRESSION_OPTIONS.values()),
        get_value=lambda state: state.get_compression(),
        set_value=lambda state, value: state.set_compression(value),
    ),
    ArcamSelectEntityDescription(
        key="room_eq",
        translation_key="room_eq",
        entity_category=EntityCategory.CONFIG,
        options_map=ROOM_EQ_OPTIONS,
        options=list(ROOM_EQ_OPTIONS.values()),
        get_value=lambda state: state.get_room_eq(),
        set_value=lambda state, value: state.set_room_eq(value),
    ),
    ArcamSelectEntityDescription(
        key="dolby_audio",
        translation_key="dolby_audio",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        options_map=DOLBY_AUDIO_OPTIONS,
        options=list(DOLBY_AUDIO_OPTIONS.values()),
        get_value=lambda state: (
            int(v) if (v := state.get_dolby_audio()) is not None else None
        ),
        set_value=lambda state, value: state.set_dolby_audio(DolbyAudioMode(value)),
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


class ArcamSelectEntity(ArcamFmjEntity, SelectEntity):
    """Representation of an Arcam select control."""

    entity_description: ArcamSelectEntityDescription

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
        description: ArcamSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(device_name, state, uuid)
        self.entity_description = description
        self._reverse_map = {v: k for k, v in description.options_map.items()}
        self._attr_unique_id = f"{uuid}-{state.zn}-{description.key}"

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
