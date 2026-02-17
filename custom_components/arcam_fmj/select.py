"""Arcam select entities."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from arcam.fmj import ConnectionFailed, DolbyAudioMode, SourceCodes
from arcam.fmj.state import State

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcamFmjConfigEntry
from .entity import ArcamFmjEntity

_LOGGER = logging.getLogger(__name__)

# Display brightness levels: protocol value -> label (0-2 per spec)
DISPLAY_BRIGHTNESS_OPTIONS = {
    0: "Off",
    1: "Level 1",
    2: "Level 2",
}

# Compression modes: protocol value -> label (0-2 per spec)
COMPRESSION_OPTIONS = {
    0: "Off",
    1: "Light",
    2: "Medium",
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
        options_map=DISPLAY_BRIGHTNESS_OPTIONS,
        options=list(DISPLAY_BRIGHTNESS_OPTIONS.values()),
        get_value=lambda state: state.get_display_brightness(),
        set_value=lambda state, value: state.set_display_brightness(value),
    ),
    ArcamSelectEntityDescription(
        key="compression",
        translation_key="compression",
        entity_registry_enabled_default=False,
        options_map=COMPRESSION_OPTIONS,
        options=list(COMPRESSION_OPTIONS.values()),
        get_value=lambda state: state.get_compression(),
        set_value=lambda state, value: state.set_compression(value),
    ),
    ArcamSelectEntityDescription(
        key="dolby_audio",
        translation_key="dolby_audio",
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

    entities: list[SelectEntity] = [
        ArcamSelectEntity(data.device_name, data.state_zone1, uuid, description)
        for description in SELECT_DESCRIPTIONS
    ]

    # Room EQ with dynamic preset names from device
    entities.append(
        ArcamRoomEqSelectEntity(data.device_name, data.state_zone1, uuid)
    )

    # Sound mode (decode mode) for Zone 1 — dynamic options based on audio input
    entities.append(
        ArcamSoundModeSelectEntity(data.device_name, data.state_zone1, uuid)
    )

    # Source select for Zone 1 and Zone 2
    for state in (data.state_zone1, data.state_zone2):
        if state.get_source_list():
            entities.append(
                ArcamSourceSelectEntity(data.device_name, state, uuid)
            )

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


class ArcamRoomEqSelectEntity(ArcamFmjEntity, SelectEntity):
    """Select entity for Room EQ with dynamic preset names from device."""

    _attr_name = "Room EQ"
    _FALLBACK_NAMES = {1: "Preset 1", 2: "Preset 2", 3: "Preset 3"}

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
    ) -> None:
        """Initialize the Room EQ select entity."""
        super().__init__(device_name, state, uuid)
        self._attr_unique_id = f"{uuid}-{state.zn}-room_eq"

    def _preset_label(self, index: int) -> str:
        """Get the display label for a preset index (1-3)."""
        names = self._state.get_room_eq_names()
        if names:
            name = getattr(names, f"eq{index}", None)
            if name:
                return name
        return self._FALLBACK_NAMES[index]

    def _build_options_map(self) -> dict[int, str]:
        """Build protocol value -> display label map with unique labels."""
        labels: dict[int, str] = {0: "Off"}
        raw_labels = {i: self._preset_label(i) for i in (1, 2, 3)}

        # Count occurrences to detect duplicates
        counts: dict[str, int] = {}
        for label in raw_labels.values():
            counts[label] = counts.get(label, 0) + 1

        for i in (1, 2, 3):
            label = raw_labels[i]
            if counts[label] > 1 or label == "Off":
                labels[i] = f"{label} (Preset {i})"
            else:
                labels[i] = label

        return labels

    @property
    def options(self) -> list[str]:
        """Return available Room EQ options with device preset names."""
        return list(self._build_options_map().values())

    @property
    def current_option(self) -> str | None:
        """Return the current Room EQ setting."""
        raw = self._state.get_room_eq()
        if raw is None:
            return None
        return self._build_options_map().get(raw)

    async def async_select_option(self, option: str) -> None:
        """Set the Room EQ preset."""
        options_map = self._build_options_map()
        reverse = {v: k for k, v in options_map.items()}
        raw = reverse.get(option)
        if raw is None:
            _LOGGER.error("Unknown Room EQ option: %s", option)
            return
        try:
            await self._state.set_room_eq(raw)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                "Connection failed during room_eq"
            ) from exception
        self.async_write_ha_state()


def _format_mode_name(name: str) -> str:
    """Format enum name for display: STEREO_DOWNMIX -> Stereo Downmix."""
    return name.replace("_", " ").title()


def _parse_mode_name(display: str) -> str:
    """Parse display name back to enum name: Stereo Downmix -> STEREO_DOWNMIX."""
    return display.replace(" ", "_").upper()


class ArcamSoundModeSelectEntity(ArcamFmjEntity, SelectEntity):
    """Select entity for Arcam sound/decode mode with dynamic options."""

    _attr_name = "Sound Mode"

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
    ) -> None:
        """Initialize the sound mode select entity."""
        super().__init__(device_name, state, uuid)
        self._attr_unique_id = f"{uuid}-{state.zn}-sound_mode"

    @property
    def options(self) -> list[str]:
        """Return available sound modes (dynamic based on audio input)."""
        modes = self._state.get_decode_modes()
        if modes is None:
            return []
        names = [_format_mode_name(m.name) for m in modes]
        # Ensure current mode is in the list (may come from fallback enum)
        current = self.current_option
        if current and current not in names:
            names.append(current)
        return names

    @property
    def current_option(self) -> str | None:
        """Return the current sound mode."""
        mode = self._state.get_decode_mode()
        if mode is None:
            return None
        return _format_mode_name(mode.name)

    async def async_select_option(self, option: str) -> None:
        """Set the sound mode."""
        try:
            await self._state.set_decode_mode(_parse_mode_name(option))
        except (KeyError, ValueError) as exception:
            raise HomeAssistantError(
                f"Unsupported sound mode: {option}"
            ) from exception
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                "Connection failed during sound_mode"
            ) from exception
        self.async_write_ha_state()


class ArcamSourceSelectEntity(ArcamFmjEntity, SelectEntity):
    """Select entity for Arcam input source."""

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
    ) -> None:
        """Initialize the source select entity."""
        super().__init__(device_name, state, uuid)
        self._attr_name = f"Zone {state.zn} Source"
        self._attr_unique_id = f"{uuid}-{state.zn}-source"
        self._attr_entity_registry_enabled_default = state.zn == 1

    @property
    def options(self) -> list[str]:
        """Return available input sources."""
        return [x.name for x in self._state.get_source_list()]

    @property
    def current_option(self) -> str | None:
        """Return the current input source."""
        if (value := self._state.get_source()) is None:
            return None
        return value.name

    async def async_select_option(self, option: str) -> None:
        """Set the input source."""
        try:
            value = SourceCodes[option]
        except KeyError:
            raise HomeAssistantError(f"Unsupported source: {option}") from None
        try:
            await self._state.set_source(value)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                "Connection failed during source selection"
            ) from exception
        self.async_write_ha_state()
