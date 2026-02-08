"""Tests for Arcam FMJ select entities."""

from unittest.mock import MagicMock

import pytest
from arcam.fmj import ConnectionFailed

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration

ENTITY_BRIGHTNESS = "select.arcam_fmj_192_168_1_100_display_brightness"
ENTITY_COMPRESSION = "select.arcam_fmj_192_168_1_100_compression"


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
    assert entry.entity_category == "config"


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
