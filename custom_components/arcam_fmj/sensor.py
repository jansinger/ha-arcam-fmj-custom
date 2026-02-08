"""Arcam diagnostic sensor entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from arcam.fmj.state import State

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcamFmjConfigEntry
from .entity import ArcamFmjEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ArcamSensorEntityDescription(SensorEntityDescription):
    """Describes an Arcam sensor entity."""

    get_value: Callable[[State], str | None]


def _get_audio_format(state: State) -> str | None:
    """Return the incoming audio format."""
    audio_format, _ = state.get_incoming_audio_format()
    if audio_format is None:
        return None
    return audio_format.name


def _get_audio_config(state: State) -> str | None:
    """Return the incoming audio channel configuration."""
    _, audio_config = state.get_incoming_audio_format()
    if audio_config is None:
        return None
    return audio_config.name


def _get_video_resolution(state: State) -> str | None:
    """Return the incoming video resolution."""
    video = state.get_incoming_video_parameters()
    if video is None:
        return None
    return f"{video.horizontal_resolution}x{video.vertical_resolution}"


def _get_video_refresh_rate(state: State) -> str | None:
    """Return the incoming video refresh rate."""
    video = state.get_incoming_video_parameters()
    if video is None:
        return None
    return str(video.refresh_rate)


def _get_video_colorspace(state: State) -> str | None:
    """Return the incoming video colorspace."""
    video = state.get_incoming_video_parameters()
    if video is None:
        return None
    return video.colorspace.name


def _get_video_interlaced(state: State) -> str | None:
    """Return whether the incoming video is interlaced."""
    video = state.get_incoming_video_parameters()
    if video is None:
        return None
    return "Interlaced" if video.interlaced else "Progressive"


def _get_audio_sample_rate(state: State) -> str | None:
    """Return the incoming audio sample rate."""
    rate = state.get_incoming_audio_sample_rate()
    if not rate:
        return None
    return str(rate)


SENSOR_DESCRIPTIONS: list[ArcamSensorEntityDescription] = [
    ArcamSensorEntityDescription(
        key="audio_format",
        translation_key="audio_format",
        entity_category=EntityCategory.DIAGNOSTIC,
        get_value=_get_audio_format,
    ),
    ArcamSensorEntityDescription(
        key="audio_config",
        translation_key="audio_config",
        entity_category=EntityCategory.DIAGNOSTIC,
        get_value=_get_audio_config,
    ),
    ArcamSensorEntityDescription(
        key="video_resolution",
        translation_key="video_resolution",
        entity_category=EntityCategory.DIAGNOSTIC,
        get_value=_get_video_resolution,
    ),
    ArcamSensorEntityDescription(
        key="video_refresh_rate",
        translation_key="video_refresh_rate",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_video_refresh_rate,
    ),
    ArcamSensorEntityDescription(
        key="video_colorspace",
        translation_key="video_colorspace",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_video_colorspace,
    ),
    ArcamSensorEntityDescription(
        key="video_scan_mode",
        translation_key="video_scan_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_video_interlaced,
    ),
    ArcamSensorEntityDescription(
        key="audio_sample_rate",
        translation_key="audio_sample_rate",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_audio_sample_rate,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ArcamFmjConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Arcam sensor entities."""
    data = config_entry.runtime_data
    uuid = config_entry.unique_id or config_entry.entry_id

    # Diagnostic sensors are only relevant for Zone 1
    entities: list[ArcamSensorEntity] = [
        ArcamSensorEntity(config_entry.title, data.state_zone1, uuid, description)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class ArcamSensorEntity(ArcamFmjEntity, SensorEntity):
    """Representation of an Arcam diagnostic sensor."""

    entity_description: ArcamSensorEntityDescription

    def __init__(
        self,
        device_name: str,
        state: State,
        uuid: str,
        description: ArcamSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(device_name, state, uuid)
        self.entity_description = description
        self._attr_unique_id = f"{uuid}-{state.zn}-{description.key}"

    @property
    def native_value(self) -> str | None:
        """Return the sensor value."""
        return self.entity_description.get_value(self._state)
