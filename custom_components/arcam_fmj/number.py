"""Arcam number entities for audio controls."""

from __future__ import annotations

import asyncio
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


def _sign_mag_decode(raw: int) -> float:
    """Decode sign-magnitude byte: 0x00-0x7F positive, 0x80+ negative."""
    if raw >= 0x80:
        return -(raw - 0x80)
    return raw


def _sign_mag_encode(value: float) -> int:
    """Encode to sign-magnitude byte."""
    if value < 0:
        return 0x80 + int(-value)
    return int(value)


def _sub_trim_decode(raw: int) -> float:
    """Decode subwoofer trim: sign-magnitude with 0.5dB steps."""
    if raw >= 0x80:
        return -(raw - 0x80) * 0.5
    return raw * 0.5


def _sub_trim_encode(value: float) -> int:
    """Encode subwoofer trim to sign-magnitude with 0.5dB steps."""
    if value < 0:
        return 0x80 + int(-value / 0.5)
    return int(value / 0.5)


def _lipsync_decode(raw: int) -> float:
    """Decode lipsync delay: raw value in 5ms steps."""
    return raw * 5


def _lipsync_encode(value: float) -> int:
    """Encode lipsync delay: ms to 5ms steps."""
    return int(value / 5)


@dataclass(frozen=True, kw_only=True)
class ArcamNumberEntityDescription(NumberEntityDescription):
    """Describes an Arcam number entity."""

    get_value: Callable[[State], int | None]
    set_value: Callable[[State, int], Coroutine[Any, Any, None]]
    decode_value: Callable[[int], float]
    encode_value: Callable[[float], int]


NUMBER_DESCRIPTIONS: list[ArcamNumberEntityDescription] = [
    ArcamNumberEntityDescription(
        key="bass",
        translation_key="bass",
        native_min_value=-12,
        native_max_value=12,
        native_step=1,
        native_unit_of_measurement="dB",
        decode_value=_sign_mag_decode,
        encode_value=_sign_mag_encode,
        get_value=lambda state: state.get_bass(),
        set_value=lambda state, value: state.set_bass(value),
    ),
    ArcamNumberEntityDescription(
        key="treble",
        translation_key="treble",
        native_min_value=-12,
        native_max_value=12,
        native_step=1,
        native_unit_of_measurement="dB",
        decode_value=_sign_mag_decode,
        encode_value=_sign_mag_encode,
        get_value=lambda state: state.get_treble(),
        set_value=lambda state, value: state.set_treble(value),
    ),
    ArcamNumberEntityDescription(
        key="balance",
        translation_key="balance",
        native_min_value=-6,
        native_max_value=6,
        native_step=1,
        decode_value=_sign_mag_decode,
        encode_value=_sign_mag_encode,
        get_value=lambda state: state.get_balance(),
        set_value=lambda state, value: state.set_balance(value),
    ),
    ArcamNumberEntityDescription(
        key="subwoofer_trim",
        translation_key="subwoofer_trim",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_min_value=-10,
        native_max_value=10,
        native_step=0.5,
        native_unit_of_measurement="dB",
        decode_value=_sub_trim_decode,
        encode_value=_sub_trim_encode,
        get_value=lambda state: state.get_subwoofer_trim(),
        set_value=lambda state, value: state.set_subwoofer_trim(value),
    ),
    ArcamNumberEntityDescription(
        key="lipsync_delay",
        translation_key="lipsync_delay",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_min_value=0,
        native_max_value=250,
        native_step=5,
        native_unit_of_measurement="ms",
        decode_value=_lipsync_decode,
        encode_value=_lipsync_encode,
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
        return self.entity_description.decode_value(raw)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        raw = self.entity_description.encode_value(value)
        try:
            await self.entity_description.set_value(self._state, raw)
        except ConnectionFailed as exception:
            raise HomeAssistantError(
                f"Connection failed during {self.entity_description.key}"
            ) from exception
        except asyncio.CancelledError:
            _LOGGER.debug("Command %s superseded by newer value", self.entity_description.key)
            return
        self.async_write_ha_state()
