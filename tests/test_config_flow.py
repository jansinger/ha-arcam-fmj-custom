"""Tests for Arcam FMJ config flow."""

from unittest.mock import AsyncMock, patch

from arcam.fmj.client import ConnectionFailed

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.arcam_fmj.const import DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import MOCK_HOST, MOCK_PORT, MOCK_UUID


async def test_user_flow_success(hass: HomeAssistant):
    """Test successful user-initiated config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "custom_components.arcam_fmj.config_flow.get_uniqueid_from_host",
            return_value=MOCK_UUID,
        ),
        patch(
            "custom_components.arcam_fmj.config_flow.Client",
        ) as mock_client_cls,
    ):
        client = mock_client_cls.return_value
        client.start = AsyncMock()
        client.stop = AsyncMock()

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": MOCK_HOST, "port": MOCK_PORT},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Arcam FMJ ({MOCK_HOST})"
    assert result["data"] == {"host": MOCK_HOST, "port": MOCK_PORT}
    assert result["result"].unique_id == MOCK_UUID


async def test_user_flow_connection_error(hass: HomeAssistant):
    """Test user flow shows error on connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.arcam_fmj.config_flow.get_uniqueid_from_host",
            return_value=None,
        ),
        patch(
            "custom_components.arcam_fmj.config_flow.Client",
        ) as mock_client_cls,
    ):
        client = mock_client_cls.return_value
        client.start = AsyncMock(side_effect=ConnectionFailed)
        client.stop = AsyncMock()

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": MOCK_HOST, "port": MOCK_PORT},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_no_uuid(hass: HomeAssistant):
    """Test user flow works without UUID (no SSDP available)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.arcam_fmj.config_flow.get_uniqueid_from_host",
            return_value=None,
        ),
        patch(
            "custom_components.arcam_fmj.config_flow.Client",
        ) as mock_client_cls,
    ):
        client = mock_client_cls.return_value
        client.start = AsyncMock()
        client.stop = AsyncMock()

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": MOCK_HOST, "port": MOCK_PORT},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id is None


async def test_ssdp_flow(hass: HomeAssistant):
    """Test SSDP discovery flow."""
    from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo

    discovery_info = SsdpServiceInfo(
        ssdp_usn="mock_usn",
        ssdp_st="mock_st",
        ssdp_location=f"http://{MOCK_HOST}:8080/description.xml",
        upnp={"UDN": f"uuid:{MOCK_UUID}"},
    )

    with patch(
        "custom_components.arcam_fmj.config_flow.get_uniqueid_from_udn",
        return_value=MOCK_UUID,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=discovery_info,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with patch(
        "custom_components.arcam_fmj.config_flow.Client",
    ) as mock_client_cls:
        client = mock_client_cls.return_value
        client.start = AsyncMock()
        client.stop = AsyncMock()

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == MOCK_UUID


async def test_ssdp_flow_no_uuid(hass: HomeAssistant):
    """Test SSDP flow aborts when UDN cannot be parsed."""
    from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo

    discovery_info = SsdpServiceInfo(
        ssdp_usn="mock_usn",
        ssdp_st="mock_st",
        ssdp_location=f"http://{MOCK_HOST}:8080/description.xml",
        upnp={"UDN": "invalid"},
    )

    with patch(
        "custom_components.arcam_fmj.config_flow.get_uniqueid_from_udn",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=discovery_info,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


# --- Options flow tests ---


async def test_options_flow_defaults(hass: HomeAssistant):
    """Test options flow shows default values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": MOCK_HOST, "port": MOCK_PORT},
        unique_id=MOCK_UUID,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_custom_values(hass: HomeAssistant):
    """Test options flow saves custom values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": MOCK_HOST, "port": MOCK_PORT},
        unique_id=MOCK_UUID,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"poll_interval": 30, "zone2_enabled": False},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"poll_interval": 30, "zone2_enabled": False}
