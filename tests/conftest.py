"""Fixtures for Arcam FMJ integration tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.arcam_fmj.const import DOMAIN

MOCK_HOST = "192.168.1.100"
MOCK_PORT = 50000
MOCK_UUID = "test-uuid-1234"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


def _create_mock_state(zone: int, client: MagicMock) -> MagicMock:
    """Create a mock State object for a given zone."""
    state = MagicMock()
    state.zn = zone
    state.client = client
    state.model = "AV40"
    state.start = AsyncMock()
    state.stop = AsyncMock()
    state.update = AsyncMock()

    # Power / volume / mute
    state.get_power.return_value = True
    state.get_volume.return_value = 50
    state.get_mute.return_value = False

    # Source
    from arcam.fmj import SourceCodes

    state.get_source.return_value = SourceCodes.PVR
    state.get_source_list.return_value = [
        SourceCodes.CD,
        SourceCodes.BD,
        SourceCodes.PVR,
        SourceCodes.SAT,
        SourceCodes.FM,
        SourceCodes.DAB,
    ]

    # Decode mode
    from arcam.fmj import DecodeModeMCH

    state.get_decode_mode.return_value = DecodeModeMCH.MULTI_CHANNEL
    state.get_decode_modes.return_value = [
        DecodeModeMCH.STEREO_DOWNMIX,
        DecodeModeMCH.MULTI_CHANNEL,
    ]

    # Audio / video
    state.get_incoming_audio_format.return_value = (None, None)
    state.get_incoming_video_parameters.return_value = None
    state.get_incoming_audio_sample_rate.return_value = 0

    # Tuner
    state.get_tuner_preset.return_value = None
    state.get_preset_details.return_value = {}
    state.get_dab_station.return_value = None
    state.get_dls_pdt.return_value = None
    state.get_rds_information.return_value = None

    # Number entity controls
    state.get_bass.return_value = 14  # 0x0E = neutral (offset 14 -> displayed as 0)
    state.get_treble.return_value = 14
    state.get_balance.return_value = 13  # offset 13 -> displayed as 0
    state.get_subwoofer_trim.return_value = 14
    state.get_lipsync_delay.return_value = 0

    # Select entity controls
    state.get_display_brightness.return_value = 2
    state.get_compression.return_value = 0

    # Switch -> Select: Room EQ now returns int (0=Off, 1-3=presets)
    state.get_room_eq.return_value = 1

    # New HDA series getters
    state.get_network_playback_status.return_value = None
    state.get_dolby_audio.return_value = None
    state.get_now_playing_info.return_value = None
    state.get_bluetooth_status.return_value = None
    state.get_room_eq_names.return_value = None
    state.get_hdmi_settings.return_value = None
    state.get_zone_settings.return_value = None

    # Async setters
    state.set_power = AsyncMock()
    state.set_volume = AsyncMock()
    state.set_mute = AsyncMock()
    state.set_source = AsyncMock()
    state.set_decode_mode = AsyncMock()
    state.inc_volume = AsyncMock()
    state.dec_volume = AsyncMock()
    state.set_tuner_preset = AsyncMock()
    state.set_bass = AsyncMock()
    state.set_treble = AsyncMock()
    state.set_balance = AsyncMock()
    state.set_subwoofer_trim = AsyncMock()
    state.set_lipsync_delay = AsyncMock()
    state.set_display_brightness = AsyncMock()
    state.set_compression = AsyncMock()
    state.set_room_eq = AsyncMock()
    state.set_dolby_audio = AsyncMock()

    return state


@pytest.fixture
def mock_client():
    """Create a mock Arcam client."""
    client = MagicMock()
    client.host = MOCK_HOST
    client.port = MOCK_PORT
    client.connected = True
    client.started = True
    client.start = AsyncMock()
    client.stop = AsyncMock()
    return client


@pytest.fixture
def mock_state_zone1(mock_client):
    """Create a mock State for zone 1."""
    return _create_mock_state(1, mock_client)


@pytest.fixture
def mock_state_zone2(mock_client):
    """Create a mock State for zone 2."""
    state = _create_mock_state(2, mock_client)
    state.get_power.return_value = False
    return state


@pytest.fixture
def mock_config_entry(hass):
    """Create and register a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": MOCK_HOST, "port": MOCK_PORT},
        unique_id=MOCK_UUID,
        title=f"Arcam FMJ ({MOCK_HOST})",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_setup_entry(mock_client, mock_state_zone1, mock_state_zone2):
    """Patch Client and State constructors for integration setup."""
    with (
        patch(
            "custom_components.arcam_fmj.Client",
            return_value=mock_client,
        ),
        patch(
            "custom_components.arcam_fmj.State",
            side_effect=[mock_state_zone1, mock_state_zone2],
        ),
        patch(
            "custom_components.arcam_fmj._run_client",
            return_value=AsyncMock()(),
        ),
    ):
        yield


async def setup_integration(hass, mock_config_entry):
    """Set up the integration and wait for entities."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
