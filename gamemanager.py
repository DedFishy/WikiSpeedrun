from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from responsegen import ResponseGenerator
import utils
from flask_socketio import join_room, leave_room
from enum import Enum
from wiki import PageMeta, NoPage
from abc import ABC, abstractmethod
from wiki import WikipediaAPI

# Errors
class GameManagerError(Exception): 
    client_error = "Unknown error"
    def __init__(self, context:str = "Unknown"):
        super().__init__()
        self.error_context = context

    def __str__(self) -> str:
        return 'GameManagerError: "' + self.client_error + '" with context: ' + self.error_context

class PlayerDoesNotExistException(GameManagerError): client_error = "Player does not exist or has not been registered to the server"
class UsernameTakenException(GameManagerError): client_error = "That username is taken"
class RoomExistsException(GameManagerError): client_error = "That room already exists"
class RoomDoesNotExistException(GameManagerError): client_error = "That room does not exist"
class RoomAuthenticationErrorException(GameManagerError): client_error = "The code is incorrect"
class PlayerNotInRoomException(GameManagerError): client_error = "Player not found in this room"
class NotRoomOwnerException(GameManagerError): client_error = "Not the owner of the room"

class PageNotFoundException(GameManagerError): client_error = "Couldn't find that page"

class MalformedRequestException(GameManagerError): client_error = "Malformed request"

class InvalidInputException(GameManagerError): 
    def __init__(self, input_validation_result: utils.InputValidationResult, error_context = "Unknown"): 
        self.client_error = input_validation_result.value
        self.error_context = error_context

# Player class
class Player:
    def __init__(self, session_id: str):
        self.sid: str = session_id # Session ID provided by 
        self.name: str = session_id # Unique username
        self.room: Room = None # Tracks joined room, should be updated by Room.add_player
        self.page_path: list[dict] = [] # Tracks navigated pages, should be updated by GameModeResponse and reset by Room
        self.ready = True # Is player ready to start a game?

        self.current_page_index = -1 # The index of the page in the page_path that the player is viewing (for back & forward history)

    def get_title_page_path(self) -> list[str]:
        return [page["title"] for page in self.page_path]
# Game modes
class GameModeResponse(Enum):
    START = "start"
    CHANGE_USER_SCENE = "change_user_scene"
    CHANGE_ALL_SCENES = "change_all_scenes"
    VICTORY_RACE = "victory_race"
    NAV_PAGE = "navpage"
    NONE = ""

    def handle(self, response_gen: 'ResponseGenerator', room: 'Room', wikipedia_api: WikipediaAPI, player: Player = None, data = {}):
        if self == GameModeResponse.CHANGE_USER_SCENE:
            return response_gen.emit(GameModeResponse.CHANGE_USER_SCENE, response_gen.change_scene, player.sid, room=player.room, **data)
        elif self == GameModeResponse.CHANGE_ALL_SCENES:
            return response_gen.emit(GameModeResponse.CHANGE_ALL_SCENES, response_gen.change_scene, player.room.name, room=player.room, **data)
        elif self == GameModeResponse.NAV_PAGE:

            if player.current_page_index == -1:
                player.current_page_index = 0

            success = True

            if "direction" in data.keys():
                print(data)
                print(player.current_page_index)
                print(player.page_path)
                player.current_page_index += -1 if data["direction"] == "back" else 1

                if player.current_page_index >= len(player.page_path):
                    player.current_page_index = len(player.page_path) - 1
                
                print(player.current_page_index)
                if player.current_page_index > 0:
                    data["page_id"] = player.page_path[player.current_page_index]["page_id"]
                else:
                    data["page_id"] = player.room.settings.start_article.page_id
                
                
            else:
                player.page_path = player.page_path[0:player.current_page_index+1]
                success = wikipedia_api.process_page_request(data["page_id"], player, True)
                player.current_page_index = len(player.page_path) - 1
                
            if success:
                return response_gen.emit(GameModeResponse.NAV_PAGE, response_gen.nav_page, player.sid, page_id = data["page_id"])
            else:
                return response_gen.emit_error_response(GameModeResponse.NAV_PAGE, PageNotFoundException)
        elif self == GameModeResponse.VICTORY_RACE:
            room.unready_all_players()
            return response_gen.emit(GameModeResponse.VICTORY_RACE, response_gen.change_scene, player.room.name, room=player.room, scene="victory", winner_name=player.name, page_path=player.get_title_page_path())
        elif self == GameModeResponse.NONE:
            return
        elif self == GameModeResponse.START:
            start_article = player.room.settings.start_article
            for other_player in player.room.players:
                other_player.page_path = [start_article.serialize()]
                other_player.current_page_index = 0
            return response_gen.emit(GameModeResponse.START, response_gen.start, player.room.name, scene="wikiWindow", start_title = room.settings.start_article.page_id)
        else:
            print(f"Unhandled GameModeResponse: {self.value}")

class GameMode(ABC):
    name = "Base GameMode"
    def __init__(self, room):
        self.room: Room = room

    @abstractmethod
    def start(self) -> GameModeResponse:
        pass

    @abstractmethod
    def user_event(self, event, data) -> GameModeResponse:
        pass

class Race(GameMode):

    name = "Race"

    def start(self):
        return GameModeResponse.START
    
    def user_event(self, event, data):
        if event == "navpage":
            if "page_id" in data.keys():
                page = data["page_id"]
                if page == self.room.settings.end_article.page_id:
                    return GameModeResponse.VICTORY_RACE
            return GameModeResponse.NAV_PAGE
    
GAME_MODES = {
    "Race": Race
}

# Room setting container
class RoomSettings:
    mode: GameMode
    start_article: PageMeta = None
    end_article: PageMeta = None

    def __init__(self, room, api: WikipediaAPI):
        self.mode = GAME_MODES["Race"](room)

    def get_member_or(self, member, default = NoPage()):
        value = getattr(self, member)
        if value == None: return default
        return value
    
    def set_member(self, member, value):
        setattr(self, member, value)

    def check_room_settings_complete(self) -> bool:
        if type(self.mode) is not GameMode:
            return False
        if self.mode == GameMode.RACE:
            if None in [
                self.start_article,
                self.end_article
            ]:
                return False
        return True

# Room class
class Room:
    def __init__(self, name: str, code: str, api: WikipediaAPI):
        self.name = name # Room name
        self.requires_code = True # Require a code by default
        self.code = code if not code == "" else utils.generate_pin() # Generate four digit code for room if no code provided
        self.players: list[Player] = [] # Tracks players, should be updated by Room.add_player
        self.owner = None # Room creator
        self.settings = RoomSettings(self, api)
        self.waiting_for_reset = True # If we're waiting for all players to press finish

    def add_player(self, player: Player):
        if self.owner == None:
            self.owner = player
        if player.sid == player.name:
            player.name = utils.generate_unique_name(self.players)
        self.players.append(player)
        player.room = self
        join_room(self.name, player.sid)
    
    def get_players_waiting(self) -> int:
        return len([x for x in self.players if not x.ready])
    
    def evaluate_waiting_for_reset(self) -> bool:
        for player in self.players:
            if not player.ready:
                print("Waiting for reset.")
                self.waiting_for_reset = True
                return True
        print("All players were ready.")
        self.waiting_for_reset = False
        return False
    
    def unready_all_players(self):
        for player in self.players:
            player.ready = False
    
    def remove_player(self, player: Player):
        try:
            assign_new_leader = self.owner.sid == player.sid
            self.players.remove(player)
            leave_room(self.name, player.sid)
            player.room = None
            if assign_new_leader:
                if len(self.players) > 0:
                    self.owner = self.players[0]

        except ValueError:
            raise PlayerNotInRoomException("Removing player from room")
        return len(self.players) == 0

# Game manager
class GameManager:
    def __init__(self):
        self.players: dict[str, Player] = {}
        self.rooms = {}

    def get_username_taken(self, room: Room, username: str):
        for player in room.players:
            if player.name == username:
                return True
            
        return False

    def create_player(self, sid: str):
        self.players[sid] = Player(sid)
        return self.get_player(sid)
    
    def remove_player(self, sid: str) -> str|None:
        player = self.get_player(sid)
        if player.room is not None:
            room = player.room.name
            room_empty = player.room.remove_player(player)
            if room_empty:
                self.destroy_room(room)
            else:
                return room
        try:
            
            del self.players[sid]
        except KeyError:
            raise PlayerDoesNotExistException("Removing player")

    def get_player(self, sid: str) -> Player:
        try:
            return self.players[sid]
        except KeyError:
            raise PlayerDoesNotExistException("Retrieving player")
        
    def get_room(self, room: str) -> Room:
        try:
            return self.rooms[room]
        except KeyError:
            raise RoomDoesNotExistException("Retrieving room")
    
    def destroy_room(self, room: str):
        try:
            del self.rooms[room]
        except KeyError:
            raise RoomDoesNotExistException("Destroying room")


    def change_username(self, room: Room, player: Player, username: str):
        if self.get_username_taken(room, username):
            raise UsernameTakenException()
        
        self._validate(username)

        player.name = username

    def create_room(self, name: str, api: WikipediaAPI, code: str = "") -> Room:

        self._validate(name)

        if name in self.rooms.keys():
            raise RoomExistsException()
        
        self.rooms[name] = Room(name, code, api)
        return self.get_room(name)
    
    def join_room(self, player: Player, room: Room, code: str = "", ignore_incorrect: bool = False):

        if (room.requires_code and not room.code == code) and not ignore_incorrect:
            raise RoomAuthenticationErrorException()
        
        room.add_player(player)
    
    def validate_owns_room(self, player: Player):
        if not player.room.owner == player:
            raise NotRoomOwnerException("Ownership validator")

    def _validate(self, string: str):
        name_validation = utils.validate_input(string)
        if name_validation != utils.InputValidationResult.VALID:
            raise InvalidInputException(name_validation)    