"""
VK Notify config_flow.py v1.5.2
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_GROUP_ID,
    CONF_MODE,
    CONF_PEER_ID,
    DOMAIN,
    MODE_API,
    MODE_LONGPOLL,
    VK_API_CONVERSATIONS,
    VK_API_VERSION,
)

STEP_TOKEN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional("name", default="VK Notify"): str,
    }
)


async def _detect_group_id(hass, access_token: str) -> int | None:
    """Try to auto-detect group_id from a community token via groups.getById."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            "https://api.vk.com/method/groups.getById",
            params={"access_token": access_token, "v": VK_API_VERSION},
        ) as resp:
            data = await resp.json()
        groups = data.get("response", {}).get("groups", [])
        if groups:
            return groups[0]["id"]
    except Exception:
        pass
    return None


async def _check_longpoll_access(hass, access_token: str, group_id: int) -> bool:
    """Return True if the token can call groups.getLongPollServer."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            "https://api.vk.com/method/groups.getLongPollServer",
            params={"access_token": access_token, "group_id": group_id, "v": VK_API_VERSION},
        ) as resp:
            data = await resp.json()
        return "error" not in data
    except Exception:
        return False


async def _validate_token(hass, access_token: str) -> bool:
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            "https://api.vk.com/method/users.get",
            params={"access_token": access_token, "v": VK_API_VERSION},
        ) as resp:
            data = await resp.json()
            return "error" not in data
    except Exception:
        return False


def _build_conversations(response: dict) -> tuple[dict[str, str], set[str]]:
    profiles = {p["id"]: f"{p['first_name']} {p['last_name']}" for p in response.get("profiles", [])}
    groups = {g["id"]: g["name"] for g in response.get("groups", [])}

    all_options: dict[str, str] = {}
    writable_ids: set[str] = set()

    for item in response.get("items", []):
        conv = item["conversation"]
        peer = conv["peer"]
        peer_id: int = peer["id"]
        peer_type: str = peer["type"]
        can_write: bool = conv.get("can_write", {}).get("allowed", True)

        if peer_type == "chat":
            name = conv.get("chat_settings", {}).get("title", f"Chat {peer_id}")
        elif peer_type == "user":
            name = profiles.get(peer_id, str(peer_id))
        elif peer_type == "group":
            name = groups.get(abs(peer_id), str(peer_id))
        else:
            name = str(peer_id)

        key = str(peer_id)
        label = f"{name} ({peer_id})" if can_write else f"⛔ {name} ({peer_id})"
        all_options[key] = label
        if can_write:
            writable_ids.add(key)

    return all_options, writable_ids


async def _get_conversations(hass, access_token: str) -> tuple[dict[str, str], set[str]]:
    session = async_get_clientsession(hass)
    async with session.get(
        VK_API_CONVERSATIONS,
        params={"access_token": access_token, "extended": 1, "count": 200, "v": VK_API_VERSION},
    ) as resp:
        data = await resp.json()

    if "error" in data:
        return {}, set()

    return _build_conversations(data["response"])


class VkNotifyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._access_token: str = ""
        self._name: str = "VK Notify"
        self._mode: str = MODE_API
        self._group_id: int | None = None

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                valid = await _validate_token(self.hass, user_input[CONF_ACCESS_TOKEN])
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                if not valid:
                    errors["base"] = "invalid_token"
                else:
                    self._access_token = user_input[CONF_ACCESS_TOKEN]
                    self._name = user_input.get("name", "VK Notify")
                    self._group_id = await _detect_group_id(self.hass, self._access_token)
                    return await self.async_step_select_mode()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_TOKEN_SCHEMA,
            errors=errors,
            description_placeholders={
                "docs_url": "https://udocs.ru/posts/home-assistant/integrations/otpravka-uvedomleniy-v-vk"
            },
        )

    async def async_step_select_mode(self, user_input=None):
        errors = {}

        if user_input is not None:
            mode = user_input[CONF_MODE]

            if mode == MODE_LONGPOLL and not self._group_id:
                errors["base"] = "group_id_required"
            elif mode == MODE_LONGPOLL:
                ok = await _check_longpoll_access(self.hass, self._access_token, self._group_id)
                if not ok:
                    errors["base"] = "longpoll_no_access"
                else:
                    self._mode = mode
                    return await self.async_step_select_chat()
            else:
                self._mode = mode
                return await self.async_step_select_chat()

        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=MODE_API): SelectSelector(
                    SelectSelectorConfig(
                        options=[MODE_API, MODE_LONGPOLL],
                        mode=SelectSelectorMode.LIST,
                        translation_key="mode",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_mode",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_select_chat(self, user_input=None):
        errors = {}
        all_options, _ = await _get_conversations(self.hass, self._access_token)

        if user_input is not None:
            peer_id_str = str(user_input[CONF_PEER_ID]).strip()
            
            # Подхватываем имя, если чат есть в списке, иначе просто пишем ID
            chat_label = all_options.get(peer_id_str, f"Чат {peer_id_str}")
            card_title = f"{self._name}: {chat_label}"

            return self.async_create_entry(
                title=card_title,
                data={
                    CONF_ACCESS_TOKEN: self._access_token,
                    CONF_PEER_ID: int(peer_id_str),
                    CONF_MODE: self._mode,
                    CONF_GROUP_ID: self._group_id,
                    "name": self._name,
                },
            )

        # Подготавливаем опции для выпадающего списка
        options = [{"value": str(k), "label": v} for k, v in all_options.items()]

        return self.async_show_form(
            step_id="select_chat",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PEER_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            custom_value=True, # РАЗРЕШАЕТ РУЧНОЙ ВВОД!
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        self._access_token = entry.data[CONF_ACCESS_TOKEN]

        errors = {}
        all_options, _ = await _get_conversations(self.hass, self._access_token)

        if user_input is not None:
            peer_id_str = str(user_input[CONF_PEER_ID]).strip()
            
            chat_label = all_options.get(peer_id_str, f"Чат {peer_id_str}")
            base_name = entry.data.get("name", "VK Notify")
            self.hass.config_entries.async_update_entry(
                entry, title=f"{base_name}: {chat_label}"
            )
            
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, CONF_PEER_ID: int(peer_id_str)},
            )

        options = [{"value": str(k), "label": v} for k, v in all_options.items()]

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PEER_ID, default=str(entry.data[CONF_PEER_ID])): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            custom_value=True, # РАЗРЕШАЕТ РУЧНОЙ ВВОД ПРИ ПЕРЕНАСТРОЙКЕ!
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )