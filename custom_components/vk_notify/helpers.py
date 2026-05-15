"""
VK Notify  helpers.py v1.5.2
Cleaned: Removed native video upload. Kept MarkdownV2, Photo, and File logic.
"""

from __future__ import annotations

import aiohttp
import re
import json
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    VK_API_DOC_SAVE, 
    VK_API_DOC_UPLOAD_SERVER, 
    VK_API_PHOTO_SAVE, 
    VK_API_PHOTO_UPLOAD_SERVER, 
    VK_API_VERSION
)

# ==========================================
# 1. ФУНКЦИИ ФОРМАТИРОВАНИЯ ТЕКСТА
# ==========================================

def encode_utf16_len(s: str) -> int:
    return len(s.encode('utf-16-le')) // 2

def parse_vk_formatting(text: str, parse_mode: str = "html") -> tuple[str, str | None]:
    if not isinstance(text, str):
        return str(text), None

    if parse_mode == "plain":
        return text.strip(), None

    if parse_mode == "markdownv2":
        text = re.sub(r'\\([_*\[\]()~`>#+\-=|{}.!])', r'\1', text)

    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text, flags=re.S)
    text = re.sub(r'(?<!\*)\*([^\s\*][^\*]*[^\s\*]|[^\s\*])\*(?!\*)', r'<i>\1</i>', text, flags=re.S)
    text = re.sub(r'__([^_]+)__', r'<u>\1</u>', text, flags=re.S)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    pattern = re.compile(r'<(/)?(b|i|u|a|strong|em)(?: [^>]+)?>', flags=re.IGNORECASE)
    
    clean_text = ""
    current_pos = 0
    utf16_offset = 0
    open_tags = []
    items = []
    
    for match in pattern.finditer(text):
        start, end = match.span()
        chunk = text[current_pos:start]
        clean_text += chunk
        utf16_offset += encode_utf16_len(chunk)
        
        is_closing = bool(match.group(1))
        tag_name = match.group(2).lower()
        if tag_name == 'strong': tag_name = 'b'
        elif tag_name == 'em': tag_name = 'i'
        
        if not is_closing:
            tag_info = {"tag": tag_name, "start": utf16_offset}
            if tag_name == 'a':
                href_match = re.search(r'href=["\']([^"\']+)["\']', match.group(0), flags=re.IGNORECASE)
                if href_match:
                    tag_info["url"] = href_match.group(1)
            open_tags.append(tag_info)
        else:
            for i in reversed(range(len(open_tags))):
                if open_tags[i]["tag"] == tag_name:
                    tag_info = open_tags.pop(i)
                    length = utf16_offset - tag_info["start"]
                    if length > 0:
                        vk_type = {"b": "bold", "i": "italic", "u": "underline", "a": "url"}[tag_name]
                        item = {"offset": tag_info["start"], "length": length, "type": vk_type}
                        if vk_type == "url" and "url" in tag_info:
                            item["url"] = tag_info["url"]
                        items.append(item)
                    break
        current_pos = end
    
    chunk = text[current_pos:]
    clean_text += chunk
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    
    format_data = None
    if items:
        format_data = json.dumps({"version": 1, "items": items}, ensure_ascii=False)
        
    return clean_text.strip(), format_data

# ==========================================
# 2. ФУНКЦИИ ЗАГРУЗКИ МЕДИАФАЙЛОВ
# ==========================================

async def async_upload_photo(hass: HomeAssistant, access_token: str, peer_id: int, url: str | None = None, filepath: str | None = None) -> str:
    """Загрузка фотографии в ВК."""
    session = async_get_clientsession(hass)
    
    async with session.get(VK_API_PHOTO_UPLOAD_SERVER, params={
        "access_token": access_token, "peer_id": peer_id, "v": VK_API_VERSION
    }) as resp:
        data = await resp.json()
    if "error" in data: raise HomeAssistantError(f"VK API error (photos.getMessagesUploadServer): {data['error']}")
    
    upload_url = data["response"]["upload_url"]
    form = aiohttp.FormData()

    if url:
        async with session.get(url) as img_resp:
            form.add_field("photo", await img_resp.read(), filename="image.jpg")
    elif filepath:
        if not hass.config.is_allowed_path(filepath):
            raise HomeAssistantError(f"Path '{filepath}' not allowed.")
        file_bytes = await hass.async_add_executor_job(lambda: open(filepath, "rb").read())
        form.add_field("photo", file_bytes, filename=filepath.split("/")[-1])
    else:
        raise HomeAssistantError("Neither URL nor filepath provided for photo upload.")

    async with session.post(upload_url, data=form) as resp:
        upload_result = await resp.json()

    if "error" in upload_result or not upload_result.get("photo"):
        raise HomeAssistantError(f"Photo upload error: {upload_result}")

    async with session.post(VK_API_PHOTO_SAVE, data={
        "access_token": access_token, "v": VK_API_VERSION,
        "photo": upload_result["photo"], "server": upload_result["server"], "hash": upload_result["hash"]
    }) as resp:
        data = await resp.json()
        
    if "error" in data: raise HomeAssistantError(f"VK API error (photos.saveMessagesPhoto): {data['error']}")

    photo = data["response"][0]
    access_key = photo.get("access_key", "")
    return f"photo{photo['owner_id']}_{photo['id']}{'_' + access_key if access_key else ''}"

async def async_upload_file(hass: HomeAssistant, access_token: str, peer_id: int, filepath: str) -> str:
    """Загрузка документов и голосовых сообщений."""
    session = async_get_clientsession(hass)
    if not hass.config.is_allowed_path(filepath):
        raise HomeAssistantError(f"Path '{filepath}' not allowed.")
        
    doc_type = "audio_message" if filepath.lower().endswith(".ogg") else "doc"

    async with session.get(VK_API_DOC_UPLOAD_SERVER, params={
        "access_token": access_token, "peer_id": peer_id, "type": doc_type, "v": VK_API_VERSION
    }) as resp:
        data = await resp.json()
    if "error" in data: raise HomeAssistantError(f"VK API error (docs.getUploadServer): {data['error']}")
    
    upload_url = data["response"]["upload_url"]
    filename = filepath.split("/")[-1]
    file_bytes = await hass.async_add_executor_job(lambda: open(filepath, "rb").read())
    
    form = aiohttp.FormData()
    form.add_field("file", file_bytes, filename=filename)
    
    async with session.post(upload_url, data=form) as resp:
        upload_result = await resp.json()

    async with session.get(VK_API_DOC_SAVE, params={
        "access_token": access_token, "v": VK_API_VERSION, "file": upload_result["file"], "title": filename
    }) as resp:
        data = await resp.json()
    if "error" in data: raise HomeAssistantError(f"VK API error (docs.save): {data['error']}")

    response = data["response"]
    obj = response.get("doc") or response.get("audio_message")
    attachment_type = "doc" if "doc" in response else "audio_message"
    access_key = obj.get("access_key", "")
    return f"{attachment_type}{obj['owner_id']}_{obj['id']}{'_' + access_key if access_key else ''}"