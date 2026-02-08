"""Arcam diagnostic sensor entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from typing import Any

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
    get_attributes: Callable[[State], dict[str, Any] | None] | None = field(
        default=None
    )


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


def _get_network_playback_status(state: State) -> str | None:
    """Return the network playback status."""
    status = state.get_network_playback_status()
    if status is None:
        return None
    return status.name


def _get_bluetooth_status(state: State) -> str | None:
    """Return the Bluetooth connection status."""
    result = state.get_bluetooth_status()
    if result is None:
        return None
    status, _track = result
    return status.name


def _get_room_eq_names(state: State) -> str | None:
    """Return the Room EQ preset names."""
    names = state.get_room_eq_names()
    if names is None:
        return None
    parts = [n for n in (names.eq1, names.eq2, names.eq3) if n]
    return " / ".join(parts) if parts else None


def _get_room_eq_names_attrs(state: State) -> dict[str, Any] | None:
    """Return Room EQ names as individual attributes."""
    names = state.get_room_eq_names()
    if names is None:
        return None
    return {"eq1": names.eq1, "eq2": names.eq2, "eq3": names.eq3}


def _get_hdmi_settings(state: State) -> str | None:
    """Return HDMI settings availability."""
    s = state.get_hdmi_settings()
    return "Available" if s is not None else None


def _get_hdmi_settings_attrs(state: State) -> dict[str, Any] | None:
    """Return HDMI settings as individual attributes."""
    s = state.get_hdmi_settings()
    if s is None:
        return None
    return {
        "zone1_osd": s.zone1_osd,
        "zone1_output": s.zone1_output,
        "zone1_lipsync": s.zone1_lipsync,
        "hdmi_audio_to_tv": s.hdmi_audio_to_tv,
        "hdmi_bypass_ip": s.hdmi_bypass_ip,
        "hdmi_bypass_source": s.hdmi_bypass_source,
        "cec_control": s.cec_control,
        "arc_control": s.arc_control,
        "tv_audio": s.tv_audio,
        "power_off_control": s.power_off_control,
    }


def _get_zone_settings(state: State) -> str | None:
    """Return zone settings availability."""
    s = state.get_zone_settings()
    return "Available" if s is not None else None


def _get_zone_settings_attrs(state: State) -> dict[str, Any] | None:
    """Return zone settings as individual attributes."""
    s = state.get_zone_settings()
    if s is None:
        return None
    return {
        "zone2_input": s.zone2_input,
        "zone2_status": s.zone2_status,
        "zone2_volume": s.zone2_volume,
        "zone2_max_volume": s.zone2_max_volume,
        "zone2_fixed_volume": s.zone2_fixed_volume,
        "zone2_max_on_volume": s.zone2_max_on_volume,
    }


SENSOR_DESCRIPTIONS: list[ArcamSensorEntityDescription] = [
    ArcamSensorEntityDescription(
        key="audio_input_format",
        translation_key="audio_input_format",
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
    ArcamSensorEntityDescription(
        key="network_playback_status",
        translation_key="network_playback_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_network_playback_status,
    ),
    ArcamSensorEntityDescription(
        key="bluetooth_status",
        translation_key="bluetooth_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_bluetooth_status,
    ),
    ArcamSensorEntityDescription(
        key="room_eq_names",
        translation_key="room_eq_names",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_room_eq_names,
        get_attributes=_get_room_eq_names_attrs,
    ),
    ArcamSensorEntityDescription(
        key="hdmi_settings",
        translation_key="hdmi_settings",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_hdmi_settings,
        get_attributes=_get_hdmi_settings_attrs,
    ),
    ArcamSensorEntityDescription(
        key="zone_settings",
        translation_key="zone_settings",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        get_value=_get_zone_settings,
        get_attributes=_get_zone_settings_attrs,
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.get_attributes:
            return self.entity_description.get_attributes(self._state)
        return None
