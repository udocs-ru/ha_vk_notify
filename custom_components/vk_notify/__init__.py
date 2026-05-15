"""
VK Notify  __init__.py v1.5.2
Cleaned: All services moved to notify.py
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ACCESS_TOKEN, CONF_GROUP_ID, CONF_MODE, DOMAIN, MODE_LONGPOLL
from .longpoll import VkLongPollManager

PLATFORMS = [Platform.NOTIFY]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("lp_managers", {})
    hass.data[DOMAIN][entry.entry_id] = {"data": entry.data}
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    if entry.data.get(CONF_MODE) == MODE_LONGPOLL:
        group_id: int = entry.data[CONF_GROUP_ID]
        lp_managers: dict = hass.data[DOMAIN]["lp_managers"]
        if group_id not in lp_managers:
            manager = VkLongPollManager(hass, entry.data[CONF_ACCESS_TOKEN], group_id)
            lp_managers[group_id] = {"manager": manager, "refcount": 1}
            manager.start()
        else:
            lp_managers[group_id]["refcount"] += 1
            
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.data.get(CONF_MODE) == MODE_LONGPOLL:
        group_id: int = entry.data[CONF_GROUP_ID]
        lp_managers: dict = hass.data[DOMAIN]["lp_managers"]
        if group_id in lp_managers:
            lp_managers[group_id]["refcount"] -= 1
            if lp_managers[group_id]["refcount"] <= 0:
                await lp_managers[group_id]["manager"].stop()
                del lp_managers[group_id]
                
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok: 
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok