"""Tests for Arcam FMJ integration setup and teardown."""

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .conftest import setup_integration


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
    mock_state_zone2,
):
    """Test successful setup of config entry."""
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_state_zone1.start.assert_called_once()
    mock_state_zone2.start.assert_called_once()


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
):
    """Test unloading config entry."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_runtime_data_set(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_client,
    mock_state_zone1,
    mock_state_zone2,
):
    """Test that runtime data is correctly populated."""
    await setup_integration(hass, mock_config_entry)

    data = mock_config_entry.runtime_data
    assert data.client is mock_client
    assert data.state_zone1 is mock_state_zone1
    assert data.state_zone2 is mock_state_zone2
    assert data.device_name == "Arcam AV40"
