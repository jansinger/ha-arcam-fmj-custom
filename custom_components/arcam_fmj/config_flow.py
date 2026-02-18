"""Config flow to configure the Arcam FMJ component."""

from __future__ import annotations

from asyncio import timeout
from typing import Any
from urllib.parse import urlparse

from arcam.fmj.client import Client, ConnectionFailed
from arcam.fmj.utils import get_uniqueid_from_host, get_uniqueid_from_udn
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.ssdp import ATTR_UPNP_UDN, SsdpServiceInfo

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN


class ArcamFmjFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    host: str
    port: int

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return ArcamFmjOptionsFlowHandler(config_entry)

    async def _async_set_unique_id_and_update(
        self, host: str, port: int, uuid: str
    ) -> None:
        await self.async_set_unique_id(uuid)
        self._abort_if_unique_id_configured({CONF_HOST: host, CONF_PORT: port})

    async def _async_try_connect(self, host: str, port: int) -> bool:
        """Test connection to device. Returns True on success."""
        client = Client(host, port)
        try:
            await client.start()
        except ConnectionFailed:
            return False
        finally:
            await client.stop()
        return True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a user-initiated config flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                async with timeout(5):
                    uuid = await get_uniqueid_from_host(
                        async_get_clientsession(self.hass), user_input[CONF_HOST]
                    )
            except TimeoutError:
                uuid = None
            if uuid:
                await self._async_set_unique_id_and_update(
                    user_input[CONF_HOST], user_input[CONF_PORT], uuid
                )

            if await self._async_try_connect(
                user_input[CONF_HOST], user_input[CONF_PORT]
            ):
                return self.async_create_entry(
                    title=f"{DEFAULT_NAME} ({user_input[CONF_HOST]})",
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    },
                )

            errors["base"] = "cannot_connect"

        fields = {
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user-confirmation of discovered node."""
        placeholders = {"host": self.host}
        self.context["title_placeholders"] = placeholders

        if user_input is not None:
            if await self._async_try_connect(self.host, self.port):
                return self.async_create_entry(
                    title=f"{DEFAULT_NAME} ({self.host})",
                    data={CONF_HOST: self.host, CONF_PORT: self.port},
                )
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="confirm", description_placeholders=placeholders
        )

    async def async_step_ssdp(
        self, discovery_info: SsdpServiceInfo
    ) -> ConfigFlowResult:
        """Handle a discovered device."""
        host = str(urlparse(discovery_info.ssdp_location).hostname)
        port = DEFAULT_PORT
        uuid = get_uniqueid_from_udn(discovery_info.upnp[ATTR_UPNP_UDN])
        if not uuid:
            return self.async_abort(reason="cannot_connect")

        await self._async_set_unique_id_and_update(host, port, uuid)

        self.host = host
        self.port = DEFAULT_PORT
        return await self.async_step_confirm()


class ArcamFmjOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle options flow for Arcam FMJ."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "poll_interval",
                        default=self.options.get("poll_interval", 10),
                    ): vol.All(int, vol.Range(min=5, max=60)),
                    vol.Optional(
                        "zone2_enabled",
                        default=self.options.get("zone2_enabled", True),
                    ): bool,
                }
            ),
        )
