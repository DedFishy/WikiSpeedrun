from enum import Enum

class EventType(Enum):

    CLIENT_CONNECT = "client_connect"
    CLIENT_DISCONNECT = "disconnect"

    TRY_JOIN_ROOM = "try_join_room"
    TRY_CREATE_ROOM = "try_create_room"
    TRY_LEAVE_ROOM = "try_leave_room"
    RETURN_TO_ROOM_SETTINGS = "return_to_room_settings"
    TRY_CHANGE_USERNAME = "try_change_username"

    JOIN_ROOM_RESPONSE = "join_room"
    LEAVE_ROOM_RESPONSE = "left_room"
    CHANGE_USERNAME_RESPONSE = "change_username"
    RETURN_TO_ROOM_SETTINGS_RESPONSE = "returned_to_room_settings"
    WAITING_ROOM = "waiting_room"

    SEND_CHAT_MESSAGE = "send_chat_message"

    ROOM_UPDATE = "room_update"

    SEARCH_PAGES = "search_pages"

    TRY_START_GAME = "try_start_game"
    START_GAME_RESPONSE = "start_game_response"

    GAME_MODE_EVENT = "game_mode_event"
