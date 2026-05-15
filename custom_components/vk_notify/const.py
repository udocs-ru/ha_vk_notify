"""
VK Notify  __init__.py v1.5.2
Cleaned: All services moved to const.py
"""

DOMAIN = "vk_notify"

CONF_ACCESS_TOKEN = "access_token"
CONF_PEER_ID = "peer_id"
CONF_MODE = "mode"
CONF_GROUP_ID = "group_id"

MODE_API = "api"
MODE_LONGPOLL = "longpoll"

VK_API_URL = "https://api.vk.com/method/messages.send"
VK_API_PHOTO_UPLOAD_SERVER = "https://api.vk.com/method/photos.getMessagesUploadServer"
VK_API_PHOTO_SAVE = "https://api.vk.com/method/photos.saveMessagesPhoto"
VK_API_DOC_UPLOAD_SERVER = "https://api.vk.com/method/docs.getMessagesUploadServer"
VK_API_DOC_SAVE = "https://api.vk.com/method/docs.save"
VK_API_WALL_POST = "https://api.vk.com/method/wall.post"
VK_API_LONGPOLL_SERVER = "https://api.vk.com/method/groups.getLongPollServer"
VK_API_MARK_AS_READ = "https://api.vk.com/method/messages.markAsRead"
VK_API_CONVERSATIONS = "https://api.vk.com/method/messages.getConversations"
VK_API_VERSION = "5.199"