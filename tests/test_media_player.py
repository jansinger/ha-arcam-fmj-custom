"""Tests for Arcam FMJ media player entity."""

from unittest.mock import MagicMock

import pytest
from arcam.fmj import ConnectionFailed, NowPlayingInfo, SourceCodes, DecodeModeMCH
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.arcam_fmj.const import DOMAIN, EVENT_TURN_ON

from .conftest import MOCK_HOST, MOCK_UUID, setup_integration

ENTITY_ZONE1 = "media_player.arcam_av40_zone_1"
ENTITY_ZONE2 = "media_player.arcam_av40_zone_2"


async def test_setup_entities(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test that both zone entities are registered."""
    await setup_integration(hass, mock_config_entry)

    # Zone 1 is enabled by default
    state1 = hass.states.get(ENTITY_ZONE1)
    assert state1 is not None

    # Zone 2 is disabled by default but registered in entity registry
    registry = er.async_get(hass)
    entry = registry.async_get(ENTITY_ZONE2)
    assert entry is not None
    assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


async def test_zone1_state_on(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test zone 1 reports ON when powered."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.state == MediaPlayerState.ON


async def test_zone1_features(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test zone 1 has all features including sound mode."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    features = state.attributes["supported_features"]
    assert features & MediaPlayerEntityFeature.SELECT_SOURCE
    assert features & MediaPlayerEntityFeature.VOLUME_SET
    assert features & MediaPlayerEntityFeature.VOLUME_MUTE
    assert features & MediaPlayerEntityFeature.VOLUME_STEP
    assert features & MediaPlayerEntityFeature.TURN_ON
    assert features & MediaPlayerEntityFeature.TURN_OFF
    assert features & MediaPlayerEntityFeature.SELECT_SOUND_MODE
    assert features & MediaPlayerEntityFeature.BROWSE_MEDIA
    assert features & MediaPlayerEntityFeature.PLAY_MEDIA


async def test_volume_level(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
):
    """Test volume is reported as 0..1 range."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    # mock volume = 50, so 50/99 ≈ 0.505
    assert abs(state.attributes["volume_level"] - 50 / 99.0) < 0.01


async def test_source(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test current source is reported."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["source"] == "PVR"


async def test_source_list(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test source list contains expected sources."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    source_list = state.attributes["source_list"]
    assert "CD" in source_list
    assert "BD" in source_list
    assert "PVR" in source_list


async def test_sound_mode(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test current sound mode is reported."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["sound_mode"] == "MULTI_CHANNEL"


async def test_mute(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test mute state is reported."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["is_volume_muted"] is False


async def test_set_volume(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test setting volume level."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "volume_set",
        {ATTR_ENTITY_ID: ENTITY_ZONE1, "volume_level": 0.5},
        blocking=True,
    )

    mock_state_zone1.set_volume.assert_called_once_with(round(0.5 * 99.0))


async def test_volume_up(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test volume up."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "volume_up",
        {ATTR_ENTITY_ID: ENTITY_ZONE1},
        blocking=True,
    )

    mock_state_zone1.inc_volume.assert_called_once()


async def test_volume_down(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test volume down."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "volume_down",
        {ATTR_ENTITY_ID: ENTITY_ZONE1},
        blocking=True,
    )

    mock_state_zone1.dec_volume.assert_called_once()


async def test_mute_volume(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test muting volume."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "volume_mute",
        {ATTR_ENTITY_ID: ENTITY_ZONE1, "is_volume_muted": True},
        blocking=True,
    )

    mock_state_zone1.set_mute.assert_called_once_with(True)


async def test_select_source(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test selecting a source."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "select_source",
        {ATTR_ENTITY_ID: ENTITY_ZONE1, "source": "BD"},
        blocking=True,
    )

    mock_state_zone1.set_source.assert_called_once_with(SourceCodes.BD)


async def test_select_source_invalid(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test selecting an invalid source does not call set_source."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "select_source",
        {ATTR_ENTITY_ID: ENTITY_ZONE1, "source": "INVALID_SOURCE"},
        blocking=True,
    )

    mock_state_zone1.set_source.assert_not_called()


async def test_select_sound_mode(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test selecting a sound mode."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "select_sound_mode",
        {ATTR_ENTITY_ID: ENTITY_ZONE1, "sound_mode": "STEREO_DOWNMIX"},
        blocking=True,
    )

    mock_state_zone1.set_decode_mode.assert_called_once_with("STEREO_DOWNMIX")


async def test_turn_on_connected(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test turn on when device is connected (power state known)."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "turn_on",
        {ATTR_ENTITY_ID: ENTITY_ZONE1},
        blocking=True,
    )

    mock_state_zone1.set_power.assert_called_once_with(True)


async def test_turn_on_disconnected_fires_event(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test turn on fires event when power state is unknown."""
    mock_state_zone1.get_power.return_value = None
    await setup_integration(hass, mock_config_entry)

    events = []
    hass.bus.async_listen(EVENT_TURN_ON, lambda e: events.append(e))

    await hass.services.async_call(
        "media_player",
        "turn_on",
        {ATTR_ENTITY_ID: ENTITY_ZONE1},
        blocking=True,
    )

    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data[ATTR_ENTITY_ID] == ENTITY_ZONE1


async def test_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test turning off the device."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "turn_off",
        {ATTR_ENTITY_ID: ENTITY_ZONE1},
        blocking=True,
    )

    mock_state_zone1.set_power.assert_called_once_with(False)


async def test_connection_error_raises_ha_error(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test that ConnectionFailed is converted to HomeAssistantError."""
    mock_state_zone1.set_volume = MagicMock(side_effect=ConnectionFailed)

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {ATTR_ENTITY_ID: ENTITY_ZONE1, "volume_level": 0.5},
            blocking=True,
        )


async def test_media_title_dab(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test media title with DAB source."""
    mock_state_zone1.get_source.return_value = SourceCodes.DAB
    mock_state_zone1.get_dab_station.return_value = "BBC Radio 2"

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["media_title"] == "DAB - BBC Radio 2"
    assert state.attributes["media_content_type"] == MediaType.MUSIC


async def test_media_title_no_channel(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test media title falls back to source name when no channel info."""
    mock_state_zone1.get_source.return_value = SourceCodes.BD

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes.get("media_title") == "BD"


async def test_browse_media(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test media browsing returns presets."""
    from arcam.fmj import PresetDetail, PresetType

    mock_state_zone1.get_preset_details.return_value = {
        1: PresetDetail(index=1, type=PresetType.DAB, name="BBC Radio 2"),
        2: PresetDetail(index=2, type=PresetType.FM_RDS_NAME, name="Classic FM"),
    }

    await setup_integration(hass, mock_config_entry)

    # Access entity via the platform entities
    from homeassistant.helpers import entity_platform

    platforms = entity_platform.async_get_platforms(hass, DOMAIN)
    entity = None
    for platform in platforms:
        if platform.domain == "media_player":
            for ent in platform.entities.values():
                if ent.entity_id == ENTITY_ZONE1:
                    entity = ent
                    break

    assert entity is not None
    result = await entity.async_browse_media(None, None)

    assert result.title == "Arcam FMJ Receiver"
    assert len(result.children) == 2
    assert result.children[0].title == "BBC Radio 2"
    assert result.children[0].media_content_id == "preset:1"


async def test_play_media_preset(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test playing a preset."""
    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            ATTR_ENTITY_ID: ENTITY_ZONE1,
            "media_content_type": MediaType.MUSIC,
            "media_content_id": "preset:3",
        },
        blocking=True,
    )

    mock_state_zone1.set_tuner_preset.assert_called_once_with(3)


async def test_device_info(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
):
    """Test device info is set correctly."""
    await setup_integration(hass, mock_config_entry)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, MOCK_UUID)})
    assert device is not None
    assert device.manufacturer == "Arcam"
    assert device.model == "AV40"
    assert device.name == "Arcam AV40"


# --- Now Playing Info tests ---


async def test_media_title_network_now_playing(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test now playing info is used for network sources."""
    mock_state_zone1.get_source.return_value = SourceCodes.NET
    mock_state_zone1.get_now_playing_info.return_value = NowPlayingInfo(
        title="My Song",
        artist="The Artist",
        album="The Album",
    )
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["media_title"] == "My Song"


async def test_media_artist_network_now_playing(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test media artist from now playing info for network sources."""
    mock_state_zone1.get_source.return_value = SourceCodes.NET
    mock_state_zone1.get_now_playing_info.return_value = NowPlayingInfo(
        title="Song",
        artist="The Artist",
        album="Album",
    )
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["media_artist"] == "The Artist"


async def test_media_album_name_network(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test media album name from now playing info for network sources."""
    mock_state_zone1.get_source.return_value = SourceCodes.NET
    mock_state_zone1.get_now_playing_info.return_value = NowPlayingInfo(
        title="Song",
        artist="Artist",
        album="The Album",
    )
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["media_album_name"] == "The Album"


async def test_media_title_network_no_info(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test fallback when network source has no now playing info."""
    mock_state_zone1.get_source.return_value = SourceCodes.NET
    mock_state_zone1.get_now_playing_info.return_value = None
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes.get("media_title") == "NET"


async def test_media_artist_dab_unchanged(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test DAB source still uses get_dls_pdt for media artist."""
    mock_state_zone1.get_source.return_value = SourceCodes.DAB
    mock_state_zone1.get_dls_pdt.return_value = "Now: Great Song"
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["media_artist"] == "Now: Great Song"


async def test_media_content_type_network(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test network source with now playing reports music content type."""
    mock_state_zone1.get_source.return_value = SourceCodes.NET
    mock_state_zone1.get_now_playing_info.return_value = NowPlayingInfo(
        title="Song",
    )
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes["media_content_type"] == MediaType.MUSIC


# --- Companion artwork tests ---


async def test_media_image_from_companion_cast(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test artwork is pulled from companion Cast entity on same host."""
    mock_state_zone1.get_source.return_value = SourceCodes.NET
    mock_state_zone1.get_now_playing_info.return_value = NowPlayingInfo(title="Song")

    # Create companion Cast config entry with same host
    cast_entry = MockConfigEntry(
        domain="cast",
        data={"host": MOCK_HOST, "port": 8009},
        unique_id="cast-uuid",
    )
    cast_entry.add_to_hass(hass)

    # Register companion entity in entity registry
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "media_player",
        "cast",
        "cast-uuid",
        config_entry=cast_entry,
        suggested_object_id="arcam_cast",
    )

    # Set companion state with artwork
    hass.states.async_set("media_player.arcam_cast", "playing", {
        "entity_picture": "https://cdn.example.com/artwork.jpg",
    })

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes.get("entity_picture") == "https://cdn.example.com/artwork.jpg"


async def test_media_image_no_companion(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test no artwork when no companion entity exists."""
    mock_state_zone1.get_source.return_value = SourceCodes.NET
    mock_state_zone1.get_now_playing_info.return_value = NowPlayingInfo(title="Song")
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes.get("entity_picture") is None


async def test_media_image_non_network_source(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
    mock_state_zone1,
):
    """Test no artwork lookup for non-network sources even with companion."""
    mock_state_zone1.get_source.return_value = SourceCodes.BD

    # Create companion with artwork
    cast_entry = MockConfigEntry(
        domain="cast",
        data={"host": MOCK_HOST, "port": 8009},
        unique_id="cast-uuid-2",
    )
    cast_entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "media_player",
        "cast",
        "cast-uuid-2",
        config_entry=cast_entry,
        suggested_object_id="arcam_cast_2",
    )

    hass.states.async_set("media_player.arcam_cast_2", "playing", {
        "entity_picture": "https://cdn.example.com/artwork.jpg",
    })

    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ZONE1)
    assert state.attributes.get("entity_picture") is None
