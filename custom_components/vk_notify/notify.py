"""
VK Notify v1.5.2 
Fixed: Dynamic auto_answer_callback injection for Carousels (templates).
Fixed: Safe payload parsing and default kwargs fallback.
"""
from __future__ import annotations

import json
import random
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_platform

from .const import CONF_ACCESS_TOKEN, CONF_PEER_ID, VK_API_VERSION
from .helpers import async_upload_file, async_upload_photo, parse_vk_formatting

VK_API_SEND = "https://api.vk.com/method/messages.send"
VK_API_EDIT = "https://api.vk.com/method/messages.edit"
VK_API_DELETE = "https://api.vk.com/method/messages.delete"
VK_API_WALL = "https://api.vk.com/method/wall.post"
VK_API_ACTIVITY = "https://api.vk.com/method/messages.setActivity"
VK_API_REACTION = "https://api.vk.com/method/messages.sendReaction"
VK_API_PIN = "https://api.vk.com/method/messages.pin"
VK_API_UNPIN = "https://api.vk.com/method/messages.unpin"
VK_API_EVENT_ANSWER = "https://api.vk.com/method/messages.sendMessageEventAnswer"
VK_API_USERS_GET = "https://api.vk.com/method/users.get"
VK_API_MESSAGES_EDIT_CHAT = "https://api.vk.com/method/messages.editChat"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([VkNotifyEntity(hass, entry)])
    platform = entity_platform.async_get_current_platform()

    COMMON_FIELDS = {
        vol.Optional("disable_mentions"): cv.boolean,
        vol.Optional("payload"): cv.string,
        vol.Optional("keyboard"): dict,
        vol.Optional("inline_keyboard"): cv.boolean,
        vol.Optional("auto_answer_callback"): cv.boolean,
        vol.Optional("reply_to"): cv.positive_int,
        vol.Optional("parse_mode", default="html"): vol.In(["html", "markdown", "markdownv2", "plain"])
    }

    platform.async_register_entity_service("send_message", {vol.Required("message"): cv.string, vol.Optional("title"): cv.string, vol.Optional("attachment"): cv.string, vol.Optional("template"): dict, vol.Optional("lat"): cv.string, vol.Optional("long"): cv.string, **COMMON_FIELDS}, "async_send_message", supports_response=SupportsResponse.OPTIONAL)
    platform.async_register_entity_service("send_photo", {vol.Optional("url"): cv.string, vol.Optional("file"): cv.string, vol.Optional("message"): cv.string, **COMMON_FIELDS}, "async_send_photo", supports_response=SupportsResponse.OPTIONAL)
    platform.async_register_entity_service("send_file", {vol.Required("file"): cv.string, vol.Optional("message"): cv.string, **COMMON_FIELDS}, "async_send_file", supports_response=SupportsResponse.OPTIONAL)
    platform.async_register_entity_service("send_voice", {vol.Required("file"): cv.string, vol.Optional("message"): cv.string, **COMMON_FIELDS}, "async_send_voice", supports_response=SupportsResponse.OPTIONAL)
    platform.async_register_entity_service("edit_message", {vol.Required("message"): cv.string, vol.Optional("message_id"): cv.positive_int, vol.Optional("conversation_message_id"): cv.positive_int, vol.Optional("attachment"): cv.string, vol.Optional("keyboard"): dict, vol.Optional("disable_mentions"): cv.boolean, vol.Optional("parse_mode", default="html"): vol.In(["html", "markdown", "markdownv2", "plain"])}, "async_edit_message")
    platform.async_register_entity_service("wall_post", {vol.Optional("message"): cv.string, vol.Optional("file"): cv.string}, "async_wall_post", supports_response=SupportsResponse.OPTIONAL)
    platform.async_register_entity_service("delete_message", {vol.Optional("message_id"): cv.positive_int, vol.Optional("conversation_message_id"): cv.positive_int}, "async_delete_message")
    platform.async_register_entity_service("set_activity", {vol.Required("type"): vol.In(["typing", "audiomsg"])}, "async_set_activity")
    platform.async_register_entity_service("send_reaction", {vol.Required("conversation_message_id"): cv.positive_int, vol.Required("reaction_id"): cv.positive_int}, "async_send_reaction")
    platform.async_register_entity_service("pin_message", {vol.Optional("message_id"): cv.positive_int, vol.Optional("conversation_message_id"): cv.positive_int}, "async_pin_message")
    platform.async_register_entity_service("unpin_message", {vol.Optional("message_id"): cv.positive_int, vol.Optional("conversation_message_id"): cv.positive_int}, "async_unpin_message")
    platform.async_register_entity_service("send_sticker", {vol.Required("sticker_id"): cv.positive_int, vol.Optional("reply_to"): cv.positive_int}, "async_send_sticker", supports_response=SupportsResponse.OPTIONAL)
    platform.async_register_entity_service("edit_chat", {vol.Required("title"): cv.string}, "async_edit_chat")
    platform.async_register_entity_service("get_user_info", {vol.Required("user_id"): vol.Any(cv.positive_int, cv.string)}, "async_get_user_info", supports_response=SupportsResponse.ONLY)
    platform.async_register_entity_service("answer_callback", {vol.Required("event_id"): cv.string, vol.Required("user_id"): vol.Any(cv.positive_int, cv.string), vol.Optional("message"): cv.string}, "async_answer_callback")

class VkNotifyEntity(NotifyEntity):
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass, self._entry = hass, entry
        self._access_token: str = entry.data[CONF_ACCESS_TOKEN]
        self._peer_id: int = entry.data[CONF_PEER_ID]
        self._last_message_id, self._last_cmid = None, None
        self._attr_unique_id = entry.entry_id
        base_name = entry.data.get("name", "VK Notify")
        self._attr_name = f"{base_name} {self._peer_id}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"peer_id": self._peer_id, "last_message_id": self._last_message_id, "last_cmid": self._last_cmid}

    async def _internal_send(self, endpoint: str, params: dict) -> ServiceResponse:
        session = async_get_clientsession(self.hass)
        params.update({"access_token": self._access_token, "v": VK_API_VERSION})
        if endpoint == VK_API_SEND:
            params.update({"peer_ids": str(self._peer_id), "random_id": random.randint(0, 2**31)})
            params.pop("peer_id", None)
        else: params.setdefault("peer_id", self._peer_id)

        try:
            async with session.post(endpoint, data=params) as resp:
                res = await resp.json()
                if "error" in res: raise HomeAssistantError(f"VK API Error: {res['error']}")
                if endpoint == VK_API_SEND and "response" in res:
                    msg = res["response"][0] if isinstance(res["response"], list) else res["response"]
                    if isinstance(msg, dict):
                        self._last_message_id = msg.get("message_id") or msg.get("id")
                        self._last_cmid = msg.get("conversation_message_id")
                    else: self._last_message_id = msg
                    self.async_write_ha_state()
                    return {"message_id": self._last_message_id, "conversation_message_id": self._last_cmid}
                return res.get("response")
        except Exception as e: raise HomeAssistantError(f"Error: {e}")

    def _prepare_reply(self, params: dict, reply_to: int | None) -> None:
        if not reply_to: return
        if self._peer_id >= 2000000000:
            params["forward"] = json.dumps({"peer_id": self._peer_id, "conversation_message_ids": [reply_to], "is_reply": 1}, ensure_ascii=False)
        else: params["reply_to"] = reply_to

    def _inject_auto_answer(self, buttons_container: list) -> None:
        """Рекурсивно ищет кнопки и безопасно инжектит флаг _ha_auto."""
        for item in buttons_container:
            if isinstance(item, list):
                self._inject_auto_answer(item)
            elif isinstance(item, dict):
                if item.get("action", {}).get("type") == "callback":
                    act = item["action"]
                    p = act.get("payload", "{}")
                    try:
                        p_obj = json.loads(p) if isinstance(p, str) else p
                        if not isinstance(p_obj, dict):
                            p_obj = {"value": p_obj}
                    except ValueError:
                        p_obj = {"value": p}
                    
                    p_obj["_ha_auto"] = True
                    act["payload"] = json.dumps(p_obj, ensure_ascii=False)

    def _apply_common_params(self, params: dict, kwargs: dict) -> None:
        if kwargs.get("disable_mentions"): params["disable_mentions"] = 1
        if "payload" in kwargs: params["payload"] = kwargs["payload"]
        
        # Получаем настройку (по умолчанию True, как в services.yaml)
        auto_answer = kwargs.get("auto_answer_callback", True)
        
        # Обработка обычной клавиатуры
        if "keyboard" in kwargs:
            kb = kwargs["keyboard"]
            if isinstance(kb, dict):
                if "inline_keyboard" in kwargs: kb["inline"] = kwargs["inline_keyboard"]
                elif "inline" not in kb: kb["inline"] = True
                
                if auto_answer:
                    self._inject_auto_answer(kb.get("buttons", []))
                        
            params["keyboard"] = json.dumps(kb, ensure_ascii=False)
            
        # Обработка каруселей (Template)
        if "template" in kwargs:
            tpl = kwargs["template"]
            if auto_answer and isinstance(tpl, dict) and "elements" in tpl:
                for el in tpl.get("elements", []):
                    if "buttons" in el:
                        self._inject_auto_answer(el["buttons"])
            params["template"] = json.dumps(tpl, ensure_ascii=False)

    async def async_send_message(self, message: str, title: str | None = None, **kwargs) -> ServiceResponse:
        if title: message = f"{title}\n\n{message}"
        clean_msg, fmt_data = parse_vk_formatting(message, kwargs.get("parse_mode", "html"))
        params = {"message": clean_msg}
        if fmt_data: params["format_data"] = fmt_data
        if "attachment" in kwargs: params["attachment"] = kwargs["attachment"]
        self._apply_common_params(params, kwargs)
        self._prepare_reply(params, kwargs.get("reply_to"))
        return await self._internal_send(VK_API_SEND, params)

    async def async_send_photo(self, **kwargs) -> ServiceResponse:
        clean_msg, fmt_data = parse_vk_formatting(kwargs.get("message", ""), kwargs.get("parse_mode", "html"))
        params = {"message": clean_msg}
        if "url" in kwargs or "file" in kwargs:
            params["attachment"] = await async_upload_photo(self.hass, self._access_token, self._peer_id, url=kwargs.get("url"), filepath=kwargs.get("file"))
        if fmt_data: params["format_data"] = fmt_data
        self._apply_common_params(params, kwargs)
        self._prepare_reply(params, kwargs.get("reply_to"))
        return await self._internal_send(VK_API_SEND, params)

    async def async_send_file(self, **kwargs) -> ServiceResponse:
        clean_msg, fmt_data = parse_vk_formatting(kwargs.get("message", ""), kwargs.get("parse_mode", "html"))
        params = {"message": clean_msg, "attachment": await async_upload_file(self.hass, self._access_token, self._peer_id, kwargs["file"])}
        if fmt_data: params["format_data"] = fmt_data
        self._apply_common_params(params, kwargs)
        self._prepare_reply(params, kwargs.get("reply_to"))
        return await self._internal_send(VK_API_SEND, params)

    async def async_send_voice(self, **kwargs) -> ServiceResponse:
        clean_msg, fmt_data = parse_vk_formatting(kwargs.get("message", ""), kwargs.get("parse_mode", "html"))
        params = {"message": clean_msg, "attachment": await async_upload_file(self.hass, self._access_token, self._peer_id, kwargs["file"])}
        if fmt_data: params["format_data"] = fmt_data
        self._apply_common_params(params, kwargs)
        self._prepare_reply(params, kwargs.get("reply_to"))
        return await self._internal_send(VK_API_SEND, params)

    async def async_edit_message(self, message: str, **kwargs) -> None:
        clean_msg, fmt_data = parse_vk_formatting(message, kwargs.get("parse_mode", "html"))
        params = {"message": clean_msg}
        if fmt_data: params["format_data"] = fmt_data
        if "attachment" in kwargs: params["attachment"] = kwargs["attachment"]
        if "keyboard" in kwargs: params["keyboard"] = json.dumps(kwargs["keyboard"], ensure_ascii=False)
        if kwargs.get("message_id"): params["message_id"] = kwargs["message_id"]
        elif kwargs.get("conversation_message_id"): params["conversation_message_id"] = kwargs["conversation_message_id"]
        if kwargs.get("disable_mentions"): params["disable_mentions"] = 1
        await self._internal_send(VK_API_EDIT, params)

    async def async_wall_post(self, **kwargs) -> ServiceResponse:
        clean_msg, _ = parse_vk_formatting(kwargs.get("message", ""), kwargs.get("parse_mode", "html"))
        params = {"owner_id": f"-{self.hass.data['vk_notify'][self._entry.entry_id]['data']['group_id']}", "message": clean_msg}
        if kwargs.get("file"): params["attachments"] = await async_upload_file(self.hass, self._access_token, self._peer_id, kwargs["file"])
        return await self._internal_send(VK_API_WALL, params)

    async def async_delete_message(self, **kwargs) -> None:
        params = {"delete_for_all": 1}
        if kwargs.get("message_id"): params["message_ids"] = kwargs["message_id"]
        if kwargs.get("conversation_message_id"): params["cmids"] = kwargs["conversation_message_id"]
        await self._internal_send(VK_API_DELETE, params)

    async def async_send_reaction(self, conversation_message_id: int, reaction_id: int, **kwargs) -> None:
        await self._internal_send(VK_API_REACTION, {"cmid": conversation_message_id, "reaction_id": reaction_id})

    async def async_pin_message(self, **kwargs) -> None:
        params = {}
        if kwargs.get("message_id"): params["message_id"] = kwargs["message_id"]
        elif kwargs.get("conversation_message_id"): params["conversation_message_id"] = kwargs["conversation_message_id"]
        await self._internal_send(VK_API_PIN, params)

    async def async_unpin_message(self, **kwargs) -> None:
        params = {}
        if kwargs.get("message_id"): params["message_id"] = kwargs["message_id"]
        elif kwargs.get("conversation_message_id"): params["conversation_message_id"] = kwargs["conversation_message_id"]
        await self._internal_send(VK_API_UNPIN, params)

    async def async_answer_callback(self, event_id: str, user_id: int | str, message: str | None = None, **kwargs) -> None:
        params = {"event_id": event_id, "user_id": user_id}
        if message: params["event_data"] = json.dumps({"type": "show_snackbar", "text": message[:90]}, ensure_ascii=False)
        await self._internal_send(VK_API_EVENT_ANSWER, params)

    async def async_get_user_info(self, user_id: int | str, **kwargs) -> ServiceResponse:
        uid = str(user_id).replace("[VK ID: ", "").replace("]", "").strip()
        uid_int = int(uid) if uid.lstrip('-').isdigit() else 0
        if not uid_int or uid_int >= 2000000000: return {"full_name": "Система", "is_online": False}
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(VK_API_USERS_GET, data={"user_ids": str(uid_int), "fields": "online,last_seen", "lang": "ru", "v": VK_API_VERSION, "access_token": self._access_token}) as resp:
                res = await resp.json()
                if "response" in res and res["response"]:
                    u = res["response"][0]
                    return {
                        "full_name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
                        "is_online": bool(u.get("online", 0)),
                        "last_seen": u.get("last_seen", {}).get("time", 0)
                    }
        except Exception: pass
        return {"full_name": "Неизвестно", "is_online": False, "last_seen": 0}

    async def async_send_sticker(self, sticker_id: int, **kwargs) -> ServiceResponse:
        params = {"sticker_id": sticker_id}
        self._prepare_reply(params, kwargs.get("reply_to"))
        return await self._internal_send(VK_API_SEND, params)

    async def async_set_activity(self, type: str, **kwargs) -> None:
        await self._internal_send(VK_API_ACTIVITY, {"type": type})

    async def async_edit_chat(self, title: str, **kwargs) -> None:
        if self._peer_id < 2000000000: raise HomeAssistantError("Only for group chats")
        await self._internal_send(VK_API_MESSAGES_EDIT_CHAT, {"chat_id": self._peer_id - 2000000000, "title": title})