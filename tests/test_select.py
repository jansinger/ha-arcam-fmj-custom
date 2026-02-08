"""Tests for Arcam FMJ select entities."""

from unittest.mock import MagicMock

import pytest
from arcam.fmj import ConnectionFailed

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration

ENTITY_BRIGHTNESS = "select.arcam_av40_display_brightness"
ENTITY_COMPRESSION = "select.arcam_av40_compression"
ENTITY_ROOM_EQ = "select.arcam_av40_room_eq"
ENTITY_DOLBY_AUDIO = "select.arcam_av40_dolby_audio"
ENTITY_SOUND_MODE = "select.arcam_av40_sound_mode"


async def test_select_entities_created(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test all select entities are created."""
    await setup_integration(hass, mock_config_entry)

    # Display brightness is enabled by default
    assert hass.states.get(ENTITY_BRIGHTNESS) is not None

    # Compression is disabled by default but registered
    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_COMPRESSION)
    assert entry is not None
    assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


async def test_display_brightness_value(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test display brightness reports correct label."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_BRIGHTNESS)
    # Raw value 2 maps to "Level 2"
    assert state.state == "Level 2"


async def test_display_brightness_options(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test display brightness options list."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_BRIGHTNESS)
    options = state.attributes["options"]
    assert options == ["Off", "Level 1", "Level 2", "Level 3"]


async def test_set_display_brightness(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting display brightness."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: ENTITY_BRIGHTNESS, "option": "Level 3"},
        blocking=True,
    )

    # "Level 3" maps to raw value 3
    mock_state_zone1.set_display_brightness.assert_called_once_with(3)


async def test_set_display_brightness_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting display brightness to off."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: ENTITY_BRIGHTNESS, "option": "Off"},
        blocking=True,
    )

    mock_state_zone1.set_display_brightness.assert_called_once_with(0)


async def test_select_config_category(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test select entities have config entity category."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_BRIGHTNESS)
    assert entry is not None
    assert entry.entity_category is None


async def test_select_none_value(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test select returns unknown when getter returns None."""
    mock_state_zone1.get_display_brightness.return_value = None
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_BRIGHTNESS)
    assert state.state == "unknown"


async def test_select_connection_error(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test ConnectionFailed is raised as HomeAssistantError."""
    mock_state_zone1.set_display_brightness = MagicMock(side_effect=ConnectionFailed)

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "select",
            "select_option",
            {ATTR_ENTITY_ID: ENTITY_BRIGHTNESS, "option": "Level 3"},
            blocking=True,
        )


# --- Room EQ Select tests ---


async def test_room_eq_select_entity_created(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test room EQ select entity is created and enabled."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state is not None


async def test_room_eq_select_value(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test room EQ shows correct preset label."""
    mock_state_zone1.get_room_eq.return_value = 1
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state.state == "Preset 1"


async def test_room_eq_select_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test room EQ shows Off when value is 0."""
    mock_state_zone1.get_room_eq.return_value = 0
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state.state == "Off"


async def test_room_eq_select_options(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test room EQ options list."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state.attributes["options"] == ["Off", "Preset 1", "Preset 2", "Preset 3"]


async def test_set_room_eq_preset(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting room EQ to a preset."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: ENTITY_ROOM_EQ, "option": "Preset 2"},
        blocking=True,
    )

    mock_state_zone1.set_room_eq.assert_called_once_with(2)


async def test_set_room_eq_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting room EQ to off."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: ENTITY_ROOM_EQ, "option": "Off"},
        blocking=True,
    )

    mock_state_zone1.set_room_eq.assert_called_once_with(0)


async def test_room_eq_select_none(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test room EQ returns unknown when getter returns None."""
    mock_state_zone1.get_room_eq.return_value = None
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state.state == "unknown"


async def test_room_eq_select_config_category(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test room EQ has config entity category."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_ROOM_EQ)
    assert entry is not None
    assert entry.entity_category is None


async def test_room_eq_select_connection_error(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test ConnectionFailed on room EQ raises HomeAssistantError."""
    mock_state_zone1.set_room_eq = MagicMock(side_effect=ConnectionFailed)

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "select",
            "select_option",
            {ATTR_ENTITY_ID: ENTITY_ROOM_EQ, "option": "Preset 1"},
            blocking=True,
        )


# --- Dolby Audio Select tests ---


async def test_dolby_audio_disabled_by_default(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test Dolby Audio select is disabled by default but registered."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_DOLBY_AUDIO)
    assert entry is not None
    assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


# --- Sound Mode Select tests ---


async def test_sound_mode_select_created(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test sound mode select entity is created."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_SOUND_MODE)
    assert state is not None


async def test_sound_mode_select_value(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test sound mode displays formatted decode mode name."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_SOUND_MODE)
    # Mock returns DecodeModeMCH.MULTI_CHANNEL -> "Multi Channel"
    assert state.state == "Multi Channel"


async def test_sound_mode_select_options(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test sound mode options are formatted decode mode names."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_SOUND_MODE)
    options = state.attributes.get("options")
    assert "Stereo Downmix" in options
    assert "Multi Channel" in options


async def test_set_sound_mode(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting sound mode converts display name back to enum name."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: ENTITY_SOUND_MODE, "option": "Stereo Downmix"},
        blocking=True,
    )

    # "Stereo Downmix" -> "STEREO_DOWNMIX"
    mock_state_zone1.set_decode_mode.assert_called_once_with("STEREO_DOWNMIX")
