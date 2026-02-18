"""Read-only integration tests against a real Arcam device.

Run with: pytest tests/test_device.py --device 192.168.x.x [-v]
Skipped automatically when --device is not provided.
"""

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_socket
from pytest_homeassistant_custom_component.common import MockConfigEntry

from arcam.fmj.client import Client
from arcam.fmj.state import State

from custom_components.arcam_fmj import (
    _fetch_device_name,
    _resolve_api_model,
)
from custom_components.arcam_fmj.const import (
    DOMAIN,
    SIGNAL_CLIENT_STARTED,
)

from homeassistant.helpers.dispatcher import async_dispatcher_send

pytestmark = [
    pytest.mark.timeout(30),
]


def _skip_without_device(device_host):
    if device_host is None:
        pytest.skip("No --device specified")


def _entity_id(model: str, platform: str, name: str) -> str:
    """Build entity_id from model name, e.g. 'AV40' -> 'media_player.arcam_av40_zone_1'."""
    slug = model.lower().replace(" ", "_").replace("-", "_")
    return f"{platform}.arcam_{slug}_{name}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _enable_network(device_host):
    """Remove pytest_socket restrictions for live device tests."""
    _skip_without_device(device_host)
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(
        [device_host, "127.0.0.1"], allow_unix_socket=True
    )
    yield
    pytest_socket.disable_socket(allow_unix_socket=True)
    pytest_socket.socket_allow_hosts(["127.0.0.1"], allow_unix_socket=True)


@pytest.fixture
async def live_state(device_host, device_port):
    """Connect to real device and poll state (no HA involved)."""

    client = Client(device_host, device_port)
    model = await _fetch_device_name(client)
    api_model = _resolve_api_model(model)

    state_z1 = State(client, 1, api_model)
    state_z2 = State(client, 2, api_model)
    await state_z1.start()
    await state_z2.start()

    await client.start()
    process_task = asyncio.create_task(client.process())
    try:
        await state_z1.update()
        await state_z2.update()
        yield {
            "client": client,
            "state_z1": state_z1,
            "state_z2": state_z2,
            "model": model,
            "api_model": api_model,
        }
    finally:
        process_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await process_task
        await client.stop()


@pytest.fixture
async def live_integration(hass, device_host, device_port, live_state):
    """Set up the full HA integration backed by the real device."""
    client = live_state["client"]
    state_z1 = live_state["state_z1"]
    state_z2 = live_state["state_z2"]
    model = live_state["model"]

    # Ensure hass.http exists for static path registration
    if not hasattr(hass, "http") or hass.http is None:
        hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": device_host, "port": device_port},
        unique_id=f"live-{device_host}",
        title=f"Arcam FMJ ({device_host})",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.arcam_fmj.Client",
            return_value=client,
        ),
        patch(
            "custom_components.arcam_fmj.State",
            side_effect=[state_z1, state_z2],
        ),
        patch(
            "custom_components.arcam_fmj._fetch_device_name",
            new=AsyncMock(return_value=model),
        ),
        patch(
            "custom_components.arcam_fmj._run_client",
            return_value=AsyncMock()(),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Signal entities that client is connected so they become available
        async_dispatcher_send(hass, SIGNAL_CLIENT_STARTED, device_host)
        await hass.async_block_till_done()

        yield {**live_state, "entry": entry, "model_slug": model}


# ---------------------------------------------------------------------------
# Library-level tests (no HA)
# ---------------------------------------------------------------------------


async def test_device_connects(live_state):
    """Device responds to AMX Duet and returns a model name."""
    assert live_state["model"] is not None, "AMX Duet should return model name"
    assert len(live_state["model"]) > 0


async def test_device_state_poll(live_state):
    """State.update() populates essential values."""
    z1 = live_state["state_z1"]
    # Power must be known after a full poll
    assert z1.get_power() is not None, "Power state should be known"
    # Volume should be a number if powered on
    if z1.get_power():
        assert z1.get_volume() is not None, "Volume should be known when on"
        assert 0 <= z1.get_volume() <= 99
        assert z1.get_source() is not None, "Source should be known when on"


async def test_device_source_list(live_state):
    """Source list should have at least one entry."""
    z1 = live_state["state_z1"]
    sources = z1.get_source_list()
    assert len(sources) > 0, "Source list should not be empty"


async def test_device_decode_modes(live_state):
    """Decode modes should be available."""
    z1 = live_state["state_z1"]
    if z1.get_power():
        modes = z1.get_decode_modes()
        assert modes is not None, "Decode modes should be available when on"
        assert len(modes) > 0


# ---------------------------------------------------------------------------
# HA Entity tests (read-only)
# ---------------------------------------------------------------------------


async def test_entity_zone1_exists(live_integration, hass):
    """Zone 1 media player entity exists and is not unavailable."""
    model = live_integration["model_slug"]
    eid = _entity_id(model, "media_player", "zone_1")
    state = hass.states.get(eid)
    assert state is not None, f"Entity {eid} should exist"
    assert state.state != "unavailable"


async def test_entity_power_state(live_integration, hass):
    """Entity state is 'on' or 'off'."""
    model = live_integration["model_slug"]
    eid = _entity_id(model, "media_player", "zone_1")
    state = hass.states.get(eid)
    assert state.state in ("on", "off"), f"Expected on/off, got {state.state}"


async def test_entity_volume_in_range(live_integration, hass):
    """Volume level is between 0.0 and 1.0 when powered on."""
    model = live_integration["model_slug"]
    z1 = live_integration["state_z1"]
    if not z1.get_power():
        pytest.skip("Device is off")

    eid = _entity_id(model, "media_player", "zone_1")
    state = hass.states.get(eid)
    volume = state.attributes.get("volume_level")
    assert volume is not None, "Volume should be set when on"
    assert 0.0 <= volume <= 1.0, f"Volume {volume} out of range"


async def test_entity_source_in_list(live_integration, hass):
    """Active source is in the source list."""
    model = live_integration["model_slug"]
    z1 = live_integration["state_z1"]
    if not z1.get_power():
        pytest.skip("Device is off")

    eid = _entity_id(model, "media_player", "zone_1")
    state = hass.states.get(eid)
    source = state.attributes.get("source")
    source_list = state.attributes.get("source_list", [])
    assert source is not None
    assert source in source_list, f"Source {source} not in {source_list}"


async def test_entity_sound_mode(live_integration, hass):
    """Sound mode is available when powered on."""
    model = live_integration["model_slug"]
    z1 = live_integration["state_z1"]
    if not z1.get_power():
        pytest.skip("Device is off")

    eid = _entity_id(model, "media_player", "zone_1")
    state = hass.states.get(eid)
    sound_mode = state.attributes.get("sound_mode")
    sound_mode_list = state.attributes.get("sound_mode_list")
    assert sound_mode is not None, "Sound mode should be set when on"
    assert sound_mode_list is not None
    assert sound_mode in sound_mode_list


async def test_number_entities_have_values(live_integration, hass):
    """Number entities (bass, treble, etc.) have numeric values."""
    model = live_integration["model_slug"]
    z1 = live_integration["state_z1"]
    if not z1.get_power():
        pytest.skip("Device is off")

    for name in ("bass", "treble", "balance", "subwoofer_trim", "lip_sync_delay"):
        eid = _entity_id(model, "number", name)
        state = hass.states.get(eid)
        if state is None:
            continue  # Entity might not exist for all models
        assert state.state != "unavailable", f"{eid} is unavailable"
        if state.state != "unknown":
            val = float(state.state)
            assert isinstance(val, float), f"{eid} state is not numeric: {state.state}"


async def test_select_entities_have_values(live_integration, hass):
    """Select entities have valid option values."""
    model = live_integration["model_slug"]

    for name in ("display_brightness", "compression"):
        eid = _entity_id(model, "select", name)
        state = hass.states.get(eid)
        if state is None:
            continue
        assert state.state != "unavailable", f"{eid} is unavailable"
        if state.state != "unknown":
            options = state.attributes.get("options", [])
            assert state.state in options, f"{eid}: {state.state} not in {options}"


async def test_sensor_entities(live_integration, hass):
    """Sensor entities exist and are not unavailable."""
    model = live_integration["model_slug"]

    for name in ("audio_input_format", "audio_channels", "audio_sample_rate"):
        eid = _entity_id(model, "sensor", name)
        state = hass.states.get(eid)
        if state is None:
            continue
        assert state.state != "unavailable", f"{eid} is unavailable"


async def test_dump_all_entities(live_integration, hass, capsys):
    """Print all entities created by the integration (informational, always passes)."""
    entry = live_integration["entry"]
    model = live_integration["model_slug"]

    # Collect all states belonging to our config entry via entity registry
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)

    lines = [f"\n{'='*70}", f"  Arcam {model} — All Entities ({len(entities)})", f"{'='*70}"]

    for reg_entry in sorted(entities, key=lambda e: e.entity_id):
        state = hass.states.get(reg_entry.entity_id)
        val = state.state if state else "?"
        disabled = " (DISABLED)" if reg_entry.disabled_by else ""
        lines.append(f"\n  {reg_entry.entity_id}{disabled}")
        lines.append(f"    state: {val}")
        if state and state.attributes:
            for key, value in sorted(state.attributes.items()):
                # Truncate long lists for readability
                display = str(value)
                if len(display) > 80:
                    display = display[:77] + "..."
                lines.append(f"    {key}: {display}")

    lines.append(f"\n{'='*70}\n")

    with capsys.disabled():
        print("\n".join(lines))
