"""Tests for Arcam FMJ sensor entities."""

from unittest.mock import MagicMock

from arcam.fmj import (
    IncomingAudioConfig,
    IncomingAudioFormat,
    IncomingVideoColorspace,
    VideoParameters,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration

# Enabled by default
ENTITY_AUDIO_FORMAT = "sensor.arcam_fmj_192_168_1_100_audio_format"
ENTITY_AUDIO_CONFIG = "sensor.arcam_fmj_192_168_1_100_audio_channels"
ENTITY_VIDEO_RESOLUTION = "sensor.arcam_fmj_192_168_1_100_video_resolution"

# Disabled by default
ENTITY_VIDEO_REFRESH = "sensor.arcam_fmj_192_168_1_100_video_refresh_rate"
ENTITY_VIDEO_COLORSPACE = "sensor.arcam_fmj_192_168_1_100_video_colorspace"
ENTITY_VIDEO_SCAN = "sensor.arcam_fmj_192_168_1_100_video_scan_mode"
ENTITY_AUDIO_SAMPLE = "sensor.arcam_fmj_192_168_1_100_audio_sample_rate"


async def test_enabled_sensor_entities_created(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test enabled sensor entities have state."""
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get(ENTITY_AUDIO_FORMAT) is not None
    assert hass.states.get(ENTITY_AUDIO_CONFIG) is not None
    assert hass.states.get(ENTITY_VIDEO_RESOLUTION) is not None


async def test_disabled_sensor_entities_registered(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test disabled sensor entities are in entity registry."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    for entity_id in (
        ENTITY_VIDEO_REFRESH,
        ENTITY_VIDEO_COLORSPACE,
        ENTITY_VIDEO_SCAN,
        ENTITY_AUDIO_SAMPLE,
    ):
        entry = registry.async_get(entity_id)
        assert entry is not None, f"{entity_id} not in registry"
        assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


async def test_audio_format_none(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test audio format is unknown when no data."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_AUDIO_FORMAT)
    assert state.state == "unknown"


async def test_audio_config_none(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test audio config is unknown when no data."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_AUDIO_CONFIG)
    assert state.state == "unknown"


async def test_audio_format_with_data(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test audio format shows format name."""
    mock_state_zone1.get_incoming_audio_format.return_value = (
        IncomingAudioFormat.DOLBY_DIGITAL,
        IncomingAudioConfig.STEREO_ONLY,
    )
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_AUDIO_FORMAT)
    assert state.state == "DOLBY_DIGITAL"

    state = hass.states.get(ENTITY_AUDIO_CONFIG)
    assert state.state == "STEREO_ONLY"


async def test_video_resolution_none(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test video resolution is unknown when no data."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_VIDEO_RESOLUTION)
    assert state.state == "unknown"


async def test_video_resolution_with_data(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test video resolution displays correctly."""
    video = MagicMock(spec=VideoParameters)
    video.horizontal_resolution = 3840
    video.vertical_resolution = 2160

    mock_state_zone1.get_incoming_video_parameters.return_value = video
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_VIDEO_RESOLUTION)
    assert state.state == "3840x2160"


async def test_sensor_diagnostic_category(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test sensor entities have diagnostic entity category."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_AUDIO_FORMAT)
    assert entry is not None
    assert entry.entity_category == "diagnostic"
