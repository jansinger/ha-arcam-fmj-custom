"""Tests for Arcam FMJ number entities."""

from unittest.mock import MagicMock

import pytest
from arcam.fmj import ConnectionFailed

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration

ENTITY_BASS = "number.arcam_fmj_192_168_1_100_bass"
ENTITY_TREBLE = "number.arcam_fmj_192_168_1_100_treble"
ENTITY_BALANCE = "number.arcam_fmj_192_168_1_100_balance"
ENTITY_SUB_TRIM = "number.arcam_fmj_192_168_1_100_subwoofer_trim"
ENTITY_LIPSYNC = "number.arcam_fmj_192_168_1_100_lip_sync_delay"


async def test_number_entities_created(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test all number entities are created."""
    await setup_integration(hass, mock_config_entry)

    # Enabled by default
    assert hass.states.get(ENTITY_BASS) is not None
    assert hass.states.get(ENTITY_TREBLE) is not None
    assert hass.states.get(ENTITY_BALANCE) is not None

    # Disabled by default but registered
    registry = er.async_get(hass)
    entry_sub = registry.async_get(ENTITY_SUB_TRIM)
    assert entry_sub is not None
    assert entry_sub.disabled_by == er.RegistryEntryDisabler.INTEGRATION

    entry_lip = registry.async_get(ENTITY_LIPSYNC)
    assert entry_lip is not None
    assert entry_lip.disabled_by == er.RegistryEntryDisabler.INTEGRATION


async def test_bass_neutral_value(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test bass reads neutral (0) when raw value equals offset."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_BASS)
    # Raw 14 - offset 14 = 0
    assert float(state.state) == 0.0


async def test_treble_neutral_value(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test treble reads neutral (0) when raw value equals offset."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_TREBLE)
    assert float(state.state) == 0.0


async def test_balance_neutral_value(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test balance reads neutral (0) when raw value equals offset."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_BALANCE)
    assert float(state.state) == 0.0


async def test_set_bass(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting bass value applies offset correctly."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: ENTITY_BASS, "value": 5},
        blocking=True,
    )

    # User value 5 + offset 14 = raw 19
    mock_state_zone1.set_bass.assert_called_once_with(19)


async def test_set_bass_negative(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting negative bass value."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: ENTITY_BASS, "value": -7},
        blocking=True,
    )

    # User value -7 + offset 14 = raw 7
    mock_state_zone1.set_bass.assert_called_once_with(7)


async def test_set_treble(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting treble value applies offset correctly."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: ENTITY_TREBLE, "value": -3},
        blocking=True,
    )

    # User value -3 + offset 14 = raw 11
    mock_state_zone1.set_treble.assert_called_once_with(11)


async def test_number_config_category(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test number entities have config entity category."""
    await setup_integration(hass, mock_config_entry)

    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_BASS)
    assert entry is not None
    assert entry.entity_category == "config"


async def test_number_none_value(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test number returns unknown when getter returns None."""
    mock_state_zone1.get_bass.return_value = None
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_BASS)
    assert state.state == "unknown"


async def test_number_connection_error(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test ConnectionFailed is raised as HomeAssistantError."""
    mock_state_zone1.set_bass = MagicMock(side_effect=ConnectionFailed)

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "number",
            "set_value",
            {ATTR_ENTITY_ID: ENTITY_BASS, "value": 5},
            blocking=True,
        )
