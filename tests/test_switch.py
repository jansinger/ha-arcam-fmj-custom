"""Tests for Arcam FMJ switch entity."""

from unittest.mock import MagicMock

import pytest
from arcam.fmj import ConnectionFailed

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration

ENTITY_ROOM_EQ = "switch.arcam_fmj_192_168_1_100_room_eq"


async def test_switch_entity_created(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test room EQ switch entity is created."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state is not None


async def test_room_eq_on(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test room EQ reports on when enabled."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state.state == "on"


async def test_room_eq_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test room EQ reports off when disabled."""
    mock_state_zone1.get_room_eq.return_value = False
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ROOM_EQ)
    assert state.state == "off"


async def test_turn_on_room_eq(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test turning on room EQ."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {ATTR_ENTITY_ID: ENTITY_ROOM_EQ},
        blocking=True,
    )

    mock_state_zone1.set_room_eq.assert_called_once_with(True)


async def test_turn_off_room_eq(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test turning off room EQ."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "switch",
        "turn_off",
        {ATTR_ENTITY_ID: ENTITY_ROOM_EQ},
        blocking=True,
    )

    mock_state_zone1.set_room_eq.assert_called_once_with(False)


async def test_switch_config_category(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test switch entity has config entity category."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_ROOM_EQ)
    assert entry is not None
    assert entry.entity_category == "config"


async def test_room_eq_none(
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


async def test_switch_connection_error_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test ConnectionFailed on turn_on raises HomeAssistantError."""
    mock_state_zone1.set_room_eq = MagicMock(side_effect=ConnectionFailed)

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {ATTR_ENTITY_ID: ENTITY_ROOM_EQ},
            blocking=True,
        )


async def test_switch_connection_error_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test ConnectionFailed on turn_off raises HomeAssistantError."""
    mock_state_zone1.set_room_eq = MagicMock(side_effect=ConnectionFailed)

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch",
            "turn_off",
            {ATTR_ENTITY_ID: ENTITY_ROOM_EQ},
            blocking=True,
        )
